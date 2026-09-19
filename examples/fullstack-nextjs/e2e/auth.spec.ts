import { expect, test } from "@playwright/test";

test("register, login, dashboard, logout", async ({ page }) => {
  const email = `user-${Date.now()}@example.com`;
  await page.goto("/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("password123");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("Welcome document")).toBeVisible();
  await expect(page.getByText("Missing documents.create")).toBeVisible();
  // The E2E backend issues two-second access tokens. Reload after expiry must
  // restore through the HttpOnly refresh cookie and rotate the refresh token.
  await page.waitForTimeout(3_000);
  await page.reload();
  await expect(page.getByText(email)).toBeVisible();
  await expect(page.getByText("Welcome document")).toBeVisible();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByRole("link", { name: "Sign in" })).toBeVisible();
});

test("incorrect login stays on the form", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email or username").fill("missing@example.com");
  await page.getByLabel("Password").fill("wrong-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Invalid credentials.")).toBeVisible();
});

test("public authentication pages render their supported flows", async ({ page }) => {
  for (const [path, heading] of [
    ["/forgot-password", "Forgot password"],
    ["/reset-password", "Reset password"],
    ["/verify-email", "Verify email"],
    ["/mfa", "Multi-factor authentication"],
  ] as const) {
    await page.goto(path);
    await expect(page.getByRole("heading", { name: heading })).toBeVisible();
  }
});
