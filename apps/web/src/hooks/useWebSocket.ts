'use client';

import { useEffect, useRef, useState, useCallback } from 'react';

interface WebSocketMessage {
  type: string;
  data?: unknown;
}

interface UseWebSocketOptions {
  url: string;
  onMessage?: (data: WebSocketMessage) => void;
  onError?: (error: Error) => void;
  onOpen?: () => void;
  onClose?: () => void;
  reconnect?: boolean;
  maxRetries?: number;
}

export function useWebSocket({
  url,
  onMessage,
  onError,
  onOpen,
  onClose,
  reconnect = true,
  maxRetries = 5,
}: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const retryCountRef = useRef(0);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    if (isConnecting) return;

    setIsConnecting(true);
    try {
      wsRef.current = new WebSocket(url);

      wsRef.current.onopen = () => {
        console.log('WebSocket connected:', url);
        setIsConnected(true);
        setIsConnecting(false);
        retryCountRef.current = 0;
        onOpen?.();
      };

      wsRef.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          onMessage?.(message);
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      wsRef.current.onerror = () => {
        const error = new Error('WebSocket error');
        console.error('WebSocket error:', error);
        onError?.(error);
      };

      wsRef.current.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        setIsConnecting(false);
        onClose?.();

        if (reconnect && retryCountRef.current < maxRetries) {
          retryCountRef.current += 1;
          const delay = Math.min(1000 * Math.pow(2, retryCountRef.current - 1), 30000);
          setTimeout(() => connect(), delay);
        }
      };
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to connect');
      onError?.(err);
      setIsConnecting(false);

      if (reconnect && retryCountRef.current < maxRetries) {
        retryCountRef.current += 1;
        const delay = Math.min(1000 * Math.pow(2, retryCountRef.current - 1), 30000);
        setTimeout(() => connect(), delay);
      }
    }
  }, [url, onMessage, onError, onOpen, onClose, reconnect, maxRetries, isConnecting]);

  const send = useCallback((message: WebSocketMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected');
    }
  }, []);

  const disconnect = useCallback(() => {
    retryCountRef.current = maxRetries;
    wsRef.current?.close();
  }, [maxRetries]);

  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return { isConnected, isConnecting, send, disconnect };
}
