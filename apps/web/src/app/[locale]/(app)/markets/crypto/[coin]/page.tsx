import { CryptoCoinLiveContent } from "@/components/market/crypto-coin-live-content";
import { AuthGuard } from "@/components/auth/AuthGuard";

export default function CoinDetailPage({ params }: { params: { coin: string } }): JSX.Element {
  const coin = decodeURIComponent(params.coin).toUpperCase();
  return (
    <AuthGuard>
      <CryptoCoinLiveContent coin={coin} />
    </AuthGuard>
  );
}

