import { DashboardOverview } from '@/modules/dashboard/DashboardOverview';
import { AuthGuard } from "@/components/auth/AuthGuard";

export default function DashboardPage(): JSX.Element {
  return (
    <AuthGuard>
      <DashboardOverview />
    </AuthGuard>
  );
}
