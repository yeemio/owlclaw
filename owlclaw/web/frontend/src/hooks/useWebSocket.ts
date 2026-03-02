import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";

export function useConsoleWebSocket(): void {
  const client = useQueryClient();

  useEffect(() => {
    let ws: WebSocket | null = null;
    let retry: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      const protocol = location.protocol === "https:" ? "wss" : "ws";
      ws = new WebSocket(`${protocol}://${location.host}/api/v1/ws`);

      ws.onmessage = (event) => {
        const payload = JSON.parse(event.data) as { type?: string };
        if (payload.type === "overview") {
          client.invalidateQueries({ queryKey: ["overview"] });
        }
        if (payload.type === "ledger") {
          client.invalidateQueries({ queryKey: ["ledger"] });
        }
        if (payload.type === "triggers") {
          client.invalidateQueries({ queryKey: ["triggers"] });
        }
      };

      ws.onclose = () => {
        retry = setTimeout(connect, 1500);
      };
    };

    connect();
    return () => {
      if (retry) {
        clearTimeout(retry);
      }
      ws?.close();
    };
  }, [client]);
}
