import { useEffect, useRef, useState } from "react";
import { io, Socket } from "socket.io-client";
import type {
  ClientToServerEvents,
  ServerToClientEvents,
} from "../types/socket";

export type ConnStatus = "connecting" | "connected" | "disconnected";

type UseSocketOptions = {
  url?: string;
  path?: string;
  // If you want auth tokens later, pass them in here
  auth?: Record<string, unknown>;
};

export function useSocket({
  url = "http://localhost:5000",
  path,
  auth,
}: UseSocketOptions = {}) {
  const [status, setStatus] = useState<ConnStatus>("connecting");
  const socketRef = useRef<Socket<
    ServerToClientEvents,
    ClientToServerEvents
  > | null>(null);

  useEffect(() => {
    const socket: Socket<ServerToClientEvents, ClientToServerEvents> = io(url, {
      path,
      auth,
      // Reconnect every ~5s forever
      reconnection: true,
      reconnectionAttempts: Infinity,
      reconnectionDelay: 5000,
      reconnectionDelayMax: 5000,
      autoConnect: true,
      transports: ["websocket"], // skip polling for lower latency
    });

    socketRef.current = socket;

    const onConnect = () => setStatus("connected");
    const onDisconnect = () => setStatus("disconnected");
    const onConnectError = () => setStatus("disconnected");
    const onReconnectAttempt = () => setStatus("connecting");
    const onReconnect = () => setStatus("connected");

    socket.on("connect", onConnect);
    socket.on("disconnect", onDisconnect);
    socket.on("connect_error", onConnectError);
    socket.io.on("reconnect_attempt", onReconnectAttempt);
    socket.io.on("reconnect", onReconnect);

    return () => {
      socket.off("connect", onConnect);
      socket.off("disconnect", onDisconnect);
      socket.off("connect_error", onConnectError);
      socket.io.off("reconnect_attempt", onReconnectAttempt);
      socket.io.off("reconnect", onReconnect);
      socket.disconnect();
    };
  }, [url, path, auth]);

  return { socket: socketRef, status };
}
