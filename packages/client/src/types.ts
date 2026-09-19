export type AuthUser = {
  id: string;
  email: string;
  username: string | null;
  full_name: string | null;
  is_active: boolean;
  is_verified: boolean;
  is_superuser: boolean;
  roles: string[];
  scopes: string[];
  mfa_enabled: boolean;
  has_password: boolean;
  created_at: string;
  updated_at: string;
};

export type RegisterRequest = {
  email: string;
  password: string;
  username?: string | null;
  full_name?: string | null;
  phone_number?: string | null;
};

export type LoginRequest = {
  identifier: string;
  password: string;
  totp_code?: string | null;
};

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export type LoginResponse = TokenPair & {
  user: AuthUser;
};

export type MessageResponse = {
  detail: string;
};

export type PublicAuthConfig = {
  allow_registration: boolean;
  require_email_verification: boolean;
  verification_method: "link" | "otp";
  password_reset_method: "link" | "otp";
  enable_mfa: boolean;
  oauth_providers: string[];
  refresh_cookie: boolean;
};

export type SessionRead = {
  session_id: string;
  user_agent: string | null;
  issued_at: string;
  expires_at: string;
};

export type MfaSetupResult = {
  secret: string;
  qr_uri: string;
  backup_codes: string[];
};

export type OAuthAccount = {
  id: string;
  provider: string;
  email: string | null;
  created_at: string;
};

export type OAuthCallbackResponse = LoginResponse & {
  is_new_user: boolean;
};

export type OAuthCallbackInput = {
  code: string;
  state: string;
  postBody?: Record<string, unknown>;
};

export type AuthClientMode = "bearer" | "browser";

export type TokenStore = {
  getAccessToken(): string | null;
  setAccessToken(token: string | null): void;
  getRefreshToken(): string | null;
  setRefreshToken(token: string | null): void;
};

export type AuthClientOptions = {
  baseUrl: string;
  mode?: AuthClientMode;
  tokenStore?: TokenStore;
  fetch?: typeof fetch;
  /** Frontend-host cookie used only for Next.js middleware UX redirects. */
  authenticatedCookieName?: string;
  /** UX-cookie lifetime in seconds; align it with the backend refresh TTL. */
  authenticatedCookieMaxAge?: number;
};
