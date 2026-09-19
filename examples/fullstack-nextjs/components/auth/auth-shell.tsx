import type { ReactNode } from "react";

import { authUIConfig } from "@/lib/auth/config";

export function AuthShell({ title, children }: { title: string; children: ReactNode }) {
  return (
    <main className="auth-shell min-h-dvh px-4 py-8 sm:px-6">
      <section className="auth-card w-full max-w-md" aria-labelledby="auth-title">
        {authUIConfig.logo ? (
          // The scaffold accepts arbitrary consumer-owned logo URLs.
          // eslint-disable-next-line @next/next/no-img-element
          <img className="auth-logo" src={authUIConfig.logo} alt="" />
        ) : null}
        <p className="auth-app">{authUIConfig.appName}</p>
        <h1 id="auth-title">{title}</h1>
        {children}
      </section>
    </main>
  );
}
