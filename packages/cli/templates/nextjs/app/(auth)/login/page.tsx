import { Suspense } from "react";

import { AuthShell } from "@/components/auth/auth-shell";
import { LoginForm } from "@/components/auth/login-form";

export default function LoginPage() {
  return (
    <AuthShell title="Sign in">
      <Suspense fallback={<p>Loading sign-in…</p>}><LoginForm /></Suspense>
    </AuthShell>
  );
}
