import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AuthKitError, createAuthClient, type AuthUser } from "@authkit/client";

import { AuthProvider } from "./provider.js";
import { RequireAuth, RequirePermission, RequireRole } from "./guards.js";
import { useAuth } from "./hooks.js";

const user: AuthUser = {
  id: "1",
  email: "a@b.com",
  username: null,
  full_name: null,
  is_active: true,
  is_verified: true,
  is_superuser: false,
  roles: ["member"],
  scopes: ["documents.read"],
  mfa_enabled: false,
  has_password: true,
  created_at: "",
  updated_at: "",
};

function Probe() {
  const { isAuthenticated, user: current, hasPermission } = useAuth();
  return (
    <div>
      <span>{isAuthenticated ? "in" : "out"}</span>
      <span>{current?.email ?? "none"}</span>
      <span>{hasPermission("documents.read") ? "allowed" : "denied"}</span>
    </div>
  );
}

describe("AuthProvider", () => {
  it("restores a session and enforces permission UX", async () => {
    const client = createAuthClient({
      baseUrl: "http://api/auth",
      fetch: (async () =>
        new Response(JSON.stringify(user), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })) as unknown as typeof fetch,
    });
    client.tokens.setAccessToken("access");
    render(
      <AuthProvider client={client}>
        <RequireAuth fallback={<span>loading-or-anon</span>}>
          <RequireRole role="member" fallback={<span>wrong-role</span>}>
            <RequirePermission permission="documents.read" fallback={<span>nope</span>}>
              <Probe />
            </RequirePermission>
          </RequireRole>
        </RequireAuth>
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByText("in")).toBeDefined());
    expect(screen.getByText("a@b.com")).toBeDefined();
    expect(screen.getByText("allowed")).toBeDefined();
  });

  it("transitions from guest to authenticated after login", async () => {
    const client = createAuthClient({ baseUrl: "http://api/auth", fetch: vi.fn() });
    vi.spyOn(client, "restoreSession").mockResolvedValue(null);
    vi.spyOn(client, "login").mockResolvedValue({
      access_token: "access",
      refresh_token: "refresh",
      token_type: "bearer",
      user,
    });
    function LoginProbe() {
      const { login, isAuthenticated } = useAuth();
      return (
        <button type="button" onClick={() => void login({ identifier: user.email, password: "secret" })}>
          {isAuthenticated ? "authenticated" : "guest"}
        </button>
      );
    }
    render(<AuthProvider client={client}><LoginProbe /></AuthProvider>);
    await waitFor(() => expect(screen.getByText("guest")).toBeDefined());
    fireEvent.click(screen.getByText("guest"));
    await waitFor(() => expect(screen.getByText("authenticated")).toBeDefined());
  });

  it("logs out and clears auth state", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith("/logout")) return new Response(null, { status: 204 });
      return new Response(JSON.stringify(user), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });
    const client = createAuthClient({
      baseUrl: "http://api/auth",
      fetch: fetchMock as unknown as typeof fetch,
    });
    client.tokens.setAccessToken("access");
    function LogoutProbe() {
      const { logout, isAuthenticated } = useAuth();
      return (
        <button type="button" onClick={() => void logout()}>
          {isAuthenticated ? "authed" : "guest"}
        </button>
      );
    }
    render(
      <AuthProvider client={client}>
        <LogoutProbe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByText("authed")).toBeDefined());
    screen.getByText("authed").click();
    await waitFor(() => expect(screen.getByText("guest")).toBeDefined());
  });

  it("surfaces a session-restoration network failure without authenticating", async () => {
    const client = createAuthClient({ baseUrl: "http://api/auth", fetch: vi.fn() });
    vi.spyOn(client, "restoreSession").mockRejectedValue(new AuthKitError("NETWORK_ERROR", "offline"));
    function ErrorProbe() {
      const { error, isAuthenticated, isLoading } = useAuth();
      return <span>{isLoading ? "loading" : `${isAuthenticated ? "in" : "out"}:${error?.code ?? "none"}`}</span>;
    }
    render(<AuthProvider client={client}><ErrorProbe /></AuthProvider>);
    await waitFor(() => expect(screen.getByText("out:NETWORK_ERROR")).toBeDefined());
  });
});
