import type { Metadata } from "next";
import { StockDetailContent } from "@/components/market/stock-detail-content";

interface PageProps {
  params: { symbol: string };
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  return { title: `${decodeURIComponent(params.symbol)} — Market` };
}

export default function StockDetailPage({ params }: PageProps) {
  return <StockDetailContent symbol={decodeURIComponent(params.symbol)} />;
}
