import type { Metadata } from "next";
import { BacktestingContent } from "@/components/backtesting/backtesting-content";

export const metadata: Metadata = { title: "Backtesting" };

export default function BacktestingPage() {
  return <BacktestingContent />;
}
