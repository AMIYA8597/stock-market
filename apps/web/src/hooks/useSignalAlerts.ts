"use client";

import { useEffect, useState, useCallback } from "react";
import { realtime } from "@/lib/realtime";

export interface SignalAlert {
  type: "signal_alert" | "signal" | "progress";
  symbol: string;
  direction: string;
  signal_score: number;
  confidence: number;
  current_price: number;
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
  payload?: any;
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

  realtime.onMessage((message) => {
    if (message.type === "signal" || message.type === "signal_alert") {
      const alert = {
        ...message,
        patterns_detected: message.patterns || message.patterns_detected || [],
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
        new Notification(`${alert.payload?.direction || alert.direction} Alert: ${alert.symbol}`, {
          body: alert.message || `Confidence: ${alert.payload?.confidence || alert.confidence}`,
          icon: "/favicon.ico",
          tag: alert.symbol,
        });
      }
      
      notifySubscribers();
    }
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
