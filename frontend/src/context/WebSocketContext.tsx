import React, { createContext, useContext, useEffect, useState, useRef } from 'react';
import { Alert } from '../types';

export interface LiveSensorReading {
  id?: number;
  value: number;
  unit: string;
  timestamp: string;
  device_id: string;
  sensor_id: string;
  sensor_type: string;
  location?: string;
  connection_status?: string;
  is_stale?: boolean;
  last_updated_human?: string;
  receivedAt: number;
}

interface WebSocketContextType {
  isConnected: boolean;
  latestReadings: Record<string, LiveSensorReading>;
  liveAlerts: Alert[];
  clearAlert: (id: string) => void;
  lastReading: LiveSensorReading | null;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const WebSocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [latestReadings, setLatestReadings] = useState<Record<string, LiveSensorReading>>({});
  const [lastReading, setLastReading] = useState<LiveSensorReading | null>(null);
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
              const readingObj: LiveSensorReading = {
                id: r.id,
                value: r.value,
                unit: r.unit,
                timestamp: r.timestamp,
                device_id: r.device_id,
                sensor_id: r.sensor_id || `${r.device_id}-${r.sensor_type.toUpperCase()}`,
                sensor_type: r.sensor_type,
                location: r.location,
                connection_status: r.connection_status || 'online',
                is_stale: false,
                last_updated_human: 'Just now',
                receivedAt: Date.now()
              };
              setLastReading(readingObj);
              setLatestReadings((prev) => ({
                ...prev,
                [key]: readingObj,
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
    <WebSocketContext.Provider value={{ isConnected, latestReadings, liveAlerts, clearAlert, lastReading }}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = () => {
  const ctx = useContext(WebSocketContext);
  if (!ctx) throw new Error('useWebSocket must be used within WebSocketProvider');
  return ctx;
};
