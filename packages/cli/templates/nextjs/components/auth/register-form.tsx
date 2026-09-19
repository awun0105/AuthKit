"use client";

import { AuthKitError } from "@authkit/client";
import { useAuth } from "@authkit/react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";

import { FormStatus } from "./form-status";

export function RegisterForm() {
  const { client, register, login } = useAuth();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [allowed, setAllowed] = useState<boolean | null>(null);
  const [configError, setConfigError] = useState(false);

  useEffect(() => {
    void client.getConfig()
      .then((config) => setAllowed(config.allow_registration))
      .catch(() => setConfigError(true));
  }, [client]);

  if (configError) return <p role="alert">Unable to load registration configuration.</p>;
  if (allowed === null) return <p role="status">Loading registration…</p>;
  if (!allowed) return <p role="alert">Registration is not enabled.</p>;

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "");
    const password = String(form.get("password") ?? "");
    if (password.length < 8) {
      setError("Use at least 8 characters.");
      return;
    }
    setPending(true);
    setError(null);
    try {
      await register({ email, password, full_name: String(form.get("full_name") ?? "") || null });
      try {
        await login({ identifier: email, password });
        router.replace("/");
      } catch (cause) {
        if (cause instanceof AuthKitError && cause.code === "EMAIL_NOT_VERIFIED") {
          router.replace("/verify-email");
          return;
        }
        throw cause;
      }
    } catch (cause) {
      setError(cause instanceof AuthKitError ? cause.detail : "Unable to register.");
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="auth-form">
      <label htmlFor="full_name">Name</label>
      <input id="full_name" name="full_name" type="text" autoComplete="name" />
      <label htmlFor="email">Email</label>
      <input id="email" name="email" type="email" autoComplete="email" required />
      <label htmlFor="password">Password</label>
      <input id="password" name="password" type="password" autoComplete="new-password" required minLength={8} />
      <FormStatus error={error} />
      <button type="submit" disabled={pending}>
        {pending ? "Creating…" : "Create account"}
      </button>
      <p className="auth-links">
        <Link href="/login">Already have an account</Link>
      </p>
    </form>
  );
}
