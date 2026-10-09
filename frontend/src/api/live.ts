export interface QueueEventConnection {
  close: () => void;
}

export type QueueEventKind = "connected" | "changed";

export function connectQueueEvents(onEvent: (kind: QueueEventKind) => void): QueueEventConnection {
  let socket: WebSocket | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let closed = false;
  let retryDelay = 500;

  const connect = () => {
    if (closed) return;
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    socket = new WebSocket(`${protocol}//${window.location.host}/api/queue/events`);
    socket.addEventListener("open", () => {
      retryDelay = 500;
      onEvent("connected");
    });
    socket.addEventListener("message", (event) => {
      const message = JSON.parse(String(event.data)) as { type?: string };
      if (message.type === "queue.changed") onEvent("changed");
    });
    socket.addEventListener("close", () => {
      socket = null;
      if (closed) return;
      reconnectTimer = setTimeout(connect, retryDelay);
      retryDelay = Math.min(retryDelay * 2, 10_000);
    });
  };

  connect();

  return {
    close: () => {
      closed = true;
      if (reconnectTimer !== null) clearTimeout(reconnectTimer);
      socket?.close();
      socket = null;
    },
  };
}
