import { AuthShell } from "@/components/auth/auth-shell";
import { AccountSecurity } from "@/components/auth/account-security";

export default function AccountSecurityPage() {
  return (
    <AuthShell title="Account security">
      <AccountSecurity />
    </AuthShell>
  );
}
