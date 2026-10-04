"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const WS_URL =
  (typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/^http/, "ws")
    : "ws://localhost:8000") + "/api/v1/ws";

export type WsMessage = {
  type: string;
  message?: string;
  title?: string;
  data?: Record<string, unknown>;
  tick?: number;
};

export function useWebSocket(token?: string | null) {
  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WsMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const pingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const url = token ? `${WS_URL}?token=${encodeURIComponent(token)}` : WS_URL;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      pingRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "ping" }));
        }
      }, 25000);
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as WsMessage;
        setLastMessage(msg);
      } catch {
        /* ignore */
      }
    };

    ws.onclose = () => {
      setConnected(false);
      if (pingRef.current) clearInterval(pingRef.current);
    };

    ws.onerror = () => setConnected(false);
  }, [token]);

  const disconnect = useCallback(() => {
    if (pingRef.current) clearInterval(pingRef.current);
    wsRef.current?.close();
    wsRef.current = null;
    setConnected(false);
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return { connected, lastMessage, connect, disconnect };
}
