/**
 * WebSocket client for real-time 1Hz data updates
 */
export interface SensorData {
  z_rms: number
  x_rms: number
  z_peak: number
  x_peak: number
  z_accel: number
  x_accel: number
  temperature: number
  timestamp: string
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
}

type WebSocketCallback = (data: WebSocketData) => void

class WebSocketClient {
  private ws: WebSocket | null = null
  private url: string
  private callbacks: Set<WebSocketCallback> = new Set()
  private reconnectAttempts = 0
  private maxReconnectAttempts = 10
  private reconnectDelay = 1000
  private isConnecting = false

  constructor(url: string = 'ws://localhost:8000/ws') {
    this.url = url
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
      }

      this.ws.onclose = () => {
        console.log('WebSocket disconnected')
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
    setTimeout(() => {
      console.log(`Reconnecting... (attempt ${this.reconnectAttempts})`)
      this.connect()
    }, this.reconnectDelay * this.reconnectAttempts)
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

