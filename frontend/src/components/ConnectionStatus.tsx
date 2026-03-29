import { useState, useEffect } from 'react'
import { Wifi, WifiOff, AlertTriangle } from 'lucide-react'
import { wsHealthMonitor } from '@/lib/websocket-health'

export default function ConnectionStatus() {
  const [health, setHealth] = useState(wsHealthMonitor.getHealth())

  useEffect(() => {
    const unsubscribe = wsHealthMonitor.onHealthChange((isHealthy) => {
      setHealth(wsHealthMonitor.getHealth())
    })

    // Update health every second
    const interval = setInterval(() => {
      setHealth(wsHealthMonitor.getHealth())
    }, 1000)

    return () => {
      unsubscribe()
      clearInterval(interval)
    }
  }, [])

  const getStatusColor = () => {
    if (health.isHealthy) return 'text-success'
    if (health.isConnected) return 'text-warning'
    return 'text-error'
  }

  const getStatusIcon = () => {
    if (health.isHealthy) return <Wifi className="w-4 h-4" />
    if (health.isConnected) return <AlertTriangle className="w-4 h-4" />
    return <WifiOff className="w-4 h-4" />
  }

  const getStatusText = () => {
    if (health.isHealthy) return 'Connected'
    if (health.isConnected) return 'Receiving Data'
    return 'Disconnected'
  }

  return (
    <div className={`flex items-center gap-2 px-3 py-1 rounded-full border ${getStatusColor()} border-current/20`}>
      {getStatusIcon()}
      <span className="text-sm font-medium">{getStatusText()}</span>
    </div>
  )
}
