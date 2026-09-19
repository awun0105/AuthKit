import { Suspense } from "react";

import { AuthShell } from "@/components/auth/auth-shell";
import { MfaChallenge } from "@/components/auth/mfa-challenge";

export default function MfaPage() {
  return (
    <AuthShell title="Multi-factor authentication">
      <Suspense fallback={<p>Loading MFA challenge…</p>}><MfaChallenge /></Suspense>
    </AuthShell>
  );
}
