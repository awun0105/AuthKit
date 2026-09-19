"use client";

import { AuthKitError } from "@authkit/client";
import { useAuth } from "@authkit/react";
import { QRCodeSVG } from "qrcode.react";
import { type FormEvent, useState } from "react";

import { FormStatus } from "./form-status";
import { RecoveryCodes } from "./recovery-codes";

export function MfaSetup() {
  const { client, restoreSession } = useAuth();
  const [secret, setSecret] = useState<string | null>(null);
  const [qr, setQr] = useState<string | null>(null);
  const [codes, setCodes] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [pending, setPending] = useState<"setup" | "confirm" | "done" | null>(null);
  const [enabled, setEnabled] = useState(false);

  async function start() {
    setError(null);
    setSuccess(null);
    setPending("setup");
    try {
      const result = await client.mfa.setup();
      setSecret(result.secret);
      setQr(result.qr_uri);
      setCodes(result.backup_codes);
    } catch (cause) {
      setError(cause instanceof AuthKitError ? cause.detail : "Unable to start MFA setup.");
    } finally {
      setPending(null);
    }
  }

  async function onConfirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const totp = String(new FormData(event.currentTarget).get("totp_code") ?? "");
    setError(null);
    setPending("confirm");
    try {
      await client.mfa.confirm(totp);
      setEnabled(true);
      setSuccess("MFA is enabled. Save the recovery codes before continuing.");
    } catch (cause) {
      setError(cause instanceof AuthKitError ? cause.detail : "Invalid code.");
    } finally {
      setPending(null);
    }
  }

  async function finish() {
    setPending("done");
    setError(null);
    try {
      await restoreSession();
    } catch (cause) {
      setError(cause instanceof AuthKitError ? cause.detail : "Unable to refresh account security.");
      setPending(null);
    }
  }

  return (
    <div className="auth-form">
      {!qr && !enabled ? (
        <button type="button" disabled={pending !== null} onClick={() => void start()}>
          {pending === "setup" ? "Generating…" : "Generate authenticator secret"}
        </button>
      ) : null}
      {qr && !enabled ? (
        <figure>
          <QRCodeSVG value={qr} title="Authenticator setup QR code" size={192} />
          <figcaption className="auth-muted">Scan with your authenticator app.</figcaption>
        </figure>
      ) : null}
      {secret && !enabled ? <p>Manual setup key: <code>{secret}</code></p> : null}
      {qr && !enabled ? (
        <form onSubmit={onConfirm}>
          <label htmlFor="totp_code">Confirmation code</label>
          <input id="totp_code" name="totp_code" inputMode="numeric" autoComplete="one-time-code" required />
          <button type="submit" disabled={pending !== null}>
            {pending === "confirm" ? "Confirming…" : "Confirm MFA"}
          </button>
        </form>
      ) : null}
      <RecoveryCodes codes={codes} />
      {enabled ? (
        <button type="button" disabled={pending !== null} onClick={() => void finish()}>
          {pending === "done" ? "Finishing…" : "I saved these recovery codes"}
        </button>
      ) : null}
      <FormStatus error={error} success={success} />
    </div>
  );
}
