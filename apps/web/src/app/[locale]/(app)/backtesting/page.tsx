import type { Metadata } from "next";
import { redirect } from "@/i18n/navigation";

export const metadata: Metadata = { title: "Backtesting" };

export default async function BacktestingPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<never> {
  const { locale } = await params;
  return redirect({ href: "/backtest-lab", locale });
}
