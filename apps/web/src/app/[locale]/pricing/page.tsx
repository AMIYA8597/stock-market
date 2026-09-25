import { PublicLayout } from '@/layouts/PublicLayout';
import { PricingPage } from '@/modules/payments/PaymentPages';

export default function PricingRoutePage(): JSX.Element {
  return (
    <PublicLayout>
      <PricingPage />
    </PublicLayout>
  );
}
