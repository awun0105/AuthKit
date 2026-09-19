export type AuthKitErrorCode =
  | "INVALID_CREDENTIALS"
  | "ACCOUNT_DISABLED"
  | "ACCOUNT_LOCKED"
  | "REGISTRATION_DISABLED"
  | "WEAK_PASSWORD"
  | "EMAIL_ALREADY_EXISTS"
  | "EMAIL_NOT_VERIFIED"
  | "MFA_REQUIRED"
  | "INVALID_MFA_CODE"
  | "TOKEN_EXPIRED"
  | "TOKEN_REVOKED"
  | "INVALID_TOKEN"
  | "INVALID_RESET_TOKEN"
  | "USER_NOT_FOUND"
  | "PERMISSION_DENIED"
  | "CSRF_FAILED"
  | "RATE_LIMITED"
  | "MFA_NOT_ENABLED"
  | "MFA_ALREADY_ENABLED"
  | "INVALID_BACKUP_CODE"
  | "OAUTH_STATE_MISMATCH"
  | "OAUTH_PROVIDER_NOT_CONFIGURED"
  | "OAUTH_CODE_EXCHANGE_FAILED"
  | "OAUTH_USER_INFO_FAILED"
  | "PROVIDER_ALREADY_LINKED"
  | "LAST_LOGIN_METHOD"
  | "VALIDATION_ERROR"
  | "NETWORK_ERROR"
  | "UNAUTHENTICATED"
  | "UNKNOWN_ERROR"
  | string;

export class AuthKitError extends Error {
  readonly code: AuthKitErrorCode;
  readonly status: number;
  readonly detail: string;

  constructor(code: AuthKitErrorCode, detail: string, status = 0) {
    super(detail);
    this.name = "AuthKitError";
    this.code = code;
    this.detail = detail;
    this.status = status;
  }
}

export function errorFromResponse(status: number, detail: string, headerCode?: string | null): AuthKitError {
  if (headerCode) {
    return new AuthKitError(headerCode, detail || headerCode, status);
  }
  if (status === 401 && /credential/i.test(detail)) {
    return new AuthKitError("INVALID_CREDENTIALS", detail, status);
  }
  if (status === 401) {
    return new AuthKitError("UNAUTHENTICATED", detail || "Not authenticated", status);
  }
  if (status === 403) {
    return new AuthKitError("PERMISSION_DENIED", detail, status);
  }
  if (status === 422) {
    return new AuthKitError("VALIDATION_ERROR", detail, status);
  }
  return new AuthKitError("UNKNOWN_ERROR", detail || "Request failed", status);
}
