"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import type { ToastMessage } from "@/components/Toast";

// WebSocket hook
export function useWebSocket(url: string) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<any>(null);
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout>();

  const connect = useCallback(() => {
    try {
      ws.current = new WebSocket(url);

      ws.current.onopen = () => {
        setIsConnected(true);
        console.log("WebSocket connected");
      };

      ws.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        setLastMessage(data);
      };

      ws.current.onclose = () => {
        setIsConnected(false);
        console.log("WebSocket disconnected, reconnecting...");
        // Reconnect after 3 seconds
        reconnectTimeout.current = setTimeout(connect, 3000);
      };

      ws.current.onerror = (error) => {
        console.error("WebSocket error:", error);
      };
    } catch (error) {
      console.error("Failed to connect WebSocket:", error);
      reconnectTimeout.current = setTimeout(connect, 3000);
    }
  }, [url]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [connect]);

  const sendMessage = useCallback((message: any) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    }
  }, []);

  return { isConnected, lastMessage, sendMessage };
}

// Toast notifications hook
export function useToast() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = useCallback(
    (
      message: string,
      type: ToastMessage["type"] = "info",
      duration?: number
    ) => {
      const id = Math.random().toString(36).substring(7);
      const toast: ToastMessage = { id, message, type, duration };
      setToasts((prev) => [...prev, toast]);
    },
    []
  );

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const success = useCallback(
    (message: string) => addToast(message, "success"),
    [addToast]
  );
  const error = useCallback(
    (message: string) => addToast(message, "error"),
    [addToast]
  );
  const info = useCallback(
    (message: string) => addToast(message, "info"),
    [addToast]
  );
  const warning = useCallback(
    (message: string) => addToast(message, "warning"),
    [addToast]
  );

  return {
    toasts,
    addToast,
    removeToast,
    success,
    error,
    info,
    warning,
  };
}

// Search hook
export function useSearch<T>(
  items: T[],
  searchFields: (keyof T)[],
  searchTerm: string
): T[] {
  return useState(() => {
    if (!searchTerm) return items;

    const term = searchTerm.toLowerCase();
    return items.filter((item) => {
      return searchFields.some((field) => {
        const value = item[field];
        if (typeof value === "string") {
          return value.toLowerCase().includes(term);
        }
        return false;
      });
    });
  })[0];
}
