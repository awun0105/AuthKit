import { NextRequest } from "next/server.js";
import { describe, expect, it } from "vitest";

import { authkitMiddleware, DEFAULT_PUBLIC, isPublicPath, safeLocalRedirect } from "./middleware.js";

describe("authkitMiddleware helpers", () => {
  it("treats login as public", () => {
    expect(isPublicPath("/login", DEFAULT_PUBLIC)).toBe(true);
    expect(isPublicPath("/account/security", DEFAULT_PUBLIC)).toBe(false);
    const response = authkitMiddleware()(new NextRequest("https://app.example/account/security?tab=mfa"));
    const location = new URL(response.headers.get("location") ?? "https://invalid.example");
    expect(location.pathname).toBe("/login");
    expect(location.searchParams.get("next")).toBe("/account/security?tab=mfa");
  });

  it("accepts only local post-login redirect paths", () => {
    expect(safeLocalRedirect("/documents?view=mine", "/dashboard")).toBe("/documents?view=mine");
    expect(safeLocalRedirect("https://evil.example", "/dashboard")).toBe("/dashboard");
    expect(safeLocalRedirect("//evil.example", "/dashboard")).toBe("/dashboard");
    expect(safeLocalRedirect("/\\evil.example", "/dashboard")).toBe("/dashboard");
  });
});
