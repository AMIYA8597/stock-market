import { DashboardLayout } from '@/layouts/DashboardLayout';

export default function DashboardRouteLayout({ children }: { children: React.ReactNode }): JSX.Element {
  return <DashboardLayout>{children}</DashboardLayout>;
}
