/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars, prefer-const, react-hooks/exhaustive-deps, react/no-unescaped-entities, react/display-name */
"use client";

import { useEffect, useState } from "react";
import { Brain, TrendingUp, AlertTriangle } from "lucide-react";
import { Card, CardHeader, CardTitle, Badge, Button } from "@neuroquant/ui";
import { useSignalFeed } from "@/hooks/useSignalFeed";
import { marketApi } from "@/lib/api-client";
import Link from "next/link";
import { cn } from "@neuroquant/ui";

export function SignalsFeedPage() {
  const [symbols, setSymbols] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  // Subscribe to signals for the loaded symbols
  const { signals, status } = useSignalFeed(symbols);

  useEffect(() => {
    async function loadUniverse() {
      try {
        const universe = await marketApi.getUniverse();
        // Subscribe to top 50 symbols for the feed
        const toSubscribe = universe.instruments.map((s: { symbol: string }) => s.symbol).slice(0, 50);
        setSymbols(toSubscribe);
      } catch (err) {
        console.error("Failed to load universe", err);
        setSymbols([]);
      } finally {
        setLoading(false);
      }
    }
    void loadUniverse();
  }, []);

  const signalList = Array.from(signals.values()).sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-xl font-bold text-nq-text-primary">Live AI Signals</h1>
          <p className="text-sm text-nq-text-secondary mt-1">Real-time signal feed across the universe.</p>
        </div>
        <Badge variant={status === "connected" ? "bull" : status === "reconnecting" ? "warning" : "default"}>
          {status === "connected" ? "Live" : status === "reconnecting" ? "Reconnecting..." : "Disconnected"}
        </Badge>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {loading ? (
          <div className="col-span-full text-center text-nq-text-secondary py-12">Loading universe...</div>
        ) : signalList.length === 0 ? (
          <div className="col-span-full flex flex-col items-center justify-center p-12 border border-dashed border-nq-border rounded-xl">
            <Brain className="h-8 w-8 text-nq-text-tertiary mb-3" />
            <p className="text-sm text-nq-text-secondary">Waiting for live signals...</p>
          </div>
        ) : (
          signalList.map((sig) => (
            <Card key={sig.symbol} className="hover:border-nq-accent/50 transition-colors">
              <CardHeader className="pb-3 flex flex-row items-start justify-between">
                <div>
                  <Link href={`/markets/stocks/${sig.symbol}`} className="font-mono font-bold text-lg text-nq-text-primary hover:text-nq-accent">
                    {sig.symbol}
                  </Link>
                  <p className="text-[10px] text-nq-text-tertiary mt-1">
                    {new Date(sig.timestamp).toLocaleTimeString()}
                  </p>
                </div>
                <Badge variant={sig.direction.includes("BUY") ? "bull" : sig.direction.includes("SELL") ? "bear" : "default"}>
                  {sig.direction.replace("_", " ")}
                </Badge>
              </CardHeader>
              <div className="px-4 pb-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-nq-text-secondary">AI Confidence</span>
                  <span className="font-mono text-sm text-nq-text-primary">{sig.confidence}%</span>
                </div>
                <div className="w-full h-1.5 rounded-full bg-nq-bg-elevated mt-2 overflow-hidden">
                  <div 
                    className={cn(
                      "h-full rounded-full transition-all",
                      sig.direction.includes("BUY") ? "bg-nq-bull" : sig.direction.includes("SELL") ? "bg-nq-bear" : "bg-nq-text-secondary"
                    )}
                    style={{ width: `${sig.confidence}%` }}
                  />
                </div>
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
