"use client";

import { useMemo } from "react";
import { safeFormat } from "@/lib/formatters";

interface OptionChainTabProps {
  currentPrice: number;
}

export default function OptionChainTab({ currentPrice }: OptionChainTabProps): JSX.Element {
  const optionChainData = useMemo(() => {
    const baseStrike = Math.round(currentPrice / 5) * 5;
    const strikes = [];
    for (let i = -4; i <= 4; i++) {
      strikes.push(baseStrike + i * 5);
    }
    return strikes.map((strike, index) => {
      const isITM_Call = currentPrice > strike;
      const isITM_Put = currentPrice < strike;
      const callVal = Math.max(0.5, currentPrice - strike + (5 + (index % 3) * 1.5));
      const putVal = Math.max(0.5, strike - currentPrice + (5 + (index % 4) * 1.2));
      return {
        strike,
        callBid: callVal * 0.98,
        callAsk: callVal * 1.02,
        callOI: Math.round((20 - Math.abs(currentPrice - strike) / 5) * 100) * 10,
        putBid: putVal * 0.98,
        putAsk: putVal * 1.02,
        putOI: Math.round((20 - Math.abs(currentPrice - strike) / 5) * 120) * 10,
        isITM_Call,
        isITM_Put,
      };
    });
  }, [currentPrice]);

  const handlePrefillOption = (side: "BUY" | "SELL", price: number) => {
    const event = new CustomEvent("prefill-order-ticket", {
      detail: {
        side,
        price,
        quantity: 10,
      },
    });
    window.dispatchEvent(event);
  };

  return (
    <div className="min-w-[500px] overflow-x-auto">
      <table className="w-full text-left text-[10px] font-mono">
        <thead>
          <tr className="border-b border-[var(--nq-border)] text-[var(--nq-text-muted)] uppercase tracking-wider text-[8px]">
            <th className="pb-1.5 text-center border-r border-[rgba(255,255,255,0.05)]" colSpan={3}>
              Calls
            </th>
            <th className="pb-1.5 text-center border-x border-[var(--nq-border)] bg-[rgba(255,255,255,0.04)]">
              Strike
            </th>
            <th className="pb-1.5 text-center border-l border-[rgba(255,255,255,0.05)]" colSpan={3}>
              Puts
            </th>
          </tr>
          <tr className="border-b border-[var(--nq-border)] text-[var(--nq-text-secondary)] text-[8px]">
            <th className="py-1">OI</th>
            <th className="py-1">Bid</th>
            <th className="py-1 border-r border-[rgba(255,255,255,0.05)]">Ask</th>
            <th className="py-1 text-center border-x border-[var(--nq-border)] bg-[rgba(255,255,255,0.04)]">
              Price
            </th>
            <th className="py-1 border-l border-[rgba(255,255,255,0.05)]">Bid</th>
            <th className="py-1">Ask</th>
            <th className="py-1 text-right">OI</th>
          </tr>
        </thead>
        <tbody>
          {optionChainData.map((row) => (
            <tr
              key={row.strike}
              className="border-b border-[rgba(255,255,255,0.04)] hover:bg-[rgba(255,255,255,0.02)] transition-colors"
            >
              <td className={`py-1 ${row.isITM_Call ? "bg-[rgba(0,212,245,0.06)]" : ""} text-[var(--nq-text-muted)]`}>
                {row.callOI.toLocaleString()}
              </td>
              <td
                onClick={() => handlePrefillOption("SELL", row.callBid)}
                className={`py-1 cursor-pointer hover:bg-[rgba(0,230,118,0.15)] hover:text-white transition ${
                  row.isITM_Call ? "bg-[rgba(0,212,245,0.06)]" : ""
                } text-[var(--nq-accent-green)]`}
                title="Sell Call Option at Bid"
              >
                {safeFormat(row.callBid, 2)}
              </td>
              <td
                onClick={() => handlePrefillOption("BUY", row.callAsk)}
                className={`py-1 cursor-pointer hover:bg-[rgba(0,230,118,0.15)] hover:text-white transition border-r border-[rgba(255,255,255,0.05)] ${
                  row.isITM_Call ? "bg-[rgba(0,212,245,0.06)]" : ""
                } text-[var(--nq-accent-green)]`}
                title="Buy Call Option at Ask"
              >
                {safeFormat(row.callAsk, 2)}
              </td>
              <td className="py-1 text-center font-bold border-x border-[var(--nq-border)] bg-[rgba(255,255,255,0.04)] text-[var(--nq-text-primary)]">
                {safeFormat(row.strike, 2)}
              </td>
              <td
                onClick={() => handlePrefillOption("SELL", row.putBid)}
                className={`py-1 cursor-pointer hover:bg-[rgba(255,59,92,0.15)] hover:text-white transition border-l border-[rgba(255,255,255,0.05)] ${
                  row.isITM_Put ? "bg-[rgba(0,212,245,0.06)]" : ""
                } text-[var(--nq-accent-green)]`}
                title="Sell Put Option at Bid"
              >
                {safeFormat(row.putBid, 2)}
              </td>
              <td
                onClick={() => handlePrefillOption("BUY", row.putAsk)}
                className={`py-1 cursor-pointer hover:bg-[rgba(255,59,92,0.15)] hover:text-white transition ${
                  row.isITM_Put ? "bg-[rgba(0,212,245,0.06)]" : ""
                } text-[var(--nq-accent-green)]`}
                title="Buy Put Option at Ask"
              >
                {safeFormat(row.putAsk, 2)}
              </td>
              <td className={`py-1 text-right ${row.isITM_Put ? "bg-[rgba(0,212,245,0.06)]" : ""} text-[var(--nq-text-muted)]`}>
                {row.putOI.toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
