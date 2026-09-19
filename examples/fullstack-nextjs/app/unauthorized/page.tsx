import { AuthShell } from "@/components/auth/auth-shell";
import Link from "next/link";

export default function UnauthorizedPage() {
  return (
    <AuthShell title="Not allowed">
      <p>You do not have permission to view this page.</p>
      <Link href="/">Go home</Link>
    </AuthShell>
  );
}
