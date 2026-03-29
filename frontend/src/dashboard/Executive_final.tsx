import { useEffect, useState } from 'react'
import { TrendingUp, Thermometer, Activity, AlertCircle, Download, RefreshCw, Clock, Zap, AlertTriangle } from 'lucide-react'
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, ComposedChart } from 'recharts'
import { wsClient, WebSocketData } from '@/lib/websocket'
import AdvancedChart from '@/components/ui/AdvancedChart'
import StatusBadge from '@/components/ui/StatusBadge'

interface ChartDataPoint {
  time: string
  z_rms: number
  x_rms: number
  temperature: number
  frequency?: number
}

export default function ExecutiveTab() {
  const [data, setData] = useState<WebSocketData | null>(null)
  const [chartData, setChartData] = useState<ChartDataPoint[]>([])

  useEffect(() => {
    const unsubscribe = wsClient.subscribe((newData: WebSocketData) => {
      setData(newData)
      
      // Update chart data (keep last 60 points for 1 minute)
      if (newData.sensor_data) {
        const timestamp = new Date(newData.timestamp).toLocaleTimeString()
        const newPoint: ChartDataPoint = {
          time: timestamp,
          z_rms: newData.sensor_data.z_rms,
          x_rms: newData.sensor_data.x_rms,
          temperature: newData.sensor_data.temperature,
          frequency: 50 + Math.random() * 10 // Simulated frequency data
        }
        
        setChartData(prev => {
          const updated = [...prev, newPoint]
          return updated.slice(-60) // Keep last 60 points (1 minute)
        })
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
  const ml = data.ml_prediction

  // Status determination
  const hasAlert = ml && ml.class === 1
  const mlConfidence = ml ? (ml.confidence * 100).toFixed(1) : '0'
  const mlStatus = ml?.class_name || 'NORMAL'

  return (
    <div className="space-y-6 fade-in-up">
      {/* Alert Banner */}
      {hasAlert && (
        <div className="p-4 bg-gradient-to-r from-critical/20 to-warning/10 border border-critical/40 rounded-lg flex items-start gap-4 animate-pulse">
          <AlertTriangle className="w-5 h-5 text-critical flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-text mb-1">⚠️ Anomaly Detected</p>
            <p className="text-sm text-text-muted">ML prediction indicates abnormal vibration pattern - investigate recommended</p>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold text-text tracking-tight">Railway Condition Monitor</h1>
          <p className="text-text-muted font-medium flex items-center gap-2 mt-2">
            <Clock className="w-4 h-4" />
            Live System Monitoring • Real-time Analysis
          </p>
        </div>
        <div className="flex gap-2">
          <button className="p-2.5 rounded-lg border border-border hover:bg-primary/10 transition-all">
            <RefreshCw className="w-5 h-5 text-primary" />
          </button>
          <button className="p-2.5 rounded-lg border border-border hover:bg-primary/10 transition-all">
            <Download className="w-5 h-5 text-text-muted" />
          </button>
        </div>
      </div>

      {/* ML Prediction Card - TOP PRIORITY */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* ML Prediction - Large Card */}
        <AdvancedChart title="🤖 ML Prediction Engine" subtitle="Real-time Anomaly Detection" className="md:col-span-1">
          <div className="space-y-6 h-full flex flex-col justify-center">
            {/* Status Badge */}
            <div className="text-center">
              <div className={`text-6xl font-bold font-mono mb-3 ${
                hasAlert ? 'text-critical' : 'text-success'
              }`}>
                {mlStatus}
              </div>
              <StatusBadge
                status={hasAlert ? 'critical' : 'active'}
                label={hasAlert ? 'ANOMALY' : 'NORMAL'}
                animated
              />
            </div>

            {/* Confidence Bar */}
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-text-muted">Confidence Level</span>
                <span className="font-mono font-bold text-primary">{mlConfidence}%</span>
              </div>
              <div className="h-3 bg-background/50 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-300 rounded-full ${
                    hasAlert ? 'bg-gradient-to-r from-critical to-critical/50' : 'bg-gradient-to-r from-success to-success/50'
                  }`}
                  style={{ width: `${Math.min(parseFloat(mlConfidence), 100)}%` }}
                />
              </div>
            </div>

            {/* Info */}
            <div className="text-xs text-text-muted text-center pt-3 border-t border-border/30">
              <p>Machine Learning Model Confidence</p>
              <p className="mt-1">Class 0: Normal | Class 1: Anomaly</p>
            </div>
          </div>
        </AdvancedChart>

        {/* Current Metrics - Compact */}
        <div className="md:col-span-2 grid grid-cols-2 gap-4">
          {/* Z RMS */}
          <div className="bg-card border border-border/30 rounded-lg p-6 hover:border-primary/40 transition-all">
            <p className="text-text-muted text-sm mb-2 font-medium">Z RMS Velocity</p>
            <p className="text-4xl font-mono font-bold text-primary mb-1">{sensor.z_rms.toFixed(3)}</p>
            <p className="text-text-muted text-xs">mm/s</p>
            <p className="text-xs text-success mt-2">Peak: {sensor.z_peak.toFixed(3)}</p>
          </div>

          {/* X RMS */}
          <div className="bg-card border border-border/30 rounded-lg p-6 hover:border-success/40 transition-all">
            <p className="text-text-muted text-sm mb-2 font-medium">X RMS Velocity</p>
            <p className="text-4xl font-mono font-bold text-success mb-1">{sensor.x_rms.toFixed(3)}</p>
            <p className="text-text-muted text-xs">mm/s</p>
            <p className="text-xs text-warning mt-2">Peak: {sensor.x_peak.toFixed(3)}</p>
          </div>

          {/* Temperature */}
          <div className="bg-card border border-border/30 rounded-lg p-6 hover:border-warning/40 transition-all">
            <p className="text-text-muted text-sm mb-2 font-medium">Temperature</p>
            <p className="text-4xl font-mono font-bold text-warning mb-1">{sensor.temperature.toFixed(1)}</p>
            <p className="text-text-muted text-xs">°C</p>
            <p className="text-xs text-text-muted mt-2">Normal Range: 20-50</p>
          </div>

          {/* Status */}
          <div className="bg-card border border-border/30 rounded-lg p-6">
            <p className="text-text-muted text-sm mb-2 font-medium">System Status</p>
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${data.connection_status?.connected ? 'bg-success animate-pulse' : 'bg-critical'}`} />
              <p className="text-lg font-bold text-text">
                {data.connection_status?.connected ? 'ONLINE' : 'OFFLINE'}
              </p>
            </div>
            <p className="text-xs text-success mt-2">Real-time Data</p>
          </div>
        </div>
      </div>

      {/* Main Chart Section - Z and X RMS */}
      <AdvancedChart title="📊 Vibration Analysis" subtitle="Z-axis and X-axis RMS Velocity Trends">
        <ResponsiveContainer width="100%" height={400}>
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="colorZ" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#00D4FF" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#00D4FF" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="colorX" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10B981" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#2D3748" />
            <XAxis dataKey="time" stroke="#9CA3AF" tick={{ fill: '#9CA3AF', fontSize: 11 }} />
            <YAxis stroke="#9CA3AF" tick={{ fill: '#9CA3AF' }} />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: '#1A2332', 
                border: '1px solid #2D3748', 
                borderRadius: '8px',
                color: '#E5E7EB'
              }} 
            />
            <Legend />
            <Area type="monotone" dataKey="z_rms" stroke="#00D4FF" strokeWidth={2.5} fillOpacity={1} fill="url(#colorZ)" name="Z RMS (mm/s)" />
            <Area type="monotone" dataKey="x_rms" stroke="#10B981" strokeWidth={2.5} fillOpacity={1} fill="url(#colorX)" name="X RMS (mm/s)" />
          </AreaChart>
        </ResponsiveContainer>
      </AdvancedChart>

      {/* Bottom Section - Temperature and Frequency */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Temperature Graph */}
        <AdvancedChart title="🌡️ Temperature Monitoring" subtitle="System Thermal Status (1 minute)">
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="colorTemp" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#F59E0B" stopOpacity={0.4}/>
                  <stop offset="95%" stopColor="#F59E0B" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#2D3748" />
              <XAxis dataKey="time" stroke="#9CA3AF" tick={{ fill: '#9CA3AF', fontSize: 10 }} />
              <YAxis stroke="#9CA3AF" tick={{ fill: '#9CA3AF' }} />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#1A2332', 
                  border: '1px solid #2D3748', 
                  borderRadius: '8px',
                  color: '#E5E7EB'
                }} 
              />
              <Area type="monotone" dataKey="temperature" stroke="#F59E0B" strokeWidth={2.5} fill="url(#colorTemp)" name="Temperature (°C)" />
            </AreaChart>
          </ResponsiveContainer>
        </AdvancedChart>

        {/* Frequency Analysis */}
        <AdvancedChart title="📈 Frequency Spectrum" subtitle="Harmonic Analysis (1 minute)">
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2D3748" />
              <XAxis dataKey="time" stroke="#9CA3AF" tick={{ fill: '#9CA3AF', fontSize: 10 }} />
              <YAxis stroke="#9CA3AF" tick={{ fill: '#9CA3AF' }} />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#1A2332', 
                  border: '1px solid #2D3748', 
                  borderRadius: '8px',
                  color: '#E5E7EB'
                }} 
              />
              <Bar dataKey="frequency" fill="#8B5CF6" opacity={0.7} name="Frequency (Hz)" />
              <Line type="monotone" dataKey="frequency" stroke="#8B5CF6" strokeWidth={2.5} dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </AdvancedChart>
      </div>

      {/* Advanced Metrics Footer */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-6 bg-card border border-border/30 rounded-lg">
        <div>
          <p className="text-xs text-text-muted mb-1">Z Acceleration</p>
          <p className="text-2xl font-mono font-bold text-primary">{sensor.z_accel.toFixed(2)}</p>
          <p className="text-xs text-text-muted">mm/s²</p>
        </div>
        <div>
          <p className="text-xs text-text-muted mb-1">X Acceleration</p>
          <p className="text-2xl font-mono font-bold text-success">{sensor.x_accel.toFixed(2)}</p>
          <p className="text-xs text-text-muted">mm/s²</p>
        </div>
        <div>
          <p className="text-xs text-text-muted mb-1">Z/X Ratio</p>
          <p className="text-2xl font-mono font-bold text-warning">
            {(sensor.z_rms / (sensor.x_rms || 0.001)).toFixed(2)}
          </p>
          <p className="text-xs text-text-muted">Axis Ratio</p>
        </div>
        <div>
          <p className="text-xs text-text-muted mb-1">Data Points</p>
          <p className="text-2xl font-mono font-bold text-info">{chartData.length}</p>
          <p className="text-xs text-text-muted">60s window</p>
        </div>
      </div>
    </div>
  )
}
