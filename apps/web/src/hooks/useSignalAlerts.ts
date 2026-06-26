"use client";

import { useEffect, useRef, useState, useCallback } from "react";
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

const cleanWsUrl = getWsBaseUrl();

export function useSignalAlerts() {
  const [alerts, setAlerts] = useState<SignalAlert[]>([]);
  const [latestAlert, setLatestAlert] = useState<SignalAlert | null>(null);
  const [unread, setUnread] = useState<number>(0);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Mark all alerts as read
  const markAllRead = useCallback(() => {
    setUnread(0);
  }, []);

  // Request browser Notification permissions
  useEffect(() => {
    if (typeof window !== "undefined" && "Notification" in window) {
      if (Notification.permission === "default") {
        void Notification.requestPermission();
      }
    }
  }, []);

  const connect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      return;
    }

    const base = cleanWsUrl.replace(/\/+$/, "");
    const cleanBase = base.replace(/\/ws$/i, "");
    const wsUrl = `${cleanBase}/ws/alerts`; // Resolved WebSocket URL: ws://host:port/ws/alerts (no double slash)
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data && data.type === "signal_alert") {
          const alert = {
            ...data,
            patterns_detected: data.patterns || data.patterns_detected || [],
          } as SignalAlert;
          
          setAlerts((prev) => {
            const next = [alert, ...prev];
            // Cap at 50 entries
            if (next.length > 50) {
              return next.slice(0, 50);
            }
            return next;
          });

          setLatestAlert(alert);
          setUnread((prev) => prev + 1);

          // Fire OS notification
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
        }
      } catch (err) {
        // Suppress malformed WS messages
      }
    };

    ws.onclose = () => {
      reconnectTimerRef.current = setTimeout(() => {
        connect();
      }, 5000);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, []);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  return {
    alerts,
    latestAlert,
    unread,
    markAllRead,
  };
}
