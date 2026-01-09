import { useEffect, useState } from 'react'
import { TrendingUp, Thermometer, Activity, AlertCircle, Download, RefreshCw, Clock, Zap } from 'lucide-react'
import { wsClient, WebSocketData } from '@/lib/websocket'
import MetricCard from '@/components/ui/MetricCard'
import LiveGauge from '@/components/ui/LiveGauge'
import StatCard from '@/components/ui/StatCard'
import AdvancedChart from '@/components/ui/AdvancedChart'
import StatusBadge from '@/components/ui/StatusBadge'
import { getSeverityColor } from '@/lib/utils'

export default function ExecutiveTab() {
  const [data, setData] = useState<WebSocketData | null>(null)
  const [sparklines, setSparklines] = useState<{
    z_rms: number[]
    x_rms: number[]
    temp: number[]
  }>({
    z_rms: [],
    x_rms: [],
    temp: []
  })

  useEffect(() => {
    const unsubscribe = wsClient.subscribe((newData: WebSocketData) => {
      setData(newData)
      
      // Update sparklines (keep last 20 points)
      if (newData.sensor_data) {
        setSparklines(prev => ({
          z_rms: [...prev.z_rms.slice(-19), newData.sensor_data.z_rms],
          x_rms: [...prev.x_rms.slice(-19), newData.sensor_data.x_rms],
          temp: [...prev.temp.slice(-19), newData.sensor_data.temperature]
        }))
      }
    })

    return unsubscribe
  }, [])

  if (!data) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto mb-4" />
          <div className="text-text-muted font-medium">Waiting for data...</div>
        </div>
      </div>
    )
  }

  const sensor = data.sensor_data
  const iso = data.iso_severity
  const ml = data.ml_prediction

  // Calculate bearing health (simplified)
  const bearingHealth = Math.max(0, Math.min(100, 100 - (sensor.temperature - 25) * 2))

  return (
    <div className="space-y-8 fade-in-up">
      {/* World-Class Header with Advanced Styling */}
      <div className="relative">
        {/* Background glow effect */}
        <div className="absolute -inset-4 bg-gradient-to-r from-primary/10 via-transparent to-success/10 blur-2xl opacity-50" />
        
        <div className="relative flex items-center justify-between mb-8 p-6 rounded-2xl glassmorphism border border-border/50">
          <div className="flex-1">
            <div className="flex items-center gap-4 mb-3">
              <div className="relative">
                <div className="w-2 h-12 bg-gradient-to-b from-primary via-primary/80 to-success rounded-full" />
                <div className="absolute inset-0 w-2 h-12 bg-gradient-to-b from-primary to-success rounded-full animate-pulse-cyan opacity-50" />
              </div>
              <div>
                <h1 className="text-5xl font-black text-gradient-primary tracking-tight mb-1">
                  EXECUTIVE DASHBOARD
                </h1>
                <div className="flex items-center gap-3 text-text-muted">
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-primary" />
                    <span className="font-semibold">Real-time KPI Overview</span>
                  </div>
                  <span className="text-primary">•</span>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-success pulse-ring" />
                    <span className="font-semibold">1Hz Updates</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button className="group relative px-5 py-2.5 rounded-xl border border-primary/30 bg-primary/10 hover:bg-primary/20 hover:border-primary/50 transition-all duration-300 hover:scale-105 btn-glow">
              <RefreshCw className="w-5 h-5 text-primary group-hover:rotate-180 transition-transform duration-500" />
            </button>
            <button className="group relative px-5 py-2.5 rounded-xl border border-border hover:bg-primary/10 hover:border-primary/30 transition-all duration-300 hover:scale-105 btn-glow">
              <Download className="w-5 h-5 text-text group-hover:text-primary transition-colors" />
            </button>
          </div>
        </div>
      </div>

      {/* Status Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          title="System Status"
          value={data.connection_status?.connected ? 'Online' : 'Offline'}
          icon={<Zap className="w-6 h-6" />}
          color={data.connection_status?.connected ? 'success' : 'critical'}
        />
        <StatCard
          title="Health Index"
          value={bearingHealth.toFixed(1)}
          unit="%"
          icon={<Activity className="w-6 h-6" />}
          color={bearingHealth > 80 ? 'success' : bearingHealth > 60 ? 'warning' : 'critical'}
          change={bearingHealth > 75 ? 2.5 : -1.2}
        />
        <StatCard
          title="Active Alerts"
          value={ml && ml.class === 1 ? '1' : '0'}
          icon={<AlertCircle className="w-6 h-6" />}
          color={ml && ml.class === 1 ? 'critical' : 'success'}
        />
        <StatCard
          title="Uptime"
          value="99.2%"
          change={0.3}
          icon={<Clock className="w-6 h-6" />}
          color="success"
        />
      </div>

      {/* Premium 16 KPI Tiles in 4x4 Grid with Staggered Animation */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
        <MetricCard
          title="Z RMS Velocity"
          value={sensor.z_rms.toFixed(3)}
          unit="mm/s"
          status={iso?.color === 'red' ? 'critical' : iso?.color === 'yellow' ? 'warning' : 'good'}
          icon={<Activity className="w-5 h-5" />}
          sparkline={sparklines.z_rms}
        />
        <MetricCard
          title="X RMS Velocity"
          value={sensor.x_rms.toFixed(3)}
          unit="mm/s"
          status={sensor.x_rms > 4 ? 'critical' : sensor.x_rms > 2 ? 'warning' : 'good'}
          icon={<Activity className="w-5 h-5" />}
          sparkline={sparklines.x_rms}
        />
        <MetricCard
          title="Z Peak Velocity"
          value={sensor.z_peak.toFixed(3)}
          unit="mm/s"
          icon={<TrendingUp className="w-5 h-5" />}
        />
        <MetricCard
          title="X Peak Velocity"
          value={sensor.x_peak.toFixed(3)}
          unit="mm/s"
          icon={<TrendingUp className="w-5 h-5" />}
        />
        <MetricCard
          title="Z Acceleration"
          value={sensor.z_accel.toFixed(3)}
          unit="mm/s²"
          icon={<Activity className="w-5 h-5" />}
        />
        <MetricCard
          title="X Acceleration"
          value={sensor.x_accel.toFixed(3)}
          unit="mm/s²"
          icon={<Activity className="w-5 h-5" />}
        />
        <MetricCard
          title="Temperature"
          value={sensor.temperature.toFixed(1)}
          unit="°C"
          status={sensor.temperature > 70 ? 'critical' : sensor.temperature > 50 ? 'warning' : 'good'}
          icon={<Thermometer className="w-5 h-5" />}
          sparkline={sparklines.temp}
        />
        <MetricCard
          title="Bearing Health"
          value={bearingHealth.toFixed(0)}
          unit="%"
          status={bearingHealth > 80 ? 'good' : bearingHealth > 60 ? 'warning' : 'critical'}
          icon={<Activity className="w-5 h-5" />}
        />
        <MetricCard
          title="ISO10816 Class"
          value={iso?.class || 'N/A'}
          status={iso?.color === 'red' ? 'critical' : iso?.color === 'yellow' ? 'warning' : 'good'}
          icon={<AlertCircle className="w-5 h-5" />}
        />
        <MetricCard
          title="ML Confidence"
          value={ml ? `${(ml.confidence * 100).toFixed(1)}%` : 'N/A'}
          status={ml && ml.class === 1 ? 'critical' : 'good'}
          icon={<Activity className="w-5 h-5" />}
        />
        <MetricCard
          title="ML Prediction"
          value={ml?.class_name || 'NORMAL'}
          status={ml && ml.class === 1 ? 'critical' : 'good'}
          icon={<AlertCircle className="w-5 h-5" />}
        />
        <MetricCard
          title="Z Kurtosis"
          value={data.features?.z_kurtosis?.toFixed(2) || '0.00'}
          icon={<TrendingUp className="w-5 h-5" />}
        />
        <MetricCard
          title="X Kurtosis"
          value={data.features?.x_kurtosis?.toFixed(2) || '0.00'}
          icon={<TrendingUp className="w-5 h-5" />}
        />
        <MetricCard
          title="Z Crest Factor"
          value={data.features?.z_crest_factor?.toFixed(2) || '0.00'}
          icon={<Activity className="w-5 h-5" />}
        />
        <MetricCard
          title="X Crest Factor"
          value={data.features?.x_crest_factor?.toFixed(2) || '0.00'}
          icon={<Activity className="w-5 h-5" />}
        />
        <MetricCard
          title="Z/X Ratio"
          value={data.features?.z_x_ratio?.toFixed(3) || '0.000'}
          icon={<TrendingUp className="w-5 h-5" />}
        />
      </div>

      {/* Premium Live Gauges Section */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
        <AdvancedChart title="Z Axis Velocity" subtitle="Real-time vibration monitoring">
          <div className="flex flex-col items-center">
            <LiveGauge
              value={sensor.z_rms}
              min={0}
              max={10}
              label="Z RMS"
              unit="mm/s"
              thresholds={{ warn: 2.0, alarm: 4.0 }}
              size="lg"
            />
            <div className="mt-6 flex items-center gap-4 text-sm w-full justify-center">
              <div className="text-center">
                <p className="text-text-muted mb-1">Peak</p>
                <p className="text-lg font-mono font-bold text-primary">{sensor.z_peak.toFixed(3)}</p>
              </div>
              <div className="w-px h-8 bg-border/50" />
              <div className="text-center">
                <p className="text-text-muted mb-1">Accel</p>
                <p className="text-lg font-mono font-bold text-primary">{sensor.z_accel.toFixed(3)}</p>
              </div>
            </div>
          </div>
        </AdvancedChart>

        <AdvancedChart title="X Axis Velocity" subtitle="Real-time vibration monitoring">
          <div className="flex flex-col items-center">
            <LiveGauge
              value={sensor.x_rms}
              min={0}
              max={10}
              label="X RMS"
              unit="mm/s"
              thresholds={{ warn: 2.0, alarm: 4.0 }}
              size="lg"
            />
            <div className="mt-6 flex items-center gap-4 text-sm w-full justify-center">
              <div className="text-center">
                <p className="text-text-muted mb-1">Peak</p>
                <p className="text-lg font-mono font-bold text-primary">{sensor.x_peak.toFixed(3)}</p>
              </div>
              <div className="w-px h-8 bg-border/50" />
              <div className="text-center">
                <p className="text-text-muted mb-1">Accel</p>
                <p className="text-lg font-mono font-bold text-primary">{sensor.x_accel.toFixed(3)}</p>
              </div>
            </div>
          </div>
        </AdvancedChart>

        <AdvancedChart title="Temperature & Health" subtitle="System thermal monitoring">
          <div className="flex flex-col items-center">
            <LiveGauge
              value={sensor.temperature}
              min={0}
              max={100}
              label="Temp"
              unit="°C"
              thresholds={{ warn: 50, alarm: 70 }}
              size="lg"
            />
            <div className="mt-6 flex flex-col gap-3 w-full">
              <div>
                <div className="flex justify-between mb-1 text-sm">
                  <span className="text-text-muted">Bearing Health</span>
                  <span className="font-mono font-bold text-primary">{bearingHealth.toFixed(0)}%</span>
                </div>
                <div className="h-2 bg-background/50 rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all duration-300 ${
                      bearingHealth > 80 ? 'bg-success' : bearingHealth > 60 ? 'bg-warning' : 'bg-critical'
                    }`}
                    style={{ width: `${Math.min(bearingHealth, 100)}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        </AdvancedChart>
      </div>

      {/* AI Predictions & Advanced Metrics Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
        <AdvancedChart 
          title="ML Intelligence" 
          subtitle="Predictive health assessment"
          headerAction={
            <StatusBadge
              status={ml && ml.class === 1 ? 'critical' : 'active'}
              label={ml?.class_name || 'NORMAL'}
              size="sm"
              animated
            />
          }
        >
          <div className="space-y-4">
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-text-muted font-medium">Prediction Confidence</span>
                <span className="font-mono font-bold text-primary">{ml ? `${(ml.confidence * 100).toFixed(1)}%` : 'N/A'}</span>
              </div>
              <div className="h-3 bg-background/50 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-primary to-primary/50 transition-all duration-300"
                  style={{ width: `${(ml?.confidence || 0) * 100}%` }}
                />
              </div>
            </div>
            <div className="pt-3 border-t border-border/30">
              <p className="text-xs text-text-muted mb-2">Model Class Distribution</p>
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-background/30 rounded p-2 text-center">
                  <p className="text-xs text-text-muted mb-1">Normal</p>
                  <p className="font-mono font-bold text-success">Class 0</p>
                </div>
                <div className="bg-background/30 rounded p-2 text-center">
                  <p className="text-xs text-text-muted mb-1">Anomaly</p>
                  <p className="font-mono font-bold text-critical">Class 1</p>
                </div>
              </div>
            </div>
          </div>
        </AdvancedChart>

        <AdvancedChart 
          title="ISO 10816-3" 
          subtitle="International vibration standard"
          headerAction={
            <StatusBadge
              status={iso?.color === 'red' ? 'critical' : iso?.color === 'yellow' ? 'warning' : 'active'}
              label={iso?.class || 'Unknown'}
              size="sm"
              animated
            />
          }
        >
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-background/30 rounded-lg p-4 border border-border/30">
                <p className="text-xs text-text-muted mb-2">Zone A</p>
                <p className="text-sm font-semibold text-text">0 - 2.3</p>
                <p className="text-xs text-text-muted mt-1">Good</p>
              </div>
              <div className="bg-background/30 rounded-lg p-4 border border-border/30">
                <p className="text-xs text-text-muted mb-2">Zone B</p>
                <p className="text-sm font-semibold text-text">2.3 - 4.5</p>
                <p className="text-xs text-text-muted mt-1">Acceptable</p>
              </div>
              <div className="bg-background/30 rounded-lg p-4 border border-border/30">
                <p className="text-xs text-text-muted mb-2">Zone C</p>
                <p className="text-sm font-semibold text-text">4.5 - 7.1</p>
                <p className="text-xs text-text-muted mt-1">Caution</p>
              </div>
              <div className="bg-background/30 rounded-lg p-4 border border-border/30">
                <p className="text-xs text-text-muted mb-2">Zone D</p>
                <p className="text-sm font-semibold text-text">{`> 7.1`}</p>
                <p className="text-xs text-text-muted mt-1">Unacceptable</p>
              </div>
            </div>
            <div className="mt-3 p-3 bg-primary/10 border border-primary/30 rounded-lg">
              <p className="text-sm font-mono text-primary">Current: {iso?.class || 'N/A'}</p>
            </div>
          </div>
        </AdvancedChart>
      </div>

      {/* Advanced Signal Analysis */}
      <AdvancedChart 
        title="Signal Characteristics" 
        subtitle="Advanced feature extraction & analysis"
        className="mt-6"
      >
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="bg-background/30 rounded-lg p-4 border border-border/30 hover:border-primary/40 transition-colors">
            <p className="text-xs text-text-muted mb-1 uppercase">Z Kurtosis</p>
            <p className="text-xl font-mono font-bold text-primary">{data.features?.z_kurtosis?.toFixed(2) || '0.00'}</p>
          </div>
          <div className="bg-background/30 rounded-lg p-4 border border-border/30 hover:border-primary/40 transition-colors">
            <p className="text-xs text-text-muted mb-1 uppercase">X Kurtosis</p>
            <p className="text-xl font-mono font-bold text-primary">{data.features?.x_kurtosis?.toFixed(2) || '0.00'}</p>
          </div>
          <div className="bg-background/30 rounded-lg p-4 border border-border/30 hover:border-primary/40 transition-colors">
            <p className="text-xs text-text-muted mb-1 uppercase">Z Crest</p>
            <p className="text-xl font-mono font-bold text-primary">{data.features?.z_crest_factor?.toFixed(2) || '0.00'}</p>
          </div>
          <div className="bg-background/30 rounded-lg p-4 border border-border/30 hover:border-primary/40 transition-colors">
            <p className="text-xs text-text-muted mb-1 uppercase">X Crest</p>
            <p className="text-xl font-mono font-bold text-primary">{data.features?.x_crest_factor?.toFixed(2) || '0.00'}</p>
          </div>
          <div className="bg-background/30 rounded-lg p-4 border border-border/30 hover:border-primary/40 transition-colors">
            <p className="text-xs text-text-muted mb-1 uppercase">Z/X Ratio</p>
            <p className="text-xl font-mono font-bold text-primary">{data.features?.z_x_ratio?.toFixed(3) || '0.000'}</p>
          </div>
          <div className="bg-background/30 rounded-lg p-4 border border-border/30 hover:border-primary/40 transition-colors">
            <p className="text-xs text-text-muted mb-1 uppercase">ISO Class</p>
            <p className="text-xl font-mono font-bold text-primary">{iso?.class || 'N/A'}</p>
          </div>
        </div>
      </AdvancedChart>

      {/* Action Buttons - Premium Style */}
      <div className="flex gap-3 mt-8 flex-wrap">
        <button className="px-6 py-3 bg-gradient-to-r from-primary to-primary/80 border border-primary/50 rounded-lg text-text font-semibold hover:shadow-lg hover:shadow-primary/30 transition-all duration-200 flex items-center gap-2 neon-glow-hover">
          <Download className="w-4 h-4" />
          Export Data
        </button>
        <button className="px-6 py-3 bg-card border border-border hover:border-primary/40 rounded-lg text-text font-semibold hover:bg-primary/5 transition-all duration-200 flex items-center gap-2">
          <RefreshCw className="w-4 h-4" />
          Refresh Now
        </button>
        <button className="px-6 py-3 bg-card border border-border hover:border-primary/40 rounded-lg text-text font-semibold hover:bg-primary/5 transition-all duration-200">
          Configure Alerts
        </button>
      </div>
    </div>
  )
}

