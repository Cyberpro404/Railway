/**
 * WebSocket Connection Health Monitor
 */
import { wsClient } from '@/lib/websocket'

class WebSocketHealthMonitor {
  private isHealthy = false
  private lastPing = Date.now()
  private pingInterval: number | null = null
  private healthCallbacks: Set<(isHealthy: boolean) => void> = new Set()

  constructor() {
    this.startMonitoring()
  }

  private startMonitoring() {
    // Subscribe to WebSocket to monitor connection
    wsClient.subscribe((data) => {
      this.lastPing = Date.now()
      if (!this.isHealthy) {
        this.isHealthy = true
        this.notifyHealthChange(true)
      }
    })

    // Periodic health check
    this.pingInterval = setInterval(() => {
      const now = Date.now()
      const timeSinceLastPing = now - this.lastPing
      
      // Consider unhealthy if no data for more than 5 seconds
      if (timeSinceLastPing > 5000 && this.isHealthy) {
        this.isHealthy = false
        this.notifyHealthChange(false)
      }
    }, 1000)
  }

  private notifyHealthChange(isHealthy: boolean) {
    this.healthCallbacks.forEach(callback => callback(isHealthy))
  }

  public onHealthChange(callback: (isHealthy: boolean) => void) {
    this.healthCallbacks.add(callback)
    return () => {
      this.healthCallbacks.delete(callback)
    }
  }

  public getHealth() {
    return {
      isHealthy: this.isHealthy,
      isConnected: wsClient.isConnected(),
      lastPing: this.lastPing,
      timeSinceLastPing: Date.now() - this.lastPing
    }
  }

  public destroy() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }
    this.healthCallbacks.clear()
  }
}

export const wsHealthMonitor = new WebSocketHealthMonitor()
