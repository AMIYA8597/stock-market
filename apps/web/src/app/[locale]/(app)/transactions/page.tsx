import { TransactionsPage } from '@/modules/payments/PaymentPages';
import { AuthGuard } from '@/components/auth/AuthGuard';

export default function TransactionsRoutePage(): JSX.Element {
  return (
    <AuthGuard>
      <TransactionsPage />
    </AuthGuard>
  );
}
