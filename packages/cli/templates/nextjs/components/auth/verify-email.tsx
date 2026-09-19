"use client";

import { AuthKitError } from "@authkit/client";
import { useAuth } from "@authkit/react";
import { useSearchParams } from "next/navigation";
import { type FormEvent, useEffect, useRef, useState } from "react";

import { FormStatus } from "./form-status";

export function VerifyEmail() {
  const { client } = useAuth();
  const params = useSearchParams();
  const token = params.get("token") ?? "";
  const [method, setMethod] = useState<"link" | "otp" | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<"verify" | "resend" | null>(null);
  const startedForToken = useRef<string | null>(null);

  useEffect(() => {
    const requestKey = token || "no-token";
    if (startedForToken.current === requestKey) return;
    startedForToken.current = requestKey;
    void client.getConfig()
      .then(async (config) => {
        setMethod(config.verification_method);
        if (config.verification_method === "link" && token) {
          setPending("verify");
          try {
            await client.verifyEmail(token);
            setSuccess("Email verified. You can sign in.");
          } catch (cause) {
            setError(cause instanceof AuthKitError ? cause.detail : "This verification link is invalid or expired.");
          } finally {
            setPending(null);
          }
        }
      })
      .catch(() => {
        setError("Unable to load email-verification configuration.");
      });
  }, [client, token]);

  async function onVerifyOtp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setPending("verify");
    setError(null);
    try {
      await client.verifyOtp(String(form.get("identifier") ?? ""), String(form.get("otp") ?? ""));
      setSuccess("Email verified. You can sign in.");
    } catch (cause) {
      setError(cause instanceof AuthKitError ? cause.detail : "The verification code is invalid or expired.");
    } finally {
      setPending(null);
    }
  }

  async function onResend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const identifier = String(new FormData(event.currentTarget).get("identifier") ?? "");
    setPending("resend");
    setError(null);
    try {
      const result = await client.resendVerification(identifier);
      setSuccess(result.detail);
    } catch (cause) {
      setError(cause instanceof AuthKitError ? cause.detail : "Unable to resend verification.");
    } finally {
      setPending(null);
    }
  }

  if (method === null && !error) return <p role="status">Loading verification…</p>;

  return (
    <div className="auth-form">
      <FormStatus error={error} success={success} />
      {method === "link" && pending === "verify" ? <p role="status">Verifying email…</p> : null}
      {method === "otp" ? (
        <form onSubmit={onVerifyOtp} className="auth-form">
          <label htmlFor="verification-identifier">Email or phone</label>
          <input id="verification-identifier" name="identifier" autoComplete="username" required />
          <label htmlFor="verification-code">Verification code</label>
          <input id="verification-code" name="otp" inputMode="numeric" autoComplete="one-time-code" required />
          <button type="submit" disabled={pending !== null}>
            {pending === "verify" ? "Verifying…" : "Verify email"}
          </button>
        </form>
      ) : null}
      <form onSubmit={onResend} className="auth-form">
        <label htmlFor="resend-identifier">Email or phone</label>
        <input id="resend-identifier" name="identifier" autoComplete="username" required />
        <button type="submit" disabled={pending !== null}>
          {pending === "resend" ? "Sending…" : method === "otp" ? "Resend verification code" : "Resend verification link"}
        </button>
      </form>
    </div>
  );
}
