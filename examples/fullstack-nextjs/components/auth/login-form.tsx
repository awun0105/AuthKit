"use client";

import { AuthKitError } from "@authkit/client";
import { safeLocalRedirect } from "@authkit/nextjs";
import { useAuth } from "@authkit/react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";

import { authUIConfig } from "@/lib/auth/config";
import { FormStatus } from "./form-status";
import { OAuthButtons } from "./oauth-buttons";

export function LoginForm() {
  const { client, login } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const [mfa, setMfa] = useState(false);
  const [pending, setPending] = useState(false);
  const [registrationAllowed, setRegistrationAllowed] = useState(false);

  useEffect(() => {
    void client.getConfig()
      .then((config) => setRegistrationAllowed(config.allow_registration))
      .catch(() => setRegistrationAllowed(false));
  }, [client]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    setPending(true);
    setError(null);
    try {
      await login({
        identifier: String(formData.get("identifier") ?? ""),
        password: String(formData.get("password") ?? ""),
        totp_code: mfa ? String(formData.get("totp_code") ?? "") : null,
      });
      router.replace(safeLocalRedirect(params.get("next"), authUIConfig.loginRedirect));
    } catch (cause) {
      if (cause instanceof AuthKitError && cause.code === "MFA_REQUIRED") {
        setMfa(true);
        setError("Enter your authenticator or recovery code.");
      } else if (cause instanceof AuthKitError) {
        setError(cause.detail);
      } else {
        setError("Unable to sign in.");
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="auth-form">
      <label htmlFor="identifier">Email or username</label>
      <input id="identifier" name="identifier" type="text" autoComplete="username" required />
      <label htmlFor="password">Password</label>
      <input id="password" name="password" type="password" autoComplete="current-password" required />
      {mfa ? (
        <>
          <label htmlFor="totp_code">Authenticator or recovery code</label>
          <input id="totp_code" name="totp_code" autoComplete="one-time-code" required />
        </>
      ) : null}
      <FormStatus error={error} />
      <button type="submit" disabled={pending}>
        {pending ? "Signing in…" : "Sign in"}
      </button>
      <OAuthButtons />
      <p className="auth-links">
        {registrationAllowed ? <Link href="/register">Create an account</Link> : null}
        <Link href="/forgot-password">Forgot password</Link>
      </p>
    </form>
  );
}
