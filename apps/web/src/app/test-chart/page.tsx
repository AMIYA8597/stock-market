"use client";
import { useEffect, useState } from "react";
import { LightweightCandlestickChart } from "@/components/charts/LightweightCandlestickChart";
import { getApiBaseUrl } from "@/lib/runtime-config";

export default function TestChartPage() {
  const [bars, setBars] = useState([]);

  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    // Generate 5000 realistic dummy bars
    const generated = [];
    let time = new Date('2020-01-01').getTime();
    let price = 100;
    for (let i = 0; i < 5000; i++) {
      const open = price;
      const high = price + Math.random() * 5;
      const low = price - Math.random() * 5;
      const close = low + Math.random() * (high - low);
      generated.push({
        timestamp: new Date(time).toISOString(),
        open,
        high,
        low,
        close,
        volume: Math.random() * 1000000
      });
      price = close;
      // advance 1 day
      time += 24 * 60 * 60 * 1000;
    }
    setBars(generated as any);
  }, []);

  return (
    <div style={{ height: "100vh", padding: 20, background: "#0a0e18" }}>
      {errorMsg ? (
        <div style={{ color: "red" }}>{errorMsg}</div>
      ) : bars.length > 0 ? (
        <LightweightCandlestickChart 
          bars={bars} 
          height={600} 
          indicators={{ rsi: true, macd: true, atr: true, smc: true, ema50: true, bollingerBands: true }} 
          symbol="SPY" 
        />
      ) : (
        <div style={{ color: "white" }}>Loading or failed to load data...</div>
      )}
    </div>
  );
}
