import { useState, useEffect } from 'react'
import Card from '@/components/ui/Card'
import { PulseIndicator, AnimatedCard, FadeIn, SlideIn } from '@/components/ui/AnimatedComponents'
import { AlertTriangle, CheckCircle, XCircle, Clock, TrendingUp, Activity, Zap } from 'lucide-react'
import { wsClient, WebSocketData } from '@/lib/websocket'

interface Alert {
  id: string
  type: 'info' | 'warning' | 'error' | 'success'
  title: string
  message: string
  timestamp: Date
  acknowledged: boolean
  source: string
  severity: 'low' | 'medium' | 'high' | 'critical'
}

export default function AdvancedAlertSystem() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [data, setData] = useState<WebSocketData | null>(null)

  useEffect(() => {
    const unsubscribe = wsClient.subscribe((newData: WebSocketData) => {
      setData(newData)
      generateAlerts(newData)
    })

    return unsubscribe
  }, [])

  const generateAlerts = (wsData: WebSocketData) => {
    const newAlerts: Alert[] = []
    const { sensor_data } = wsData

    // Vibration alerts
    if (sensor_data.z_rms > 4.0) {
      newAlerts.push({
        id: `vib-z-${Date.now()}`,
        type: 'error',
        title: 'High Z-Axis Vibration',
        message: `Z-axis RMS velocity exceeded threshold: ${sensor_data.z_rms.toFixed(3)} mm/s`,
        timestamp: new Date(),
        acknowledged: false,
        source: 'Vibration Monitor',
        severity: sensor_data.z_rms > 5.0 ? 'critical' : 'high'
      })
    }

    if (sensor_data.x_rms > 3.5) {
      newAlerts.push({
        id: `vib-x-${Date.now()}`,
        type: 'warning',
        title: 'Elevated X-Axis Vibration',
        message: `X-axis RMS velocity elevated: ${sensor_data.x_rms.toFixed(3)} mm/s`,
        timestamp: new Date(),
        acknowledged: false,
        source: 'Vibration Monitor',
        severity: 'medium'
      })
    }

    // Temperature alerts
    if (sensor_data.temperature > 45) {
      newAlerts.push({
        id: `temp-high-${Date.now()}`,
        type: 'error',
        title: 'High Temperature',
        message: `Temperature exceeded safe limit: ${sensor_data.temperature.toFixed(1)}°C`,
        timestamp: new Date(),
        acknowledged: false,
        source: 'Temperature Sensor',
        severity: sensor_data.temperature > 50 ? 'critical' : 'high'
      })
    }

    // Bearing health alerts
    if (sensor_data.bearing_health < 70) {
      newAlerts.push({
        id: `bearing-${Date.now()}`,
        type: 'warning',
        title: 'Bearing Health Degradation',
        message: `Bearing health index dropped to ${sensor_data.bearing_health.toFixed(1)}%`,
        timestamp: new Date(),
        acknowledged: false,
        source: 'Health Monitor',
        severity: sensor_data.bearing_health < 50 ? 'critical' : 'medium'
      })
    }

    // Frequency alerts
    if (sensor_data.frequency > 200) {
      newAlerts.push({
        id: `freq-${Date.now()}`,
        type: 'info',
        title: 'High Frequency Detected',
        message: `Peak frequency elevated: ${sensor_data.frequency.toFixed(1)} Hz`,
        timestamp: new Date(),
        acknowledged: false,
        source: 'Frequency Analyzer',
        severity: 'low'
      })
    }

    // Data quality alerts
    if (sensor_data.data_quality < 90) {
      newAlerts.push({
        id: `quality-${Date.now()}`,
        type: 'warning',
        title: 'Data Quality Issue',
        message: `Data quality degraded to ${sensor_data.data_quality.toFixed(1)}%`,
        timestamp: new Date(),
        acknowledged: false,
        source: 'Data Monitor',
        severity: 'medium'
      })
    }

    if (newAlerts.length > 0) {
      setAlerts(prev => [...newAlerts, ...prev].slice(0, 50)) // Keep last 50 alerts
    }
  }

  const acknowledgeAlert = (alertId: string) => {
    setAlerts(prev => prev.map(alert => 
      alert.id === alertId ? { ...alert, acknowledged: true } : alert
    ))
  }

  const clearAlerts = () => {
    setAlerts([])
  }

  const getAlertIcon = (type: string) => {
    switch (type) {
      case 'error':
        return <XCircle className="w-5 h-5 text-error" />
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-warning" />
      case 'success':
        return <CheckCircle className="w-5 h-5 text-success" />
      default:
        return <Activity className="w-5 h-5 text-primary" />
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'border-l-critical bg-critical/5'
      case 'high':
        return 'border-l-error bg-error/5'
      case 'medium':
        return 'border-l-warning bg-warning/5'
      default:
        return 'border-l-primary bg-primary/5'
    }
  }

  const activeAlerts = alerts.filter(alert => !alert.acknowledged)
  const criticalAlerts = activeAlerts.filter(alert => alert.severity === 'critical')

  return (
    <div className="space-y-6">
      {/* Alert Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <AnimatedCard delay={0.1}>
          <Card className="p-4 text-center">
            <div className="flex items-center justify-center gap-2 mb-2">
              <PulseIndicator active={criticalAlerts.length > 0} color="error" />
              <span className="text-2xl font-bold text-error">{criticalAlerts.length}</span>
            </div>
            <p className="text-sm text-text-muted">Critical Alerts</p>
          </Card>
        </AnimatedCard>

        <AnimatedCard delay={0.2}>
          <Card className="p-4 text-center">
            <div className="flex items-center justify-center gap-2 mb-2">
              <PulseIndicator active={activeAlerts.length > 0} color="warning" />
              <span className="text-2xl font-bold text-warning">{activeAlerts.length}</span>
            </div>
            <p className="text-sm text-text-muted">Active Alerts</p>
          </Card>
        </AnimatedCard>

        <AnimatedCard delay={0.3}>
          <Card className="p-4 text-center">
            <div className="flex items-center justify-center gap-2 mb-2">
              <Clock className="w-5 h-5 text-primary" />
              <span className="text-2xl font-bold text-primary">{alerts.length}</span>
            </div>
            <p className="text-sm text-text-muted">Total Alerts</p>
          </Card>
        </AnimatedCard>

        <AnimatedCard delay={0.4}>
          <Card className="p-4 text-center">
            <div className="flex items-center justify-center gap-2 mb-2">
              <Zap className="w-5 h-5 text-success" />
              <span className="text-2xl font-bold text-success">
                {data?.sensor_data?.bearing_health?.toFixed(0) || 0}%
              </span>
            </div>
            <p className="text-sm text-text-muted">System Health</p>
          </Card>
        </AnimatedCard>
      </div>

      {/* Alert Controls */}
      <FadeIn delay={0.5}>
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-text">Alert Management</h3>
            <div className="flex gap-2">
              <button
                onClick={() => setAlerts(prev => prev.map(alert => ({ ...alert, acknowledged: true })))}
                className="px-4 py-2 bg-primary/10 border border-primary/30 rounded-lg text-primary hover:bg-primary/20 transition-colors"
              >
                Acknowledge All
              </button>
              <button
                onClick={clearAlerts}
                className="px-4 py-2 bg-error/10 border border-error/30 rounded-lg text-error hover:bg-error/20 transition-colors"
              >
                Clear All
              </button>
            </div>
          </div>
        </Card>
      </FadeIn>

      {/* Alerts List */}
      <div className="space-y-2">
        {alerts.length === 0 ? (
          <FadeIn delay={0.6}>
            <Card className="p-8 text-center">
              <CheckCircle className="w-12 h-12 text-success mx-auto mb-4" />
              <p className="text-text-muted">No alerts detected</p>
              <p className="text-sm text-text-muted mt-2">System operating normally</p>
            </Card>
          </FadeIn>
        ) : (
          alerts.map((alert, index) => (
            <SlideIn key={alert.id} direction="right" delay={0.1 + (index * 0.05)}>
              <Card className={`p-4 border-l-4 ${getSeverityColor(alert.severity)} ${alert.acknowledged ? 'opacity-60' : ''}`}>
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    {getAlertIcon(alert.type)}
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="font-semibold text-text">{alert.title}</h4>
                        {!alert.acknowledged && (
                          <PulseIndicator active={true} color="primary" size="sm" />
                        )}
                      </div>
                      <p className="text-sm text-text-muted mb-2">{alert.message}</p>
                      <div className="flex items-center gap-4 text-xs text-text-muted">
                        <span>{alert.source}</span>
                        <span>{alert.timestamp.toLocaleTimeString()}</span>
                        <span className="capitalize">{alert.severity}</span>
                      </div>
                    </div>
                  </div>
                  {!alert.acknowledged && (
                    <button
                      onClick={() => acknowledgeAlert(alert.id)}
                      className="px-3 py-1 bg-primary/10 border border-primary/30 rounded text-primary hover:bg-primary/20 transition-colors text-sm"
                    >
                      Acknowledge
                    </button>
                  )}
                </div>
              </Card>
            </SlideIn>
          ))
        )}
      </div>
    </div>
  )
}
