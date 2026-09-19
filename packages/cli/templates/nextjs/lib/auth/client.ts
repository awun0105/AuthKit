"use client";

import { createAuthClient } from "@authkit/client";

import { authUIConfig } from "./config";

export const authClient = createAuthClient({
  baseUrl: authUIConfig.apiBaseUrl,
  mode: "browser",
});
