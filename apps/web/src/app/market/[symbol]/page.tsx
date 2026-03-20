import type { Metadata } from "next";
import { redirect } from "next/navigation";

interface PageProps {
  params: { symbol: string };
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  return { title: `${decodeURIComponent(params.symbol)} - Market` };
}

export default function MarketSymbolPage({ params }: PageProps): never {
  redirect(`/markets/stocks/${encodeURIComponent(params.symbol)}`);
}