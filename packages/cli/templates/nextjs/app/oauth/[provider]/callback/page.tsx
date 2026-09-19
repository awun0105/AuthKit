import { Suspense } from "react";

import { OAuthCallbackClient } from "./oauth-callback-client";

export default function OAuthCallbackPage() {
  return <Suspense fallback={<p>Completing sign-in…</p>}><OAuthCallbackClient /></Suspense>;
}
