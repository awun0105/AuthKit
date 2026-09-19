import { createContext } from "react";

import type { AuthKitClient, AuthKitError, AuthUser } from "@authkit/client";

export type AuthContextValue = {
  client: AuthKitClient;
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: AuthKitError | null;
  login: AuthKitClient["login"];
  register: AuthKitClient["register"];
  logout: () => Promise<void>;
  restoreSession: () => Promise<AuthUser | null>;
  refreshSession: () => Promise<void>;
  hasRole: (role: string) => boolean;
  hasPermission: (permission: string) => boolean;
};

export const AuthContext = createContext<AuthContextValue | null>(null);
