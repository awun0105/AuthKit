import { authkitMiddleware } from "@authkit/nextjs";

export const middleware = authkitMiddleware({
  publicPrefixes: [
    "/login",
    "/register",
    "/forgot-password",
    "/reset-password",
    "/verify-email",
    "/mfa",
    "/oauth",
    "/unauthorized",
  ],
});

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
