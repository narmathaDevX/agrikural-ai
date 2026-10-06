import React, { createContext, useContext, useEffect, useState, useRef } from 'react';
import { Alert } from '../types';

interface WebSocketContextType {
  isConnected: boolean;
  latestReadings: Record<string, { value: number; unit: string; timestamp: string; device_id: string; sensor_type: string }>;
  liveAlerts: Alert[];
  clearAlert: (id: string) => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const WebSocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [latestReadings, setLatestReadings] = useState<Record<string, any>>({});
  const [liveAlerts, setLiveAlerts] = useState<Alert[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let reconnectTimeout: any;

    function connect() {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/ws`;

      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          setIsConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'SENSOR_READING') {
              const r = data.data;
              const key = `${r.device_id}_${r.sensor_type}`;
              setLatestReadings((prev) => ({
                ...prev,
                [key]: {
                  value: r.value,
                  unit: r.unit,
                  timestamp: r.timestamp,
                  device_id: r.device_id,
                  sensor_type: r.sensor_type,
                },
              }));
            } else if (data.type === 'NEW_ALERT') {
              const alert = data.data;
              setLiveAlerts((prev) => [alert, ...prev.slice(0, 9)]);
            }
          } catch (_) {}
        };

        ws.onclose = () => {
          setIsConnected(false);
          reconnectTimeout = setTimeout(connect, 3000);
        };

        ws.onerror = () => {
          setIsConnected(false);
          ws.close();
        };
      } catch (_) {
        reconnectTimeout = setTimeout(connect, 4000);
      }
    }

    connect();

    // Ping interval to keep connection alive
    const pingInterval = setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send('ping');
      }
    }, 15000);

    return () => {
      clearInterval(pingInterval);
      clearTimeout(reconnectTimeout);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const clearAlert = (id: string) => {
    setLiveAlerts((prev) => prev.filter((a) => a.id !== id));
  };

  return (
    <WebSocketContext.Provider value={{ isConnected, latestReadings, liveAlerts, clearAlert }}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = () => {
  const ctx = useContext(WebSocketContext);
  if (!ctx) throw new Error('useWebSocket must be used within WebSocketProvider');
  return ctx;
};
