"use client";

import { AuthKitError } from "@authkit/client";
import { useAuth } from "@authkit/react";
import { useSearchParams } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";

import { FormStatus } from "./form-status";

export function ResetPasswordForm() {
  const { client } = useAuth();
  const params = useSearchParams();
  const token = params.get("token") ?? "";
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [method, setMethod] = useState<"link" | "otp" | null>(null);

  useEffect(() => {
    void client.getConfig().then((config) => setMethod(config.password_reset_method)).catch(() => {
      setError("Unable to load password-reset configuration.");
    });
  }, [client]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const password = String(form.get("password") ?? "");
    if (method === "link" && !token) {
      setError("This reset link is missing a token.");
      return;
    }
    setPending(true);
    setError(null);
    try {
      const result = method === "otp"
        ? await client.resetPasswordOtp(
            String(form.get("identifier") ?? ""),
            String(form.get("otp") ?? ""),
            password,
          )
        : await client.resetPassword(token, password);
      setSuccess(result.detail);
    } catch (cause) {
      setError(cause instanceof AuthKitError ? cause.detail : "Unable to reset password.");
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="auth-form">
      {method === "otp" ? (
        <>
          <label htmlFor="identifier">Email or phone</label>
          <input id="identifier" name="identifier" autoComplete="username" required />
          <label htmlFor="otp">Reset code</label>
          <input id="otp" name="otp" inputMode="numeric" autoComplete="one-time-code" required />
        </>
      ) : null}
      <label htmlFor="password">New password</label>
      <input id="password" name="password" type="password" autoComplete="new-password" required minLength={8} />
      <FormStatus error={error} success={success} />
      <button type="submit" disabled={pending || method === null || (method === "link" && !token)}>
        {pending ? "Saving…" : "Reset password"}
      </button>
    </form>
  );
}
