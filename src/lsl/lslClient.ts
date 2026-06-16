import { UIConfig } from '../parser/types';

type LslConfig = NonNullable<UIConfig['lsl']>;

export type LslMarkerPayload = {
  event: string;
  timestamp: number;
  studyId?: string;
  participantId?: string;
  component?: string;
  identifier?: string;
  trialOrder?: string;
  data?: Record<string, unknown>;
};

const DEFAULT_WS_URL = 'ws://127.0.0.1:8765';
const DEFAULT_RECONNECT_INTERVAL_MS = 2000;

class LslMarkerClient {
  private socket?: WebSocket;

  private enabled = false;

  private url = DEFAULT_WS_URL;

  private reconnectIntervalMs = DEFAULT_RECONNECT_INTERVAL_MS;

  private reconnectTimer?: number;

  private queue: LslMarkerPayload[] = [];

  configure(config?: LslConfig) {
    const envEnabled = import.meta.env.VITE_LSL_ENABLED === 'true';
    const enabled = config?.enabled ?? envEnabled;
    const url = config?.url || import.meta.env.VITE_LSL_WS_URL || DEFAULT_WS_URL;
    const reconnectIntervalMs = config?.reconnectIntervalMs ?? DEFAULT_RECONNECT_INTERVAL_MS;

    if (!enabled) {
      this.close();
      this.enabled = false;
      return;
    }

    const shouldReconnect = !this.enabled || this.url !== url;
    this.enabled = true;
    this.url = url;
    this.reconnectIntervalMs = reconnectIntervalMs;

    if (shouldReconnect) {
      this.close();
      this.connect();
    }
  }

  send(marker: Omit<LslMarkerPayload, 'timestamp'> & { timestamp?: number }) {
    if (!this.enabled) {
      return;
    }

    const payload = {
      ...marker,
      timestamp: marker.timestamp ?? Date.now(),
    };

    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(payload));
      return;
    }

    this.queue.push(payload);
    if (this.queue.length > 250) {
      this.queue.shift();
    }
    this.connect();
  }

  private connect() {
    if (!this.enabled || this.socket?.readyState === WebSocket.OPEN || this.socket?.readyState === WebSocket.CONNECTING) {
      return;
    }

    try {
      this.socket = new WebSocket(this.url);
    } catch {
      this.scheduleReconnect();
      return;
    }

    this.socket.addEventListener('open', () => {
      const queued = this.queue.splice(0, this.queue.length);
      queued.forEach((marker) => this.socket?.send(JSON.stringify(marker)));
    });
    this.socket.addEventListener('close', () => this.scheduleReconnect());
    this.socket.addEventListener('error', () => this.socket?.close());
  }

  private scheduleReconnect() {
    if (!this.enabled || this.reconnectTimer !== undefined) {
      return;
    }

    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = undefined;
      this.connect();
    }, this.reconnectIntervalMs);
  }

  private close() {
    if (this.reconnectTimer !== undefined) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = undefined;
    }
    this.queue = [];
    this.socket?.close();
    this.socket = undefined;
  }
}

export const lslMarkerClient = new LslMarkerClient();
