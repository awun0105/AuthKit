import type { TokenStore } from "./types.js";

/** In-memory token store. Default for both API and browser modes. */
export function createMemoryTokenStore(): TokenStore {
  let access: string | null = null;
  let refresh: string | null = null;
  return {
    getAccessToken: () => access,
    setAccessToken: (token) => {
      access = token;
    },
    getRefreshToken: () => refresh,
    setRefreshToken: (token) => {
      refresh = token;
    },
  };
}
