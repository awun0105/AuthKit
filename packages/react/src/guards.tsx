import type { ReactNode } from "react";

import { useAuth } from "./hooks.js";

export function RequireAuth({
  children,
  fallback = null,
}: {
  children: ReactNode;
  fallback?: ReactNode;
}) {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return fallback;
  if (!isAuthenticated) return fallback;
  return children;
}

export function RequireRole({
  role,
  children,
  fallback = null,
}: {
  role: string;
  children: ReactNode;
  fallback?: ReactNode;
}) {
  const { isLoading, hasRole } = useAuth();
  if (isLoading) return fallback;
  if (!hasRole(role)) return fallback;
  return children;
}

export function RequirePermission({
  permission,
  children,
  fallback = null,
}: {
  permission: string;
  children: ReactNode;
  fallback?: ReactNode;
}) {
  const { isLoading, hasPermission } = useAuth();
  if (isLoading) return fallback;
  if (!hasPermission(permission)) return fallback;
  return children;
}
