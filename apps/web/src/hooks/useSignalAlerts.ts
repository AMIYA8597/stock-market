"use client";

import { useEffect, useState, useCallback } from "react";
import { realtime, isWsEnvelope } from "@/lib/realtime";

export interface SignalAlert {
  type: "signal_alert" | "signal" | "progress";
  symbol: string;
  direction: string;
  signal_score: number;
  confidence: number;
  // The backend's ws_signals route (app/websocket/router.py) never sends a
  // current price alongside a signal - only signal/confidence/direction.
  // Keep this optional rather than pretending it is always available.
  current_price?: number;
  kelly_fraction?: number;
  regime?: string;
  patterns_detected?: string[];
  prob_buy?: number;
  prob_sell?: number;
  target_price_5d?: number;
  stop_loss?: number;
  forecast_5d?: number;
  timestamp: string;
  message: string;
}

let alerts: SignalAlert[] = [];
let latestAlert: SignalAlert | null = null;
let unread = 0;
const subscribers = new Set<() => void>();

let initialized = false;

function notifySubscribers() {
  subscribers.forEach((cb) => cb());
}

function initGlobalListener() {
  if (initialized) return;
  initialized = true;

  realtime.onMessage((raw) => {
    if (!isWsEnvelope(raw) || (raw.type !== "signal" && raw.type !== "signal_alert")) return;
    if (!raw.symbol) return;

    // The real envelope nests signal/confidence/direction under `payload` and
    // carries the observation time as `ts` - it never sends a flat
    // direction/signal_score/current_price/message at the top level, so
    // spreading `message` directly (the previous implementation) produced an
    // alert whose required fields were all `undefined` in production.
    const payload = raw.payload ?? {};
    const direction = typeof payload.direction === "string" ? payload.direction : "NEUTRAL";
    const confidence = typeof payload.confidence === "number" ? payload.confidence : 0;
    const signalScore = typeof payload.signal === "number" ? payload.signal : 0;

    const alert: SignalAlert = {
      type: raw.type as SignalAlert["type"],
      symbol: raw.symbol,
      direction,
      signal_score: signalScore,
      confidence,
      timestamp: raw.ts ?? new Date().toISOString(),
      message: `${direction.replace(/_/g, " ")} signal on ${raw.symbol} (confidence ${(confidence * 100).toFixed(0)}%)`,
    };

    alerts = [alert, ...alerts];
    if (alerts.length > 50) {
      alerts = alerts.slice(0, 50);
    }

    latestAlert = alert;
    unread += 1;

    if (
      typeof window !== "undefined" &&
      "Notification" in window &&
      Notification.permission === "granted"
    ) {
      new Notification(`${alert.direction} Alert: ${alert.symbol}`, {
        body: alert.message,
        icon: "/favicon.ico",
        tag: alert.symbol,
      });
    }

    notifySubscribers();
  });

  realtime.connect();
}

export function useSignalAlerts() {
  const [localAlerts, setLocalAlerts] = useState<SignalAlert[]>(() => []);
  const [localLatest, setLocalLatest] = useState<SignalAlert | null>(() => null);
  const [localUnread, setLocalUnread] = useState<number>(() => 0);

  const markAllRead = useCallback(() => {
    unread = 0;
    setLocalUnread(0);
    notifySubscribers();
  }, []);

  useEffect(() => {
    if (typeof window !== "undefined" && "Notification" in window) {
      if (Notification.permission === "default") {
        void Notification.requestPermission();
      }
    }
  }, []);

  useEffect(() => {
    const handleChange = () => {
      setLocalAlerts([...alerts]);
      setLocalLatest(latestAlert);
      setLocalUnread(unread);
    };

    subscribers.add(handleChange);
    handleChange(); // Initial sync

    initGlobalListener();

    return () => {
      subscribers.delete(handleChange);
    };
  }, []);

  return {
    alerts: localAlerts,
    latestAlert: localLatest,
    unread: localUnread,
    markAllRead,
  };
}
