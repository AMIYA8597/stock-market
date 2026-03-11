"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import type {
  WSMessage,
  WSTickMessage,
  TickData,
  ConnectionStatus,
  AlertEvent,
} from "@neuroquant/types";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
const HEARTBEAT_INTERVAL = 30_000;
const HEARTBEAT_TIMEOUT = 10_000;
const MAX_RECONNECT_DELAY = 30_000;
const INITIAL_RECONNECT_DELAY = 1_000;

interface UseWebSocketReturn {
  ticks: Map<string, TickData>;
  alerts: AlertEvent[];
  connectionStatus: ConnectionStatus;
  subscribe: (symbols: string[]) => void;
  unsubscribe: (symbols: string[]) => void;
}

export function useWebSocket(
  endpoint: string = "/ws/market",
  initialSymbols: string[] = []
): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectDelayRef = useRef(INITIAL_RECONNECT_DELAY);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout>>();
  const heartbeatTimerRef = useRef<ReturnType<typeof setInterval>>();
  const heartbeatTimeoutRef = useRef<ReturnType<typeof setTimeout>>();
  const mountedRef = useRef(true);
  const symbolsRef = useRef<Set<string>>(new Set(initialSymbols));

  const [ticks, setTicks] = useState<Map<string, TickData>>(new Map());
  const [alerts, setAlerts] = useState<AlertEvent[]>([]);
  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionStatus>("disconnected");

  const clearTimers = useCallback(() => {
    if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
    if (heartbeatTimerRef.current) clearInterval(heartbeatTimerRef.current);
    if (heartbeatTimeoutRef.current) clearTimeout(heartbeatTimeoutRef.current);
  }, []);

  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const msg: WSMessage = JSON.parse(event.data as string);

      switch (msg.type) {
        case "tick": {
          const tick: TickData = {
            symbol: msg.symbol,
            price: msg.price,
            volume: msg.volume,
            change_pct: msg.change_pct,
            timestamp: msg.timestamp,
          };
          setTicks((prev) => {
            const next = new Map(prev);
            next.set(msg.symbol, tick);
            return next;
          });
          break;
        }
        case "alert_triggered": {
          const alert: AlertEvent = {
            id: msg.alert_id,
            alert_id: msg.alert_id,
            alert_name: "",
            symbol: msg.symbol,
            alert_type: "price",
            severity: msg.severity,
            message: msg.message,
            payload: {},
            triggered_at: new Date().toISOString(),
          };
          setAlerts((prev) => [alert, ...prev].slice(0, 100));
          break;
        }
        case "heartbeat": {
          if (heartbeatTimeoutRef.current)
            clearTimeout(heartbeatTimeoutRef.current);
          break;
        }
      }
    } catch {
      // Ignore malformed messages
    }
  }, []);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const token =
        typeof window !== "undefined"
          ? localStorage.getItem("nq_access_token")
          : null;
      const url = `${WS_BASE}${endpoint}${token ? `?token=${token}` : ""}`;

      const ws = new WebSocket(url);
      wsRef.current = ws;
      setConnectionStatus("reconnecting");

      ws.onopen = () => {
        if (!mountedRef.current) return;
        setConnectionStatus("connected");
        reconnectDelayRef.current = INITIAL_RECONNECT_DELAY;

        // Subscribe to symbols
        if (symbolsRef.current.size > 0) {
          ws.send(
            JSON.stringify({
              type: "subscribe",
              symbols: Array.from(symbolsRef.current),
            })
          );
        }

        // Start heartbeat
        heartbeatTimerRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: "pong" }));
            heartbeatTimeoutRef.current = setTimeout(() => {
              ws.close();
            }, HEARTBEAT_TIMEOUT);
          }
        }, HEARTBEAT_INTERVAL);
      };

      ws.onmessage = handleMessage;

      ws.onclose = () => {
        if (!mountedRef.current) return;
        clearTimers();
        setConnectionStatus("reconnecting");

        const delay = Math.min(
          reconnectDelayRef.current,
          MAX_RECONNECT_DELAY
        );
        reconnectTimerRef.current = setTimeout(() => {
          reconnectDelayRef.current = delay * 2;
          connect();
        }, delay);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      setConnectionStatus("disconnected");
    }
  }, [endpoint, handleMessage, clearTimers]);

  const subscribe = useCallback(
    (symbols: string[]) => {
      symbols.forEach((s) => symbolsRef.current.add(s));
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "subscribe", symbols }));
      }
    },
    []
  );

  const unsubscribe = useCallback(
    (symbols: string[]) => {
      symbols.forEach((s) => symbolsRef.current.delete(s));
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "unsubscribe", symbols }));
      }
    },
    []
  );

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      clearTimers();
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect, clearTimers]);

  return { ticks, alerts, connectionStatus, subscribe, unsubscribe };
}
