"use client";

import { useEffect, useState, useCallback } from "react";
import { getWsBaseUrl } from "@/lib/runtime-config";

export interface SignalAlert {
  type: "signal_alert";
  symbol: string;
  direction: string;
  signal_score: number;
  confidence: number;
  current_price: number;
  kelly_fraction: number;
  regime: string;
  patterns_detected: string[];
  prob_buy: number;
  prob_sell: number;
  target_price_5d: number;
  stop_loss: number;
  forecast_5d: number;
  timestamp: string;
  message: string;
}

let ws: WebSocket | null = null;
let alerts: SignalAlert[] = [];
let latestAlert: SignalAlert | null = null;
let unread = 0;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let reconnectDelay = 5000;
const subscribers = new Set<() => void>();
let isConnecting = false;

function notifySubscribers() {
  subscribers.forEach((cb) => cb());
}

function connectWs() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return;
  }
  if (isConnecting) return;
  isConnecting = true;

  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }

  const cleanWsUrl = getWsBaseUrl();
  const base = cleanWsUrl.replace(/\/+$/, "");
  const cleanBase = base.replace(/\/ws$/i, "");
  const wsUrl = `${cleanBase}/ws/alerts`; 

  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    isConnecting = false;
    reconnectDelay = 5000;
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data && data.type === "signal_alert") {
        const alert = {
          ...data,
          patterns_detected: data.patterns || data.patterns_detected || [],
        } as SignalAlert;
        
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
      }
    } catch (err) {
      // Suppress
    }
  };

  ws.onclose = () => {
    ws = null;
    isConnecting = false;
    reconnectTimer = setTimeout(() => {
      connectWs();
    }, reconnectDelay);
  };

  ws.onerror = () => {
    ws?.close();
  };
}

export function useSignalAlerts() {
  // Seed with static defaults, not the live singleton — see usePriceFeed.ts for why
  // (avoids a hydration mismatch when the singleton has already advanced by the time
  // a later component mounts). The mount effect below syncs to the real value immediately.
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

    if (!ws && !isConnecting) {
      connectWs();
    }

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
