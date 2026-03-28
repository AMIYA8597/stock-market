"use client";

import { useMemo } from "react";

import { useOrderHistory } from "@/hooks/use-order-history";

export default function PortfolioOrdersPage(): JSX.Element {
  const { orders, clearOrders } = useOrderHistory();

  const stats = useMemo(() => {
    const buys = orders.filter((item) => item.type === "BUY").length;
    const sells = orders.filter((item) => item.type === "SELL").length;
    const turnover = orders.reduce((sum, item) => sum + Math.abs(item.net_amount), 0);
    return { buys, sells, turnover };
  }, [orders]);

  return (
    <main className="min-h-screen bg-[var(--nq-bg-base)] p-6 text-[var(--nq-text-primary)]">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Order History</h1>
          <p className="mt-1 text-xs text-[var(--nq-text-secondary)]">Executed orders from terminal ticket flow.</p>
        </div>
        <button
          type="button"
          onClick={clearOrders}
          className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-1.5 text-xs text-[var(--nq-text-secondary)] hover:border-[var(--nq-border-hover)]"
        >
          Clear history
        </button>
      </div>

      <section className="mt-4 grid gap-3 sm:grid-cols-3">
        <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-3">
          <p className="text-xs text-[var(--nq-text-secondary)]">Buy orders</p>
          <p className="mt-1 text-lg font-semibold text-[#00E676]">{stats.buys}</p>
        </div>
        <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-3">
          <p className="text-xs text-[var(--nq-text-secondary)]">Sell orders</p>
          <p className="mt-1 text-lg font-semibold text-[#FF3B5C]">{stats.sells}</p>
        </div>
        <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-3">
          <p className="text-xs text-[var(--nq-text-secondary)]">Notional turnover</p>
          <p className="mt-1 text-lg font-semibold">{stats.turnover.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</p>
        </div>
      </section>

      <section className="mt-4 rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-3">
        <div className="max-h-[70vh] overflow-y-auto">
          <table className="min-w-full text-xs">
            <thead>
              <tr className="border-b border-[var(--nq-border)] text-[var(--nq-text-secondary)]">
                <th className="px-2 py-2 text-left">Time</th>
                <th className="px-2 py-2 text-left">Side</th>
                <th className="px-2 py-2 text-left">Symbol</th>
                <th className="px-2 py-2 text-right">Quantity</th>
                <th className="px-2 py-2 text-right">Price</th>
                <th className="px-2 py-2 text-right">Net Amount</th>
                <th className="px-2 py-2 text-left">Source</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.transaction_id} className="border-b border-[var(--nq-border)]/70">
                  <td className="px-2 py-2">{new Date(order.timestamp).toLocaleString()}</td>
                  <td className={`px-2 py-2 ${order.type === "BUY" ? "text-[#00E676]" : "text-[#FF3B5C]"}`}>{order.type}</td>
                  <td className="px-2 py-2">{order.symbol}</td>
                  <td className="px-2 py-2 text-right">{order.quantity.toLocaleString("en-IN", { maximumFractionDigits: 4 })}</td>
                  <td className="px-2 py-2 text-right">{order.price.toLocaleString("en-IN", { maximumFractionDigits: 4 })}</td>
                  <td className="px-2 py-2 text-right">{order.net_amount.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</td>
                  <td className="px-2 py-2 uppercase">{order.source}</td>
                </tr>
              ))}
              {orders.length === 0 ? (
                <tr>
                  <td className="px-2 py-3 text-[var(--nq-text-secondary)]" colSpan={7}>
                    No executed orders yet. Place trades from the terminal order ticket.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
