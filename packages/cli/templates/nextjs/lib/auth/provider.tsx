"use client";

import { AuthProvider } from "@authkit/react";
import type { ReactNode } from "react";

import { authClient } from "./client";

export function AppAuthProvider({ children }: { children: ReactNode }) {
  return <AuthProvider client={authClient}>{children}</AuthProvider>;
}
