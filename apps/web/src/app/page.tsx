import { PublicLayout } from '@/layouts/PublicLayout';
import { LandingPage } from '@/modules/public/LandingPage';

export default function RootPage(): JSX.Element {
  return (
    <PublicLayout>
      <LandingPage />
    </PublicLayout>
  );
}
