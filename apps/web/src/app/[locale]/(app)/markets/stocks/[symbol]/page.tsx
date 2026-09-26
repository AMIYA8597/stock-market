import type { Metadata } from "next";
import { StockLiveContractContent } from "@/components/market/stock-live-contract-content";
import { AuthGuard } from "@/components/auth/AuthGuard";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: { params: { symbol: string } }): Promise<Metadata> {
  return { title: `Stock Detail | ${params.symbol}` };
}

export default function StockDetailPage({ params }: { params: { symbol: string } }): JSX.Element {
  const symbol = decodeURIComponent(params.symbol).toUpperCase();
  return (
    <AuthGuard>
      <StockLiveContractContent symbol={symbol} />
    </AuthGuard>
  );
}
