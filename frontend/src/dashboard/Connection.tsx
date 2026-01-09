import { useEffect, useState } from 'react'
import { Wifi, WifiOff, RefreshCw, Settings, Scan } from 'lucide-react'
import { connectionAPI, ConnectionStatus } from '@/lib/api'
import { formatUptime, cn } from '@/lib/utils'
import { wsClient, WebSocketData } from '@/lib/websocket'

export default function ConnectionTab() {
  const [status, setStatus] = useState<ConnectionStatus | null>(null)
  const [ports, setPorts] = useState<string[]>([])
  const [isScanning, setIsScanning] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)

  useEffect(() => {
    loadStatus()
    
    const unsubscribe = wsClient.subscribe((data: WebSocketData) => {
      if (data.connection_status) {
        setStatus(data.connection_status)
      }
    })

    return unsubscribe
  }, [])

  const loadStatus = async () => {
    try {
      const data = await connectionAPI.getStatus()
      setStatus(data)
    } catch (error) {
      console.error('Error loading connection status:', error)
    }
  }

  const handleScan = async () => {
    setIsScanning(true)
    try {
      const availablePorts = await connectionAPI.scanPorts()
      setPorts(availablePorts)
    } catch (error) {
      console.error('Error scanning ports:', error)
    } finally {
      setIsScanning(false)
    }
  }

  const handleConnect = async (port: string) => {
    setIsConnecting(true)
    try {
      await connectionAPI.connect(port, 19200, 1)
      await loadStatus()
    } catch (error) {
      console.error('Error connecting:', error)
    } finally {
      setIsConnecting(false)
    }
  }

  const handleDisconnect = async () => {
    try {
      await connectionAPI.disconnect()
      await loadStatus()
    } catch (error) {
      console.error('Error disconnecting:', error)
    }
  }

  const handleReconnect = async () => {
    if (status?.port) {
      await handleConnect(status.port)
    }
  }

  if (!status) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto mb-4" />
          <div className="text-text-muted font-medium">Loading connection status...</div>
        </div>
      </div>
    )
  }

  const packetLossColor = status.packet_loss < 1 ? 'text-success' : 
                          status.packet_loss < 5 ? 'text-warning' : 'text-critical'

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div>
        <h1 className="text-h1 text-text mb-2 font-bold tracking-tight">CONNECTION STATUS</h1>
        <p className="text-text-muted font-medium">Live System Health Monitoring</p>
      </div>

      <div className="bg-card border border-border rounded-lg p-6 shadow-xl card-hover">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              {status.connected ? (
                <div className="relative">
                  <Wifi className="w-8 h-8 text-success animate-pulse-cyan" />
                  <div className="absolute inset-0 w-8 h-8 text-success animate-ping opacity-75">
                    <Wifi className="w-8 h-8" />
                  </div>
                </div>
              ) : (
                <WifiOff className="w-8 h-8 text-text-muted" />
              )}
              <div>
                <div className="text-sm text-text-muted font-semibold uppercase tracking-wide">Connection Status</div>
                <div className={`text-xl font-bold mt-1 ${status.connected ? 'text-success' : 'text-text-muted'}`}>
                  {status.connected ? 'CONNECTED' : 'DISCONNECTED'}
                </div>
              </div>
            </div>

            {status.connected && (
              <>
                <div>
                  <div className="text-sm text-text-muted">Port Configuration</div>
                  <div className="text-metric text-text font-mono mt-1">
                    {status.port} • {status.baud} baud • Slave ID: {status.slave_id}
                  </div>
                </div>

                <div>
                  <div className="text-sm text-text-muted">Uptime</div>
                  <div className="text-metric text-text font-mono mt-1">
                    {formatUptime(status.uptime_seconds)}
                  </div>
                </div>

                <div>
                  <div className="text-sm text-text-muted">Last Poll</div>
                  <div className="text-metric text-text font-mono mt-1">
                    {status.last_poll ? new Date(status.last_poll).toLocaleTimeString() : 'Never'}
                  </div>
                </div>
              </>
            )}
          </div>

          <div className="space-y-4">
            <div>
              <div className="text-sm text-text-muted">Packet Loss</div>
              <div className={`text-metric font-mono mt-1 ${packetLossColor}`}>
                {status.packet_loss.toFixed(2)}%
              </div>
            </div>

            <div>
              <div className="text-sm text-text-muted">Auto-Reconnect</div>
              <div className={`text-lg font-semibold mt-1 ${status.auto_reconnect ? 'text-success' : 'text-text-muted'}`}>
                {status.auto_reconnect ? '✓ ENABLED' : '✗ DISABLED'}
              </div>
            </div>

            {status.connected && (
              <div>
                <div className="text-sm text-text-muted">System Health</div>
                <div className="mt-2">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 bg-border rounded-full h-2">
                      <div 
                        className="bg-success h-2 rounded-full transition-all"
                        style={{ width: `${100 - status.packet_loss}%` }}
                      />
                    </div>
                    <span className="text-sm text-text-muted">
                      {(100 - status.packet_loss).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="mt-6 pt-6 border-t border-border flex flex-wrap gap-3">
          <button
            onClick={handleScan}
            disabled={isScanning}
            className={cn(
              "px-5 py-2.5 bg-card border border-border rounded-lg text-text",
              "hover:bg-primary/10 hover:border-primary/30 hover:shadow-lg",
              "transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed",
              "flex items-center gap-2 font-semibold",
              !isScanning && "hover:scale-105"
            )}
          >
            <Scan className={cn("w-4 h-4", isScanning && "animate-spin")} />
            {isScanning ? 'Scanning...' : 'SCAN PORTS'}
          </button>

          {status.connected ? (
            <button
              onClick={handleDisconnect}
              className="px-4 py-2 bg-critical/10 border border-critical/30 rounded-lg text-critical hover:bg-critical/20 transition-colors"
            >
              DISCONNECT
            </button>
          ) : (
            ports.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {ports.map((port) => (
                  <button
                    key={port}
                    onClick={() => handleConnect(port)}
                    disabled={isConnecting}
                    className="px-4 py-2 bg-primary/10 border border-primary/30 rounded-lg text-primary hover:bg-primary/20 transition-colors disabled:opacity-50"
                  >
                    Connect {port}
                  </button>
                ))}
              </div>
            )
          )}

          {status.connected && (
            <button
              onClick={handleReconnect}
              disabled={isConnecting}
              className="px-4 py-2 bg-card border border-border rounded-lg text-text hover:bg-primary/10 hover:border-primary/30 transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${isConnecting ? 'animate-spin' : ''}`} />
              RECONNECT
            </button>
          )}

          <button className="px-4 py-2 bg-card border border-border rounded-lg text-text hover:bg-primary/10 hover:border-primary/30 transition-colors flex items-center gap-2">
            <Settings className="w-4 h-4" />
            SETTINGS
          </button>
        </div>
      </div>
    </div>
  )
}

