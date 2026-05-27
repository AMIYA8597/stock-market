import { AppShell } from "@/components/layout/app-shell";

export function DashboardLayout({ children }: { children: React.ReactNode }): JSX.Element {
  return <AppShell>{children}</AppShell>;
}