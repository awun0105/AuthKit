"use client";

import { AuthKitError } from "@authkit/client";
import { useAuth } from "@authkit/react";
import { type FormEvent, useEffect, useState } from "react";

import { FormStatus } from "./form-status";

export function ForgotPasswordForm() {
  const { client } = useAuth();
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [method, setMethod] = useState<"link" | "otp" | null>(null);

  useEffect(() => {
    void client.getConfig()
      .then((config) => setMethod(config.password_reset_method))
      .catch(() => setError("Unable to load password-reset configuration."));
  }, [client]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const identifier = String(new FormData(event.currentTarget).get("identifier") ?? "");
    setPending(true);
    setError(null);
    try {
      const result = await client.requestPasswordReset(identifier);
      setSuccess(result.detail);
    } catch (cause) {
      setError(cause instanceof AuthKitError ? cause.detail : "Unable to send password-reset instructions.");
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="auth-form">
      <label htmlFor="identifier">Email</label>
      <input id="identifier" name="identifier" type="email" autoComplete="email" required />
      <FormStatus error={error} success={success} />
      <button type="submit" disabled={pending || method === null}>
        {pending ? "Sending…" : method === "otp" ? "Send reset code" : "Send reset link"}
      </button>
    </form>
  );
}
