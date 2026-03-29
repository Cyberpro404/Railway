import { useState, useEffect } from 'react'
import Card from '@/components/ui/Card'
import { PulseIndicator, AnimatedCard, FadeIn } from '@/components/ui/AnimatedComponents'
import { Activity, Thermometer, Zap, TrendingUp, AlertTriangle, CheckCircle, XCircle } from 'lucide-react'
import { wsClient, WebSocketData } from '@/lib/websocket'

interface RealTimeRegisterDisplayProps {
  data?: WebSocketData | null
}

export default function RealTimeRegisterDisplay({ data: propData }: RealTimeRegisterDisplayProps) {
  const [data, setData] = useState<WebSocketData | null>(propData || null)
  const [connectionStatus, setConnectionStatus] = useState(false)

  useEffect(() => {
    const unsubscribe = wsClient.subscribe((newData: WebSocketData) => {
      setData(newData)
      setConnectionStatus(newData.connection_status?.connected || false)
    })

    return unsubscribe
  }, [])

  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())

  useEffect(() => {
    if (data) {
      setLastUpdate(new Date(data.timestamp))
    }
  }, [data])

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'OK':
        return <CheckCircle className="w-4 h-4 text-success" />
      case 'Warning':
        return <AlertTriangle className="w-4 h-4 text-warning" />
      case 'Critical':
        return <XCircle className="w-4 h-4 text-error" />
      default:
        return <CheckCircle className="w-4 h-4 text-success" />
    }
  }

  const getSensorStatusIcon = (status: string) => {
    switch (status) {
      case 'Active':
        return <PulseIndicator active={true} color="success" size="sm" />
      case 'Error':
        return <PulseIndicator active={true} color="error" size="sm" />
      default:
        return <PulseIndicator active={false} color="primary" size="sm" />
    }
  }

  const getISOSeverityColor = (zone: string) => {
    switch (zone) {
      case 'Zone A':
        return 'text-success'
      case 'Zone B':
        return 'text-warning'
      case 'Zone C':
        return 'text-error'
      case 'Zone D':
        return 'text-critical'
      default:
        return 'text-primary'
    }
  }

  if (!data || !data.sensor_data) {
    return (
      <AnimatedCard delay={0.3}>
        <Card className="p-6">
          <div className="text-center py-8">
            <div className="w-12 h-12 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto mb-4" />
            <p className="text-text-muted">Waiting for real-time data...</p>
          </div>
        </Card>
      </AnimatedCard>
    )
  }

  const { sensor_data } = data

  return (
    <div className="space-y-6">
      {/* Connection Status */}
      <FadeIn delay={0.1}>
        <Card className="p-4 border-l-4 border-l-primary">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <PulseIndicator 
                active={connectionStatus} 
                color={connectionStatus ? 'success' : 'error'} 
              />
              <div>
                <p className="font-semibold text-text">Real-Time Monitor</p>
                <p className="text-xs text-text-muted">
                  Last Update: {lastUpdate.toLocaleTimeString()}
                </p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-xs text-text-muted">Data Quality</p>
              <p className="text-sm font-mono font-bold text-primary">
                {sensor_data.data_quality?.toFixed(1)}%
              </p>
            </div>
          </div>
        </Card>
      </FadeIn>

      {/* Primary Vibration Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <FadeIn delay={0.2}>
          <Card className="p-4 hover:shadow-lg transition-shadow">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-primary" />
                <span className="text-sm font-medium text-text-muted">Z RMS</span>
              </div>
              <PulseIndicator active={true} color="primary" size="sm" />
            </div>
            <p className="text-2xl font-mono font-bold text-primary">
              {sensor_data.z_rms?.toFixed(3)}
            </p>
            <p className="text-xs text-text-muted">mm/s</p>
          </Card>
        </FadeIn>

        <FadeIn delay={0.3}>
          <Card className="p-4 hover:shadow-lg transition-shadow">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-success" />
                <span className="text-sm font-medium text-text-muted">X RMS</span>
              </div>
              <PulseIndicator active={true} color="success" size="sm" />
            </div>
            <p className="text-2xl font-mono font-bold text-success">
              {sensor_data.x_rms?.toFixed(3)}
            </p>
            <p className="text-xs text-text-muted">mm/s</p>
          </Card>
        </FadeIn>

        <FadeIn delay={0.4}>
          <Card className="p-4 hover:shadow-lg transition-shadow">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Zap className="w-5 h-5 text-warning" />
                <span className="text-sm font-medium text-text-muted">Peak Freq</span>
              </div>
              <PulseIndicator active={true} color="warning" size="sm" />
            </div>
            <p className="text-2xl font-mono font-bold text-warning">
              {sensor_data.frequency?.toFixed(1)}
            </p>
            <p className="text-xs text-text-muted">Hz</p>
          </Card>
        </FadeIn>

        <FadeIn delay={0.5}>
          <Card className="p-4 hover:shadow-lg transition-shadow">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Thermometer className="w-5 h-5 text-error" />
                <span className="text-sm font-medium text-text-muted">Temperature</span>
              </div>
              <PulseIndicator active={true} color="error" size="sm" />
            </div>
            <p className="text-2xl font-mono font-bold text-error">
              {sensor_data.temperature?.toFixed(1)}
            </p>
            <p className="text-xs text-text-muted">°C</p>
          </Card>
        </FadeIn>
      </div>

      {/* Advanced Parameters */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <FadeIn delay={0.6}>
          <Card className="p-6">
            <h3 className="text-lg font-semibold text-text mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-primary" />
              Advanced Vibration Analysis
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-3">
                <div className="flex justify-between items-center p-3 bg-background/50 rounded-lg">
                  <span className="text-sm text-text-muted">Z Peak</span>
                  <span className="font-mono font-bold text-primary">
                    {sensor_data.z_peak?.toFixed(3)} mm/s
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-background/50 rounded-lg">
                  <span className="text-sm text-text-muted">X Peak</span>
                  <span className="font-mono font-bold text-success">
                    {sensor_data.x_peak?.toFixed(3)} mm/s
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-background/50 rounded-lg">
                  <span className="text-sm text-text-muted">Z Accel</span>
                  <span className="font-mono font-bold text-warning">
                    {sensor_data.z_accel?.toFixed(3)} mm/s²
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-background/50 rounded-lg">
                  <span className="text-sm text-text-muted">X Accel</span>
                  <span className="font-mono font-bold text-error">
                    {sensor_data.x_accel?.toFixed(3)} mm/s²
                  </span>
                </div>
              </div>
              <div className="space-y-3">
                <div className="flex justify-between items-center p-3 bg-background/50 rounded-lg">
                  <span className="text-sm text-text-muted">Kurtosis</span>
                  <span className="font-mono font-bold text-primary">
                    {sensor_data.kurtosis?.toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-background/50 rounded-lg">
                  <span className="text-sm text-text-muted">Crest Factor</span>
                  <span className="font-mono font-bold text-success">
                    {sensor_data.crest_factor?.toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-background/50 rounded-lg">
                  <span className="text-sm text-text-muted">RMS Overall</span>
                  <span className="font-mono font-bold text-warning">
                    {sensor_data.rms_overall?.toFixed(3)} mm/s
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-background/50 rounded-lg">
                  <span className="text-sm text-text-muted">Energy</span>
                  <span className="font-mono font-bold text-error">
                    {sensor_data.energy?.toFixed(2)} mJ
                  </span>
                </div>
              </div>
            </div>
          </Card>
        </FadeIn>

        <FadeIn delay={0.7}>
          <Card className="p-6">
            <h3 className="text-lg font-semibold text-text mb-4 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-warning" />
              System Health & Status
            </h3>
            <div className="space-y-4">
              <div className="flex justify-between items-center p-3 bg-background/50 rounded-lg">
                <span className="text-sm text-text-muted">Bearing Health</span>
                <div className="flex items-center gap-2">
                  <div className="w-16 bg-background rounded-full h-2">
                    <div 
                      className="bg-gradient-to-r from-success to-success/60 h-2 rounded-full"
                      style={{ width: `${sensor_data.bearing_health || 0}%` }}
                    />
                  </div>
                  <span className="font-mono font-bold text-success">
                    {sensor_data.bearing_health?.toFixed(1)}%
                  </span>
                </div>
              </div>
              <div className="flex justify-between items-center p-3 bg-background/50 rounded-lg">
                <span className="text-sm text-text-muted">ISO Severity</span>
                <span className={`font-bold ${getISOSeverityColor(sensor_data.iso_class || 'Zone A')}`}>
                  {sensor_data.iso_class || 'Zone A'}
                </span>
              </div>
              <div className="flex justify-between items-center p-3 bg-background/50 rounded-lg">
                <span className="text-sm text-text-muted">Alarm Status</span>
                <div className="flex items-center gap-2">
                  {getStatusIcon(sensor_data.alarm_status || 'OK')}
                  <span className="font-medium">
                    {sensor_data.alarm_status || 'OK'}
                  </span>
                </div>
              </div>
              <div className="flex justify-between items-center p-3 bg-background/50 rounded-lg">
                <span className="text-sm text-text-muted">Sensor Status</span>
                <div className="flex items-center gap-2">
                  {getSensorStatusIcon(sensor_data.sensor_status || 'Active')}
                  <span className="font-medium">
                    {sensor_data.sensor_status || 'Active'}
                  </span>
                </div>
              </div>
              <div className="flex justify-between items-center p-3 bg-background/50 rounded-lg">
                <span className="text-sm text-text-muted">Humidity</span>
                <span className="font-mono font-bold text-primary">
                  {sensor_data.humidity?.toFixed(1)}%RH
                </span>
              </div>
              <div className="flex justify-between items-center p-3 bg-background/50 rounded-lg">
                <span className="text-sm text-text-muted">Uptime</span>
                <span className="font-mono font-bold text-success">
                  {sensor_data.uptime || 0} hours
                </span>
              </div>
            </div>
          </Card>
        </FadeIn>
      </div>

      {/* Trend Analysis */}
      <FadeIn delay={0.8}>
        <Card className="p-6">
          <h3 className="text-lg font-semibold text-text mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-primary" />
            Real-Time Trends
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center p-4 bg-background/50 rounded-lg">
              <p className="text-sm text-text-muted mb-2">Vibration Trend</p>
              <p className="text-xl font-mono font-bold text-primary">
                {sensor_data.vibration_trend?.toFixed(4) || 0}
              </p>
              <p className="text-xs text-text-muted">mm/s/s</p>
            </div>
            <div className="text-center p-4 bg-background/50 rounded-lg">
              <p className="text-sm text-text-muted mb-2">Temperature Trend</p>
              <p className="text-xl font-mono font-bold text-warning">
                {sensor_data.temp_trend?.toFixed(2) || 0}
              </p>
              <p className="text-xs text-text-muted">°C/min</p>
            </div>
            <div className="text-center p-4 bg-background/50 rounded-lg">
              <p className="text-sm text-text-muted mb-2">Data Quality</p>
              <p className="text-xl font-mono font-bold text-success">
                {sensor_data.data_quality?.toFixed(1) || 0}%
              </p>
              <p className="text-xs text-text-muted">Signal Integrity</p>
            </div>
          </div>
        </Card>
      </FadeIn>
    </div>
  )
}
