import { CryptoCoinLiveContent } from "@/components/market/crypto-coin-live-content";

export default function CoinDetailPage({ params }: { params: { coin: string } }): JSX.Element {
  const coin = decodeURIComponent(params.coin).toUpperCase();
  return <CryptoCoinLiveContent coin={coin} />;
}

