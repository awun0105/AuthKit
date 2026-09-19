import type { NextRequest } from "next/server.js";
import { NextResponse } from "next/server.js";

export type AuthkitMiddlewareOptions = {
  loginPath?: string;
  publicPrefixes?: string[];
  cookieName?: string;
};

export const DEFAULT_PUBLIC = [
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
  "/verify-email",
  "/mfa",
  "/oauth",
  "/unauthorized",
];

export function isPublicPath(pathname: string, publicPrefixes: string[]): boolean {
  return publicPrefixes.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
}

/** Return a same-origin application path, or the configured fallback. */
export function safeLocalRedirect(value: string | null | undefined, fallback = "/"): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.includes("\\")) {
    return fallback;
  }
  return value;
}

/**
 * UX-only route protection using the non-HttpOnly `authkit_authenticated` flag.
 * Backend authorization remains the security authority.
 */
export function authkitMiddleware(options: AuthkitMiddlewareOptions = {}) {
  const loginPath = options.loginPath ?? "/login";
  const cookieName = options.cookieName ?? "authkit_authenticated";
  const publicPrefixes = options.publicPrefixes ?? DEFAULT_PUBLIC;

  return function middleware(request: NextRequest) {
    const { pathname } = request.nextUrl;
    const isPublic = isPublicPath(pathname, publicPrefixes);
    const hasSession = request.cookies.get(cookieName)?.value === "1";
    if (!isPublic && !hasSession) {
      const url = request.nextUrl.clone();
      url.pathname = loginPath;
      url.searchParams.set("next", `${pathname}${request.nextUrl.search}`);
      return NextResponse.redirect(url);
    }
    return NextResponse.next();
  };
}
