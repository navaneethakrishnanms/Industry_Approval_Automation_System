'use client';
import { useEffect, useRef, useState, useCallback } from 'react';
import { WS_URL } from './api';

export interface WSEvent {
  event_type: string;
  workflow_id?: string;
  source_agent?: string;
  payload?: Record<string, any>;
  timestamp?: string;
  message?: string;
  agents?: Record<string, any>;
}

export function useWebSocket(path: string = '/ws/dashboard') {
  const [events, setEvents] = useState<WSEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<WSEvent | null>(null);
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    try {
      ws.current = new WebSocket(`${WS_URL}${path}`);

      ws.current.onopen = () => {
        setConnected(true);
        if (reconnectTimer.current) {
          clearTimeout(reconnectTimer.current);
          reconnectTimer.current = null;
        }
      };

      ws.current.onmessage = (e) => {
        try {
          const data: WSEvent = JSON.parse(e.data);
          if (data.event_type === 'heartbeat' || data.event_type === 'pong') return;
          setLastEvent(data);
          setEvents(prev => [data, ...prev].slice(0, 200)); // rolling 200 events
        } catch { /* ignore parse errors */ }
      };

      ws.current.onclose = () => {
        setConnected(false);
        // Auto-reconnect after 3 seconds
        reconnectTimer.current = setTimeout(connect, 3000);
      };

      ws.current.onerror = () => {
        ws.current?.close();
      };
    } catch {
      reconnectTimer.current = setTimeout(connect, 5000);
    }
  }, [path]);

  useEffect(() => {
    connect();
    // Ping every 25s to keep alive
    const pingInterval = setInterval(() => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send('ping');
      }
    }, 25000);
    return () => {
      clearInterval(pingInterval);
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      ws.current?.close();
    };
  }, [connect]);

  return { events, connected, lastEvent };
}
