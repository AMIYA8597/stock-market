"use client";

import { useEffect, useState } from "react";
import { marketApi } from "@/lib/api-client";
import { InstrumentInfo } from "@neuroquant/types";
import { MarketTable } from "@/components/market/MarketTable";
import { AuthGuard } from "@/components/auth/AuthGuard";

export default function StocksUniversePage(): JSX.Element {
  const [symbols, setSymbols] = useState<InstrumentInfo[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function load(): Promise<void> {
      setLoading(true);
      setError(null);

      try {
        const response = await marketApi.getUniverse();
        if (!mounted) {
          return;
        }
        setSymbols(response.instruments);
      } catch {
        if (!mounted) {
          return;
        }
        setError("Unable to load stocks universe.");
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    void load();

    return () => {
      mounted = false;
    };
  }, []);

  return (
    <AuthGuard>
    <main className="min-h-screen bg-nq-bg-base px-4 py-6 text-nq-text-primary sm:px-6 sm:py-8">
      <h1 className="text-2xl font-semibold">Stocks Universe</h1>
      <p className="mt-2 text-sm text-nq-text-secondary">Core watch universe for institutional signal workflows.</p>
      {error ? <p className="mt-2 text-sm text-nq-accent-red">{error}</p> : null}

      <div className="mt-6">
        <MarketTable instruments={symbols} isLoading={loading} />
      </div>
    </main>
    </AuthGuard>
  );
}
