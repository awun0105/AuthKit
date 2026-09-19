import { Suspense } from "react";

import { AuthShell } from "@/components/auth/auth-shell";
import { ResetPasswordForm } from "@/components/auth/reset-password-form";

export default function ResetPasswordPage() {
  return (
    <AuthShell title="Reset password">
      <Suspense fallback={<p>Loading reset form…</p>}><ResetPasswordForm /></Suspense>
    </AuthShell>
  );
}
