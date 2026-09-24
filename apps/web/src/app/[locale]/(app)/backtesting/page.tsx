import type { Metadata } from "next";
import { redirect } from "next/navigation";

export const metadata: Metadata = { title: "Backtesting" };

export default function BacktestingPage(): never {
  redirect("/backtest-lab");
}
