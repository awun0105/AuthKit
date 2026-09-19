import type { ReactNode } from "react";

import { AppAuthProvider } from "@/lib/auth/provider";
import "./globals.css";

export const metadata = { title: "AuthKit example" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppAuthProvider>{children}</AppAuthProvider>
      </body>
    </html>
  );
}
