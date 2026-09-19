"use client";

import { LoginForm } from "./login-form";

/** MFA during login is handled inside LoginForm when the backend returns MFA_REQUIRED. */
export function MfaChallenge() {
  return <LoginForm />;
}
