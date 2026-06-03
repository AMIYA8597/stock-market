"use client";

import { useEffect, useState } from "react";
import { contractsApi, type PortfolioHolding } from "@/lib/contracts-api";
import { safeFormat } from "@/lib/formatters";

interface PortfolioTabProps {
  symbol: string | undefined;
}

export default function PortfolioTab({ symbol }: PortfolioTabProps): JSX.Element {
  const [holdings, setHoldings] = useState<PortfolioHolding[]>([]);
  const [totalPnl, setTotalPnl] = useState<number>(0);
  const [cashBalance, setCashBalance] = useState<number>(1000000);

  useEffect(() => {
    async function loadPortfolio() {
      try {
        const res = await contractsApi.getPortfolioHoldings();
        setHoldings(res.holdings);
        setTotalPnl(res.total_unrealized_pnl);

        const wallet = await contractsApi.getWalletBalance();
        setCashBalance(Number(wallet.wallet_balance ?? 1000000));
      } catch (e) {
        console.error(e);
      }
    }
    void loadPortfolio();
  }, [symbol]);

  return (
    <div className="flex flex-col gap-3 min-w-[500px]">
      <div className="grid grid-cols-3 gap-2">
        <div className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] p-2">
          <p className="text-[8px] uppercase tracking-wider text-[var(--nq-text-muted)] font-semibold">Cash Balance</p>
          <p className="text-xs font-bold font-mono text-[var(--nq-text-primary)]">₹{safeFormat(cashBalance, 2)}</p>
        </div>
        <div className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] p-2">
          <p className="text-[8px] uppercase tracking-wider text-[var(--nq-text-muted)] font-semibold">
            Total Unrealized P&L
          </p>
          <p className={`text-xs font-bold font-mono ${totalPnl >= 0 ? "text-[#00E676]" : "text-[#FF3B5C]"}`}>
            {totalPnl >= 0 ? "+" : ""}₹{safeFormat(totalPnl, 2)}
          </p>
        </div>
        <div className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] p-2">
          <p className="text-[8px] uppercase tracking-wider text-[var(--nq-text-muted)] font-semibold">Total Assets</p>
          <p className="text-xs font-bold font-mono text-[var(--nq-text-primary)]">
            ₹{safeFormat(cashBalance + totalPnl, 2)}
          </p>
        </div>
      </div>
      <div className="overflow-x-auto font-mono text-[10px]">
        <table className="w-full text-left font-mono">
          <thead>
            <tr className="border-b border-[var(--nq-border)] text-[var(--nq-text-muted)] uppercase tracking-wider text-[8px]">
              <th className="pb-1.5">Symbol</th>
              <th className="pb-1.5 text-right">Qty</th>
              <th className="pb-1.5 text-right">Avg Price</th>
              <th className="pb-1.5 text-right">LTP</th>
              <th className="pb-1.5 text-right">Current Value</th>
              <th className="pb-1.5 text-right">Unrealized P&L</th>
            </tr>
          </thead>
          <tbody>
            {holdings.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-4 text-center text-[var(--nq-text-muted)]">
                  No holdings in portfolio. Place simulated trades to populate.
                </td>
              </tr>
            ) : (
              holdings.map((h, index) => {
                const currentVal = h.quantity * h.ltp;
                return (
                  <tr
                    key={`${h.symbol}-${index}`}
                    className="border-b border-[rgba(255,255,255,0.04)] hover:bg-[rgba(255,255,255,0.02)] transition-colors"
                  >
                    <td className="py-1.5 font-bold text-[var(--nq-text-primary)]">{h.symbol}</td>
                    <td className="py-1.5 text-right text-[var(--nq-text-secondary)]">{h.quantity}</td>
                    <td className="py-1.5 text-right text-[var(--nq-text-secondary)]">₹{safeFormat(h.avg_buy_price, 2)}</td>
                    <td className="py-1.5 text-right text-[var(--nq-text-secondary)]">₹{safeFormat(h.ltp, 2)}</td>
                    <td className="py-1.5 text-right text-[var(--nq-text-secondary)]">₹{safeFormat(currentVal, 2)}</td>
                    <td
                      className={`py-1.5 text-right font-bold ${
                        h.unrealized_pnl >= 0 ? "text-[#00E676]" : "text-[#FF3B5C]"
                      }`}
                    >
                      {h.unrealized_pnl >= 0 ? "+" : ""}₹{safeFormat(h.unrealized_pnl, 2)}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
