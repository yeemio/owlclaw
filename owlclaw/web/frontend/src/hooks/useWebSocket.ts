import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { type OverviewSnapshot } from "@/hooks/useApi";

type OverviewWsMessage = {
  type: "overview_update";
  data: OverviewSnapshot;
};

type AnyWsMessage = OverviewWsMessage | { type: string; data?: unknown };

function getWebSocketUrl(): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/api/v1/ws`;
}

export function useConsoleWebSocket() {
  const queryClient = useQueryClient();
  const reconnectTimerRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    let closedByUser = false;
    let ws: WebSocket | null = null;

    const clearReconnect = () => {
      if (reconnectTimerRef.current !== undefined) {
        window.clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = undefined;
      }
    };

    const connect = () => {
      ws = new WebSocket(getWebSocketUrl());

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as AnyWsMessage;
          if (payload.type === "overview_update" && payload.data) {
            queryClient.setQueryData(["overview"], payload.data);
          }
        } catch {
          // Ignore malformed websocket messages to keep UI alive.
        }
      };

      ws.onclose = () => {
        if (closedByUser) {
          return;
        }
        clearReconnect();
        reconnectTimerRef.current = window.setTimeout(connect, 2_000);
      };
    };

    connect();

    return () => {
      closedByUser = true;
      clearReconnect();
      if (ws) {
        ws.close();
      }
    };
  }, [queryClient]);
}
