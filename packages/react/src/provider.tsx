import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import { AuthKitError, type AuthKitClient, type AuthUser, type LoginRequest, type RegisterRequest } from "@authkit/client";

import { AuthContext, type AuthContextValue } from "./context.js";

export function AuthProvider({
  client,
  children,
}: {
  client: AuthKitClient;
  children: ReactNode;
}) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<AuthKitError | null>(null);

  const rememberError = useCallback((cause: unknown): AuthKitError => {
    const authError = cause instanceof AuthKitError
      ? cause
      : new AuthKitError("UNKNOWN_ERROR", cause instanceof Error ? cause.message : "Authentication failed");
    setError(authError);
    return authError;
  }, []);

  const restoreSession = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const restored = await client.restoreSession();
      setUser(restored);
      return restored;
    } catch (cause) {
      setUser(null);
      throw rememberError(cause);
    } finally {
      setIsLoading(false);
    }
  }, [client, rememberError]);

  useEffect(() => {
    let cancelled = false;
    void Promise.resolve()
      .then(() => {
        if (cancelled) return null;
        setIsLoading(true);
        setUser(null);
        setError(null);
        return client.restoreSession();
      })
      .then((restored) => {
        if (!cancelled) setUser(restored);
      })
      .catch((cause: unknown) => {
        if (!cancelled) {
          setUser(null);
          rememberError(cause);
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [client, rememberError]);

  const login = useCallback(
    async (input: LoginRequest) => {
      setError(null);
      try {
        const result = await client.login(input);
        setUser(result.user);
        return result;
      } catch (cause) {
        throw rememberError(cause);
      }
    },
    [client, rememberError],
  );

  const register = useCallback(
    async (input: RegisterRequest) => {
      setError(null);
      try {
        return await client.register(input);
      } catch (cause) {
        throw rememberError(cause);
      }
    },
    [client, rememberError],
  );

  const logout = useCallback(async () => {
    setError(null);
    try {
      await client.logout();
    } catch (cause) {
      throw rememberError(cause);
    } finally {
      setUser(null);
    }
  }, [client, rememberError]);

  const refreshSession = useCallback(async () => {
    setError(null);
    try {
      await client.refresh();
      const current = await client.getCurrentUser();
      setUser(current);
    } catch (cause) {
      setUser(null);
      throw rememberError(cause);
    }
  }, [client, rememberError]);

  const hasRole = useCallback((role: string) => Boolean(user?.roles.includes(role)), [user]);
  const hasPermission = useCallback(
    (permission: string) => Boolean(user?.scopes.includes(permission)),
    [user],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      client,
      user,
      isAuthenticated: user !== null,
      isLoading,
      error,
      login,
      register,
      logout,
      restoreSession,
      refreshSession,
      hasRole,
      hasPermission,
    }),
    [client, user, isLoading, error, login, register, logout, restoreSession, refreshSession, hasRole, hasPermission],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
