import { AuthKitError, errorFromResponse } from "./errors.js";
import { createMemoryTokenStore } from "./storage.js";
import type {
  AuthClientOptions,
  AuthUser,
  LoginRequest,
  LoginResponse,
  MfaSetupResult,
  MessageResponse,
  OAuthAccount,
  OAuthCallbackInput,
  OAuthCallbackResponse,
  PublicAuthConfig,
  RegisterRequest,
  SessionRead,
  TokenPair,
  TokenStore,
} from "./types.js";

const CSRF_HEADER = "X-AuthKit-Requested-With";
const CSRF_VALUE = "AuthKit";

function joinUrl(baseUrl: string, path: string): string {
  return `${baseUrl.replace(/\/$/, "")}/${path.replace(/^\//, "")}`;
}

function readDetail(payload: unknown): string {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    return JSON.stringify(detail);
  }
  return "Request failed";
}

export class AuthKitClient {
  readonly baseUrl: string;
  readonly mode: "bearer" | "browser";
  readonly tokens: TokenStore;
  private readonly fetchImpl: typeof fetch;
  private readonly authenticatedCookieName: string;
  private readonly authenticatedCookieMaxAge: number;
  private refreshInFlight: Promise<TokenPair> | null = null;

  constructor(options: AuthClientOptions) {
    this.baseUrl = options.baseUrl;
    this.mode = options.mode ?? "bearer";
    this.tokens = options.tokenStore ?? createMemoryTokenStore();
    // Browser-native fetch performs a brand check in some engines. Bind the
    // default implementation so calling it through this class is legal.
    this.fetchImpl = options.fetch ?? globalThis.fetch.bind(globalThis);
    this.authenticatedCookieName = options.authenticatedCookieName ?? "authkit_authenticated";
    this.authenticatedCookieMaxAge = options.authenticatedCookieMaxAge ?? 604_800;
  }

  private rememberTokens(pair: TokenPair): void {
    this.tokens.setAccessToken(pair.access_token);
    if (this.mode === "bearer") {
      this.tokens.setRefreshToken(pair.refresh_token);
    }
    this.setBrowserAuthFlag(true);
  }

  private setBrowserAuthFlag(authenticated: boolean): void {
    // The API's non-HttpOnly flag is host-only. Mirror it on the Next.js app
    // origin so middleware can perform UX redirects when API and UI differ.
    if (this.mode !== "browser" || typeof document === "undefined") return;
    const secure = typeof window !== "undefined" && window.location.protocol === "https:" ? "; Secure" : "";
    document.cookie = authenticated
      ? `${this.authenticatedCookieName}=1; Path=/; Max-Age=${this.authenticatedCookieMaxAge}; SameSite=Lax${secure}`
      : `${this.authenticatedCookieName}=; Path=/; Max-Age=0; SameSite=Lax${secure}`;
  }

  private async parse(response: Response): Promise<unknown> {
    if (response.status === 204) return null;
    const text = await response.text();
    if (!text) return null;
    try {
      return JSON.parse(text) as unknown;
    } catch {
      return { detail: text };
    }
  }

  async request<T>(
    path: string,
    init: RequestInit = {},
    { retry = true, auth = false }: { retry?: boolean; auth?: boolean } = {},
  ): Promise<T> {
    const headers = new Headers(init.headers);
    if (init.body && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    if (this.mode === "browser") {
      headers.set(CSRF_HEADER, CSRF_VALUE);
    }
    if (auth) {
      const access = this.tokens.getAccessToken();
      if (access) headers.set("Authorization", `Bearer ${access}`);
    }
    let response: Response;
    try {
      response = await this.fetchImpl(joinUrl(this.baseUrl, path), {
        ...init,
        headers,
        credentials: this.mode === "browser" ? "include" : init.credentials,
      });
    } catch (error) {
      throw new AuthKitError(
        "NETWORK_ERROR",
        error instanceof Error ? error.message : "Network error",
      );
    }
    const authErrorCode = response.headers.get("X-AuthKit-Error");
    const canRefresh = response.status === 401 || authErrorCode === "TOKEN_EXPIRED";
    if (canRefresh && auth && retry) {
      try {
        await this.refresh();
      } catch (error) {
        this.clearSession();
        if (error instanceof AuthKitError) throw error;
        const payload = await this.parse(response);
        throw errorFromResponse(
          response.status,
          readDetail(payload),
          response.headers.get("X-AuthKit-Error"),
        );
      }
      return this.request<T>(path, init, { retry: false, auth });
    }
    const payload = await this.parse(response);
    if (!response.ok) {
      throw errorFromResponse(
        response.status,
        readDetail(payload),
        response.headers.get("X-AuthKit-Error"),
      );
    }
    return payload as T;
  }

  clearSession(): void {
    this.tokens.setAccessToken(null);
    this.tokens.setRefreshToken(null);
    this.setBrowserAuthFlag(false);
  }

  async getConfig(): Promise<PublicAuthConfig> {
    return this.request("/config");
  }

  async register(input: RegisterRequest): Promise<AuthUser> {
    return this.request("/register", { method: "POST", body: JSON.stringify(input) });
  }

  async login(input: LoginRequest): Promise<LoginResponse> {
    const result = await this.request<LoginResponse>("/login", {
      method: "POST",
      body: JSON.stringify(input),
    });
    this.rememberTokens(result);
    return result;
  }

  async logout(): Promise<void> {
    const body =
      this.mode === "bearer" && this.tokens.getRefreshToken()
        ? JSON.stringify({ refresh_token: this.tokens.getRefreshToken() })
        : undefined;
    try {
      await this.request("/logout", { method: "POST", body }, { auth: true, retry: false });
    } finally {
      this.clearSession();
    }
  }

  async refresh(): Promise<TokenPair> {
    if (this.refreshInFlight) return this.refreshInFlight;
    this.refreshInFlight = (async () => {
      const body =
        this.mode === "bearer"
          ? JSON.stringify({ refresh_token: this.tokens.getRefreshToken() })
          : JSON.stringify({});
      const pair = await this.request<TokenPair>("/refresh", { method: "POST", body }, { retry: false });
      this.rememberTokens(pair);
      return pair;
    })();
    try {
      return await this.refreshInFlight;
    } finally {
      this.refreshInFlight = null;
    }
  }

  async getCurrentUser(): Promise<AuthUser> {
    return this.request("/me", { method: "GET" }, { auth: true });
  }

  async restoreSession(): Promise<AuthUser | null> {
    try {
      if (!this.tokens.getAccessToken()) {
        await this.refresh();
      }
      return await this.getCurrentUser();
    } catch (error) {
      if (error instanceof AuthKitError) {
        if (error.code === "NETWORK_ERROR") throw error;
        this.clearSession();
        if (["UNAUTHENTICATED", "TOKEN_EXPIRED", "TOKEN_REVOKED", "INVALID_TOKEN", "UNKNOWN_ERROR"].includes(error.code)) {
          return null;
        }
        throw error;
      }
      throw error;
    }
  }

  async requestPasswordReset(identifier: string): Promise<MessageResponse> {
    return this.request("/forgot-password", {
      method: "POST",
      body: JSON.stringify({ identifier }),
    });
  }

  async resetPassword(token: string, newPassword: string): Promise<MessageResponse> {
    return this.request("/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, new_password: newPassword }),
    });
  }

  async resetPasswordOtp(identifier: string, otp: string, newPassword: string): Promise<MessageResponse> {
    return this.request("/reset-password-otp", {
      method: "POST",
      body: JSON.stringify({ identifier, otp, new_password: newPassword }),
    });
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<TokenPair> {
    const pair = await this.request<TokenPair>(
      "/change-password",
      { method: "POST", body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }) },
      { auth: true },
    );
    this.rememberTokens(pair);
    return pair;
  }

  async setPassword(newPassword: string): Promise<MessageResponse> {
    return this.request(
      "/set-password",
      { method: "POST", body: JSON.stringify({ new_password: newPassword }) },
      { auth: true },
    );
  }

  async verifyEmail(token: string): Promise<AuthUser> {
    return this.request("/verify-email", { method: "POST", body: JSON.stringify({ token }) });
  }

  async verifyOtp(identifier: string, otp: string): Promise<AuthUser> {
    return this.request("/verify-otp", { method: "POST", body: JSON.stringify({ identifier, otp }) });
  }

  async resendVerification(identifier: string): Promise<MessageResponse> {
    return this.request("/resend-verification", {
      method: "POST",
      body: JSON.stringify({ identifier }),
    });
  }

  async listSessions(): Promise<SessionRead[]> {
    return this.request("/sessions", { method: "GET" }, { auth: true });
  }

  readonly oauth = {
    listProviders: async (): Promise<{ name: string }[]> => this.request("/oauth/providers"),
    authorizeUrl: async (provider: string): Promise<string> => {
      const providerPath = encodeURIComponent(provider);
      const result = await this.request<{ authorization_url: string }>(
        `/oauth/${providerPath}/authorize`,
        { method: "GET" },
        { auth: Boolean(this.tokens.getAccessToken()) },
      );
      return result.authorization_url;
    },
    callback: async (
      provider: string,
      code: string,
      state: string,
      postBody?: Record<string, unknown>,
    ): Promise<OAuthCallbackResponse> => {
      const providerPath = encodeURIComponent(provider);
      const result = await this.request<OAuthCallbackResponse>(`/oauth/${providerPath}/callback`, {
        method: "POST",
        body: JSON.stringify({ code, state, post_body: postBody }),
      });
      this.rememberTokens(result);
      return result;
    },
    connect: async (provider: string, input: OAuthCallbackInput): Promise<OAuthAccount> => {
      if (!this.tokens.getAccessToken()) await this.refresh();
      const providerPath = encodeURIComponent(provider);
      return this.request(
        `/oauth/${providerPath}/connect`,
        {
          method: "POST",
          body: JSON.stringify({
            code: input.code,
            state: input.state,
            post_body: input.postBody,
          }),
        },
        { auth: true },
      );
    },
    accounts: async (): Promise<OAuthAccount[]> =>
      this.request("/oauth/accounts", { method: "GET" }, { auth: true }),
    disconnect: async (provider: string): Promise<void> => {
      const providerPath = encodeURIComponent(provider);
      await this.request(`/oauth/${providerPath}/disconnect`, { method: "DELETE" }, { auth: true });
    },
  };

  readonly mfa = {
    setup: async (): Promise<MfaSetupResult> =>
      this.request("/mfa/setup", { method: "POST" }, { auth: true }),
    confirm: async (totpCode: string): Promise<MessageResponse> =>
      this.request("/mfa/confirm", { method: "POST", body: JSON.stringify({ totp_code: totpCode }) }, { auth: true }),
    disable: async (password: string, totpOrBackupCode: string): Promise<MessageResponse> =>
      this.request(
        "/mfa/disable",
        { method: "POST", body: JSON.stringify({ password, totp_or_backup_code: totpOrBackupCode }) },
        { auth: true },
      ),
  };
}

export function createAuthClient(options: AuthClientOptions): AuthKitClient {
  return new AuthKitClient(options);
}
