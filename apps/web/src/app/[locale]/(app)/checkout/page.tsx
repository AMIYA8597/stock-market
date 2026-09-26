import { CheckoutPage } from '@/modules/payments/PaymentPages';
import { AuthGuard } from '@/components/auth/AuthGuard';

export default function CheckoutRoutePage(): JSX.Element {
  return (
    <AuthGuard>
      <CheckoutPage />
    </AuthGuard>
  );
}
