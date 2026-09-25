import { NotificationCenterPage } from '@/modules/notifications/NotificationCenterPage';
import { AuthGuard } from '@/components/auth/AuthGuard';

export default function NotificationsRoutePage(): JSX.Element {
  return (
    <AuthGuard>
      <NotificationCenterPage />
    </AuthGuard>
  );
}
