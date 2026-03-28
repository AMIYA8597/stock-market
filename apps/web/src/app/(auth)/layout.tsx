import { AuthLayout } from '@/layouts/AuthLayout';

export default function AuthRouteLayout({ children }: { children: React.ReactNode }): JSX.Element {
  return <AuthLayout>{children}</AuthLayout>;
}
