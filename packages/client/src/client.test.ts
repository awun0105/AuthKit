import { afterEach, describe, expect, it, vi } from "vitest";

import { AuthKitError, createAuthClient } from "./index.js";

function jsonResponse(body: unknown, status = 200, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("AuthKitClient", () => {
  it("logs in and stores the access token", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({
        access_token: "access",
        refresh_token: "refresh",
        token_type: "bearer",
        user: { id: "1", email: "a@b.com", roles: [], scopes: [], is_active: true, is_verified: true, is_superuser: false, mfa_enabled: false, has_password: true, username: null, full_name: null, created_at: "", updated_at: "" },
      }),
    );
    const auth = createAuthClient({ baseUrl: "http://api/auth", fetch: fetchMock as unknown as typeof fetch });
    const result = await auth.login({ identifier: "a@b.com", password: "secret" });
    expect(result.access_token).toBe("access");
    expect(auth.tokens.getAccessToken()).toBe("access");
  });

  it("maps structured backend error codes", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({ detail: "Invalid credentials." }, 401, { "X-AuthKit-Error": "INVALID_CREDENTIALS" }),
    );
    const auth = createAuthClient({ baseUrl: "http://api/auth", fetch: fetchMock as unknown as typeof fetch });
    await expect(auth.login({ identifier: "a@b.com", password: "bad" })).rejects.toMatchObject({
      code: "INVALID_CREDENTIALS",
    });
  });

  it("refreshes once under concurrent 401s", async () => {
    let refreshCalls = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/refresh")) {
        refreshCalls += 1;
        return jsonResponse({ access_token: "new", refresh_token: "r2", token_type: "bearer" });
      }
      const header = new Headers(init?.headers).get("Authorization");
      if (header === "Bearer expired") {
        return jsonResponse({ detail: "Token has expired" }, 400, { "X-AuthKit-Error": "TOKEN_EXPIRED" });
      }
      return jsonResponse({
        id: "1",
        email: "a@b.com",
        username: null,
        full_name: null,
        is_active: true,
        is_verified: true,
        is_superuser: false,
        roles: [],
        scopes: [],
        mfa_enabled: false,
        has_password: true,
        created_at: "",
        updated_at: "",
      });
    });
    const auth = createAuthClient({ baseUrl: "http://api/auth", fetch: fetchMock as unknown as typeof fetch });
    auth.tokens.setAccessToken("expired");
    auth.tokens.setRefreshToken("refresh");
    const [a, b] = await Promise.all([auth.getCurrentUser(), auth.getCurrentUser()]);
    expect(a.email).toBe("a@b.com");
    expect(b.email).toBe("a@b.com");
    expect(refreshCalls).toBe(1);
  });

  it("clears stale tokens when refresh fails", async () => {
    const auth = createAuthClient({
      baseUrl: "http://api/auth",
      fetch: (async (input: RequestInfo | URL) => {
        const path = String(input);
        if (path.endsWith("/refresh")) {
          return jsonResponse({ detail: "Token has been revoked" }, 401, {
            "X-AuthKit-Error": "TOKEN_REVOKED",
          });
        }
        return jsonResponse({ detail: "Token has expired" }, 401, {
          "X-AuthKit-Error": "TOKEN_EXPIRED",
        });
      }) as unknown as typeof fetch,
    });
    auth.tokens.setAccessToken("expired");
    auth.tokens.setRefreshToken("revoked");
    await expect(auth.getCurrentUser()).rejects.toMatchObject({ code: "TOKEN_REVOKED" });
    expect(auth.tokens.getAccessToken()).toBeNull();
    expect(auth.tokens.getRefreshToken()).toBeNull();
  });

  it("uses the backend contracts for set-password and OAuth connect", async () => {
    const calls: Array<{ url: string; body: string | undefined }> = [];
    const auth = createAuthClient({
      baseUrl: "http://api/auth",
      fetch: (async (input: RequestInfo | URL, init?: RequestInit) => {
        calls.push({ url: String(input), body: init?.body as string | undefined });
        if (String(input).endsWith("/connect")) {
          return jsonResponse({ id: "oauth-1", provider: "github", email: "a@b.com", created_at: "" });
        }
        return jsonResponse({ detail: "Password set successfully." });
      }) as unknown as typeof fetch,
    });
    auth.tokens.setAccessToken("access");
    await auth.setPassword("new-password");
    await auth.oauth.connect("github", { code: "code", state: "state" });
    expect(calls[0]).toMatchObject({ url: "http://api/auth/set-password" });
    expect(JSON.parse(calls[1]?.body ?? "{}")).toMatchObject({ code: "code", state: "state" });
  });

  it("wraps network failures", async () => {
    const auth = createAuthClient({
      baseUrl: "http://api/auth",
      fetch: (async () => {
        throw new TypeError("failed to fetch");
      }) as unknown as typeof fetch,
    });
    await expect(auth.getConfig()).rejects.toBeInstanceOf(AuthKitError);
    await expect(auth.getConfig()).rejects.toMatchObject({ code: "NETWORK_ERROR" });
  });

  it("does not erase a potentially valid session during a temporary network failure", async () => {
    const auth = createAuthClient({
      baseUrl: "http://api/auth",
      fetch: (async () => {
        throw new TypeError("offline");
      }) as unknown as typeof fetch,
    });
    auth.tokens.setAccessToken("possibly-valid");
    await expect(auth.restoreSession()).rejects.toMatchObject({ code: "NETWORK_ERROR" });
    expect(auth.tokens.getAccessToken()).toBe("possibly-valid");
  });

  it("surfaces a disabled account during restoration and clears its tokens", async () => {
    const auth = createAuthClient({
      baseUrl: "http://api/auth",
      fetch: (async () => jsonResponse(
        { detail: "This account has been deactivated" },
        403,
        { "X-AuthKit-Error": "ACCOUNT_DISABLED" },
      )) as unknown as typeof fetch,
    });
    auth.tokens.setAccessToken("disabled-user-token");
    await expect(auth.restoreSession()).rejects.toMatchObject({ code: "ACCOUNT_DISABLED" });
    expect(auth.tokens.getAccessToken()).toBeNull();
  });

  it("mirrors browser authentication state for a separate Next.js origin", async () => {
    const originalDocument = globalThis.document;
    let cookie = "";
    Object.defineProperty(globalThis, "document", {
      configurable: true,
      value: { get cookie() { return cookie; }, set cookie(value: string) { cookie = value; } },
    });
    try {
      const auth = createAuthClient({
        baseUrl: "http://api/auth",
        mode: "browser",
        fetch: (async () => jsonResponse({
          access_token: "access",
          refresh_token: "refresh",
          token_type: "bearer",
        })) as unknown as typeof fetch,
      });
      await auth.refresh();
      expect(cookie).toContain("authkit_authenticated=1");
      auth.clearSession();
      expect(cookie).toContain("authkit_authenticated=;");
    } finally {
      Object.defineProperty(globalThis, "document", {
        configurable: true,
        value: originalDocument,
      });
    }
  });
});
