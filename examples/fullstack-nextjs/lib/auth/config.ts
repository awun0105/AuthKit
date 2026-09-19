export const authUIConfig = {
  appName: "My App",
  logo: "",
  loginRedirect: "/",
  apiBaseUrl: process.env.NEXT_PUBLIC_AUTHKIT_API_URL ?? "http://localhost:8000/auth",
};
