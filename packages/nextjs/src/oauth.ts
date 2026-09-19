import type { AuthKitClient } from "@authkit/client";

export async function completeOAuthCallback(
  client: AuthKitClient,
  provider: string,
  searchParams: URLSearchParams,
  purpose: "login" | "connect" = "login",
): Promise<{ ok: true } | { ok: false; error: string }> {
  const code = searchParams.get("code");
  const state = searchParams.get("state");
  const oauthError = searchParams.get("error");
  if (oauthError) {
    return { ok: false, error: oauthError };
  }
  if (!code || !state) {
    return { ok: false, error: "missing_oauth_params" };
  }
  try {
    if (purpose === "connect") {
      await client.oauth.connect(provider, { code, state });
    } else {
      await client.oauth.callback(provider, code, state);
    }
    return { ok: true };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : "oauth_failed" };
  }
}
