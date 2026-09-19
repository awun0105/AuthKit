"use client";

import { useAuth } from "@authkit/react";
import { useEffect, useState } from "react";

export function OAuthButtons() {
  const { client } = useAuth();
  const [providers, setProviders] = useState<string[]>([]);
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void client.getConfig().then((config) => setProviders(config.oauth_providers)).catch(() => {
      setError("Unable to load OAuth providers.");
    });
  }, [client]);

  if (providers.length === 0 && !error) return null;

  return (
    <div className="auth-oauth">
      {providers.map((provider) => (
        <button
          key={provider}
          type="button"
          disabled={pending !== null}
          onClick={() => {
            setPending(provider);
            setError(null);
            sessionStorage.removeItem("authkit_oauth_purpose");
            void client.oauth.authorizeUrl(provider)
              .then((url) => { window.location.href = url; })
              .catch(() => { setPending(null); setError(`Unable to start ${provider} sign-in.`); });
          }}
        >
          {pending === provider ? "Opening…" : `Continue with ${provider}`}
        </button>
      ))}
      {error ? <p className="auth-error" role="alert">{error}</p> : null}
    </div>
  );
}
