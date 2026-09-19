"use client";

import { AuthKitError, type OAuthAccount, type PublicAuthConfig, type SessionRead } from "@authkit/client";
import { useAuth } from "@authkit/react";
import { type FormEvent, useEffect, useState } from "react";

import { FormStatus } from "./form-status";
import { MfaSetup } from "./mfa-setup";

export function AccountSecurity() {
  const { user, client, logout, restoreSession } = useAuth();
  const [config, setConfig] = useState<PublicAuthConfig | null>(null);
  const [sessions, setSessions] = useState<SessionRead[]>([]);
  const [accounts, setAccounts] = useState<OAuthAccount[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    void client.getConfig().then(setConfig).catch((cause: unknown) => {
      setConfig(null);
      setError(cause instanceof AuthKitError ? cause.detail : "Unable to load account capabilities.");
    });
    if (!user) return;
    void client.listSessions().then(setSessions).catch((cause: unknown) => {
      setSessions([]);
      setError(cause instanceof AuthKitError ? cause.detail : "Unable to load sessions.");
    });
    void client.oauth.accounts().then(setAccounts).catch((cause: unknown) => {
      setAccounts([]);
      setError(cause instanceof AuthKitError ? cause.detail : "Unable to load connected accounts.");
    });
  }, [client, user]);

  async function run(action: () => Promise<unknown>, message: string) {
    setPending(true);
    setError(null);
    setSuccess(null);
    try {
      await action();
      await restoreSession();
      setSuccess(message);
    } catch (cause) {
      setError(cause instanceof AuthKitError ? cause.detail : "Unable to update account security.");
    } finally {
      setPending(false);
    }
  }

  async function onChangePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await run(
      () => client.changePassword(
        String(form.get("current_password") ?? ""),
        String(form.get("new_password") ?? ""),
      ),
      "Password changed.",
    );
  }

  async function onSetPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const password = String(new FormData(event.currentTarget).get("new_password") ?? "");
    await run(() => client.setPassword(password), "Password login enabled.");
  }

  async function onDisableMfa(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await run(
      () => client.mfa.disable(
        String(form.get("password") ?? ""),
        String(form.get("totp_or_backup_code") ?? ""),
      ),
      "MFA disabled.",
    );
  }

  async function disconnect(provider: string) {
    await run(async () => {
      await client.oauth.disconnect(provider);
      setAccounts((current) => current.filter((account) => account.provider !== provider));
    }, `${provider} disconnected.`);
  }

  async function connect(provider: string) {
    setPending(true);
    setError(null);
    try {
      sessionStorage.setItem("authkit_oauth_purpose", "connect");
      window.location.assign(await client.oauth.authorizeUrl(provider));
    } catch (cause) {
      sessionStorage.removeItem("authkit_oauth_purpose");
      setError(cause instanceof AuthKitError ? cause.detail : `Unable to connect ${provider}.`);
      setPending(false);
    }
  }

  async function onLogout() {
    setPending(true);
    setError(null);
    try {
      await logout();
    } catch (cause) {
      setError(cause instanceof AuthKitError ? cause.detail : "Unable to revoke the remote session.");
      setPending(false);
    }
  }

  if (!user) return <p>Sign in to manage account security.</p>;

  const linked = new Set(accounts.map((account) => account.provider));

  return (
    <div className="auth-form">
      <section aria-labelledby="account-heading">
        <h2 id="account-heading">Account</h2>
        <p>Signed in as {user.email}</p>
        <p>Verified: {user.is_verified ? "yes" : "no"}</p>
      </section>

      <section aria-labelledby="password-heading">
        <h2 id="password-heading">Password</h2>
        {user.has_password ? (
          <form onSubmit={onChangePassword}>
            <label htmlFor="current_password">Current password</label>
            <input id="current_password" name="current_password" type="password" autoComplete="current-password" required />
            <label htmlFor="new_password">New password</label>
            <input id="new_password" name="new_password" type="password" autoComplete="new-password" required minLength={8} />
            <button type="submit" disabled={pending}>Change password</button>
          </form>
        ) : (
          <form onSubmit={onSetPassword}>
            <label htmlFor="new_password">Add a password</label>
            <input id="new_password" name="new_password" type="password" autoComplete="new-password" required minLength={8} />
            <button type="submit" disabled={pending}>Enable password login</button>
          </form>
        )}
      </section>

      {config?.enable_mfa ? (
        <section aria-labelledby="mfa-heading">
          <h2 id="mfa-heading">Multi-factor authentication</h2>
          <p>Status: {user.mfa_enabled ? "enabled" : "disabled"}</p>
          {user.mfa_enabled ? (
            <form onSubmit={onDisableMfa}>
              <label htmlFor="mfa_password">Password</label>
              <input id="mfa_password" name="password" type="password" autoComplete="current-password" required />
              <label htmlFor="totp_or_backup_code">Authenticator or recovery code</label>
              <input id="totp_or_backup_code" name="totp_or_backup_code" autoComplete="one-time-code" required />
              <button type="submit" disabled={pending}>Disable MFA</button>
            </form>
          ) : <MfaSetup />}
        </section>
      ) : null}

      {config && config.oauth_providers.length > 0 ? (
        <section aria-labelledby="oauth-heading">
          <h2 id="oauth-heading">Connected accounts</h2>
          {config.oauth_providers.map((provider) => (
            <p key={provider}>
              <span>{provider}: {linked.has(provider) ? "connected" : "not connected"} </span>
              {linked.has(provider) ? (
                <button type="button" disabled={pending} onClick={() => void disconnect(provider)}>Disconnect</button>
              ) : (
                <button type="button" disabled={pending} onClick={() => void connect(provider)}>Connect</button>
              )}
            </p>
          ))}
        </section>
      ) : null}

      <section aria-labelledby="sessions-heading">
        <h2 id="sessions-heading">Sessions</h2>
        {sessions.length === 0 ? <p>No persistent sessions are exposed by the backend.</p> : (
          <ul>{sessions.map((session) => (
            <li key={session.session_id}>{session.user_agent ?? session.session_id}</li>
          ))}</ul>
        )}
      </section>

      <FormStatus error={error} success={success} />
      <button type="button" disabled={pending} onClick={() => void onLogout()}>Sign out</button>
    </div>
  );
}
