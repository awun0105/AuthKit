"use client";

import { AuthKitError } from "@authkit/client";
import { RequireAuth, RequirePermission, useAuth } from "@authkit/react";
import Link from "next/link";
import { useEffect, useState } from "react";

function Documents() {
  const { client } = useAuth();
  const [rows, setRows] = useState<{ id: string; title: string }[]>([]);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    void client
      .request<{ id: string; title: string }[]>("../documents", {}, { auth: true })
      .then(setRows)
      .catch((cause: unknown) => {
        setRows([]);
        setError(cause instanceof AuthKitError ? cause.detail : "Unable to load documents.");
      });
  }, [client]);
  return (
    <>
      {error ? <p role="alert">{error}</p> : null}
      <ul>
        {rows.map((row) => (
          <li key={row.id}>{row.title}</li>
        ))}
      </ul>
    </>
  );
}

export default function HomePage() {
  const { user, logout, isLoading, error } = useAuth();
  if (isLoading) return <p>Restoring session…</p>;
  return (
    <main style={{ padding: "2rem", fontFamily: "sans-serif" }}>
      <RequireAuth fallback={<Link href="/login">Sign in</Link>}>
        <h1>Dashboard</h1>
        <p>{user?.email}</p>
        <p>
          <Link href="/account/security">Account security</Link>
        </p>
        <RequirePermission permission="documents.read" fallback={<p>Missing documents.read</p>}>
          <Documents />
        </RequirePermission>
        <RequirePermission permission="documents.create" fallback={<p>Missing documents.create</p>}>
          <button type="button">Create document</button>
        </RequirePermission>
        {error ? <p role="alert">{error.detail}</p> : null}
        <button type="button" onClick={() => void logout().catch(() => undefined)}>
          Sign out
        </button>
      </RequireAuth>
    </main>
  );
}
