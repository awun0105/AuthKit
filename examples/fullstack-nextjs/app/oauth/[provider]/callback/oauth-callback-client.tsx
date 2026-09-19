"use client";

import { completeOAuthCallback } from "@authkit/nextjs";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { authClient } from "@/lib/auth/client";
import { authUIConfig } from "@/lib/auth/config";

export function OAuthCallbackClient() {
  const params = useParams<{ provider: string }>();
  const search = useSearchParams();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const purpose = sessionStorage.getItem("authkit_oauth_purpose") === "connect" ? "connect" : "login";
    void completeOAuthCallback(authClient, params.provider, search, purpose).then((result) => {
      if (result.ok) {
        sessionStorage.removeItem("authkit_oauth_purpose");
        router.replace(purpose === "connect" ? "/account/security" : authUIConfig.loginRedirect);
      } else {
        setError(result.error);
      }
    });
  }, [params.provider, router, search]);

  if (error) return <p role="alert">{error}</p>;
  return <p>Completing sign-in…</p>;
}
