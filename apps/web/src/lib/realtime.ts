"use client";
import { createClient } from '@/lib/supabase/client';

import { getWsBaseUrl } from "@/lib/runtime-config";

export type ConnectionStatus = "connected" | "reconnecting" | "disconnected";

// The shape every backend WS route (app/websocket/router.py) actually sends:
// {"type": ..., "symbol": ..., "payload": {...}, "ts": ISO-8601, "source": ...}.
// Note the observation time field is `ts`, not `timestamp`.
export interface WsEnvelope {
  type: string;
  channel?: string;
  symbol?: string;
  payload?: Record<string, unknown>;
  ts?: string;
  source?: string;
}

export function isWsEnvelope(message: unknown): message is WsEnvelope {
  return (
    typeof message === "object" &&
    message !== null &&
    typeof (message as { type?: unknown }).type === "string"
  );
}

type MessageHandler = (message: unknown) => void;

class RealtimeManager {
  private ws: WebSocket | null = null;
  private status: ConnectionStatus = "disconnected";
  private statusSubscribers = new Set<(status: ConnectionStatus) => void>();
  private messageHandlers = new Set<MessageHandler>();
  
  private symbolRefs = new Map<string, number>();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectDelay = 1000;

  public async connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    this.setStatus("reconnecting");

    const cleanWsUrl = getWsBaseUrl();
    const base = cleanWsUrl.replace(/\/+$/, "");
    const wsBase = base.endsWith("/ws") ? base : `${base}/ws`;
    
    let ticket = "";
    try {
        const supabase = createClient();
        const { data: { session } } = await supabase.auth.getSession();
        const token = session?.access_token;
        if (token) {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const res = await fetch(`${apiUrl}/api/v1/websocket_url/ticket`, {
                method: "POST",
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                ticket = data.ticket;
            }
        }
    } catch (e) {}

    const wsUrl = `${wsBase}/stream?ticket=${ticket}`;
    
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.setStatus("connected");
      this.reconnectDelay = 1000;
      
      const activeSymbols = Array.from(this.symbolRefs.keys());
      if (activeSymbols.length > 0) {
        this.ws?.send(JSON.stringify({ action: "subscribe", symbols: activeSymbols }));
      }
    };

    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data as string);
        this.messageHandlers.forEach(handler => handler(message));
      } catch {
        // ignore
      }
    };

    this.ws.onclose = () => {
      this.ws = null;
      this.setStatus("reconnecting");
      
      // Exponential backoff + jitter
      this.reconnectTimer = setTimeout(() => {
        // const jitter = Math.random() * 500;
        this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000);
        this.connect();
      }, this.reconnectDelay + (Math.random() * 500));
    };

    this.ws.onerror = () => {
      this.ws?.close(); // triggers onclose
    };
  }
  
  public subscribe(symbols: string[]) {
    let changed = false;
    const addedSymbols: string[] = [];
    
    for (const s of symbols) {
      if (!s) continue;
      const sym = s.toUpperCase();
      const count = this.symbolRefs.get(sym) || 0;
      this.symbolRefs.set(sym, count + 1);
      if (count === 0) {
        addedSymbols.push(sym);
        changed = true;
      }
    }
    
    if (changed && this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action: "subscribe", symbols: addedSymbols }));
    }
    
    if (this.symbolRefs.size > 0 && !this.ws) {
      this.connect();
    }
  }
  
  public unsubscribe(symbols: string[]) {
    let changed = false;
    const removedSymbols: string[] = [];
    
    for (const s of symbols) {
      if (!s) continue;
      const sym = s.toUpperCase();
      const count = this.symbolRefs.get(sym);
      if (count !== undefined) {
        if (count <= 1) {
          this.symbolRefs.delete(sym);
          removedSymbols.push(sym);
          changed = true;
        } else {
          this.symbolRefs.set(sym, count - 1);
        }
      }
    }
    
    if (changed && this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action: "unsubscribe", symbols: removedSymbols }));
    }
  }

  public onStatusChange(callback: (status: ConnectionStatus) => void) {
    this.statusSubscribers.add(callback);
    callback(this.status);
    return () => {
      this.statusSubscribers.delete(callback);
    };
  }
  
  public onMessage(callback: MessageHandler) {
    this.messageHandlers.add(callback);
    return () => {
      this.messageHandlers.delete(callback);
    };
  }
  
  public getStatus() {
    return this.status;
  }
  
  private setStatus(status: ConnectionStatus) {
    this.status = status;
    this.statusSubscribers.forEach(cb => cb(status));
  }
}

export const realtime = new RealtimeManager();
