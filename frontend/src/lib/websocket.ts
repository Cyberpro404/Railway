/**
 * WebSocket client for real-time 1Hz data updates
 */

/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_WS_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
export interface SensorData {
  z_rms: number
  x_rms: number
  z_peak: number
  x_peak: number
  z_accel: number
  x_accel: number
  temperature: number
  frequency: number
  kurtosis: number
  crest_factor: number
  rms_overall: number
  energy: number
  bearing_health: number
  iso_class: string
  alarm_status: string
  humidity: number
  vibration_trend: number
  temp_trend: number
  uptime: number
  sensor_status: string
  data_quality: number
  maintenance_score?: number
  spectrum?: Array<{ frequency: number, amplitude: number }>
  timestamp: string
  raw_registers?: number[]
  health_status?: any
  peak_accel: number
  peak_velocity: number
}

export interface MLPrediction {
  class: number
  class_name: string
  confidence: number
  probabilities: {
    normal: number
    anomaly: number
  }
  feature_importance: Record<string, number>
  timestamp: string
}

export interface ISOSeverity {
  level: string
  class: string
  color: string
  description: string
  rms_velocity: number
}

export interface ConnectionStatus {
  connected: boolean
  port: string | null
  baud: number
  slave_id: number
  uptime_seconds: number
  last_poll: string | null
  packet_loss: number
  auto_reconnect: boolean
}

export interface WebSocketData {
  timestamp: string
  sensor_data: SensorData
  features: Record<string, number>
  ml_prediction: MLPrediction | null
  iso_severity: ISOSeverity | null
  connection_status: ConnectionStatus
  health_status?: any
  source?: string
  peak_hold?: number
  device_address?: string
  tcp_port?: number
  response_time_ms?: number
  device_id?: string
}

type WebSocketCallback = (data: WebSocketData) => void

/**
 * Derive WebSocket URL from current page location or environment.
 * Uses the Vite dev-server proxy (/ws → ws://localhost:8000) so the
 * browser never needs to reach port 8000 directly.  In production the
 * same path is served by a reverse-proxy (nginx / caddy / etc.).
 */
function deriveWebSocketUrl(): string {
  // Explicit override via .env (e.g. VITE_WS_URL=ws://192.168.1.10:8000/ws)
  const envUrl = import.meta.env.VITE_WS_URL
  if (envUrl) {
    console.log('[WS] Using VITE_WS_URL:', envUrl)
    return envUrl
  }

  // Use same host:port as the page → Vite proxies /ws to backend
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const url = `${protocol}//${window.location.host}/ws`
  console.log('[WS] Connecting via Vite proxy:', url)
  return url
}

class WebSocketClient {
  private ws: WebSocket | null = null
  private url: string
  private callbacks: Set<WebSocketCallback> = new Set()
  private reconnectAttempts = 0
  private maxReconnectAttempts = 10
  private reconnectDelay = 1000
  private isConnecting = false

  constructor() {
    this.url = deriveWebSocketUrl()
  }

  connect(): void {
    if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
      return
    }

    this.isConnecting = true

    try {
      this.ws = new WebSocket(this.url)

      this.ws.onopen = () => {
        console.log('WebSocket connected')
        this.isConnecting = false
        this.reconnectAttempts = 0
      }

      this.ws.onmessage = (event) => {
        try {
          const data: WebSocketData = JSON.parse(event.data)
          this.callbacks.forEach(callback => callback(data))
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.isConnecting = false
        // Don't immediately reconnect on error, wait a bit
        setTimeout(() => {
          this.attemptReconnect()
        }, 2000)
      }

      this.ws.onclose = (event) => {
        console.log('WebSocket disconnected, code:', event.code, 'reason:', event.reason)
        this.isConnecting = false
        this.attemptReconnect()
      }
    } catch (error) {
      console.error('Error creating WebSocket:', error)
      this.isConnecting = false
      this.attemptReconnect()
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached')
      return
    }

    this.reconnectAttempts++
    const delay = Math.min(this.reconnectDelay * this.reconnectAttempts, 10000) // Max 10 second delay

    setTimeout(() => {
      console.log(`Reconnecting... (attempt ${this.reconnectAttempts}) after ${delay}ms delay`)
      this.connect()
    }, delay)
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.callbacks.clear()
  }

  subscribe(callback: WebSocketCallback): () => void {
    this.callbacks.add(callback)
    return () => {
      this.callbacks.delete(callback)
    }
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }
}

// Singleton instance
export const wsClient = new WebSocketClient()

