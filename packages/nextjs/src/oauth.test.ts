import { createAuthClient } from "@authkit/client";
import { describe, expect, it, vi } from "vitest";

import { completeOAuthCallback } from "./oauth.js";

describe("completeOAuthCallback", () => {
  it("uses the account-connect endpoint for linking callbacks", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({
      id: "account-1",
      provider: "github",
      email: "user@example.com",
      created_at: "2026-01-01T00:00:00Z",
    }), { status: 200, headers: { "Content-Type": "application/json" } }));
    const client = createAuthClient({
      baseUrl: "http://api/auth",
      fetch: fetchMock as unknown as typeof fetch,
    });
    client.tokens.setAccessToken("access");

    const result = await completeOAuthCallback(
      client,
      "github",
      new URLSearchParams({ code: "code", state: "state" }),
      "connect",
    );

    expect(result).toEqual({ ok: true });
    expect(String(fetchMock.mock.calls[0]?.[0])).toBe("http://api/auth/oauth/github/connect");
  });
});
