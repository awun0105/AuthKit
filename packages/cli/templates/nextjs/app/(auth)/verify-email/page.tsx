import { Suspense } from "react";

import { AuthShell } from "@/components/auth/auth-shell";
import { VerifyEmail } from "@/components/auth/verify-email";

export default function VerifyEmailPage() {
  return (
    <AuthShell title="Verify email">
      <Suspense fallback={<p>Loading verification…</p>}><VerifyEmail /></Suspense>
    </AuthShell>
  );
}
