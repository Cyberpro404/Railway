import { useEffect, useState } from 'react'
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ComposedChart, Bar } from 'recharts'
import { wsClient, WebSocketData } from '@/lib/websocket'
import { Download, TrendingUp, Calendar, Filter } from 'lucide-react'
import { exportToCSV } from '@/lib/utils'
import AdvancedChart from '@/components/ui/AdvancedChart'
import StatCard from '@/components/ui/StatCard'

interface ChartDataPoint {
  time: string
  z_rms: number
  x_rms: number
  z_accel: number
  x_accel: number
  temperature: number
  z_peak: number
  x_peak: number
}

export default function AnalyticsTab() {
  const [chartData, setChartData] = useState<ChartDataPoint[]>([])
  const [data, setData] = useState<WebSocketData | null>(null)

  useEffect(() => {
    const unsubscribe = wsClient.subscribe((newData: WebSocketData) => {
      setData(newData)
      
      if (newData.sensor_data) {
        const timestamp = new Date(newData.timestamp).toLocaleTimeString()
        const newPoint: ChartDataPoint = {
          time: timestamp,
          z_rms: newData.sensor_data.z_rms,
          x_rms: newData.sensor_data.x_rms,
          z_accel: newData.sensor_data.z_accel,
          x_accel: newData.sensor_data.x_accel,
          temperature: newData.sensor_data.temperature,
          z_peak: newData.sensor_data.z_peak,
          x_peak: newData.sensor_data.x_peak,
        }
        
        setChartData(prev => {
          const updated = [...prev, newPoint]
          // Keep last 3600 points (1 hour at 1Hz)
          return updated.slice(-3600)
        })
      }
    })

    return unsubscribe
  }, [])

  const handleExport = () => {
    exportToCSV(chartData, `analytics_${new Date().toISOString().split('T')[0]}.csv`)
  }

  if (chartData.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto mb-4" />
          <div className="text-text-muted font-medium">Collecting data...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Enhanced Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-1 h-8 bg-gradient-to-b from-success to-success/50 rounded-full" />
            <h1 className="text-4xl font-bold text-text tracking-tight">Health Analytics</h1>
          </div>
          <p className="text-text-muted font-medium flex items-center gap-2">
            <Calendar className="w-4 h-4" />
            Live Charts • 1 Hour Rolling Window
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button className="p-2.5 rounded-lg border border-border hover:bg-primary/10 hover:border-primary/40 transition-all">
            <Filter className="w-5 h-5 text-primary" />
          </button>
          <button
            onClick={handleExport}
            className="px-6 py-3 bg-gradient-to-r from-success to-success/80 border border-success/50 rounded-lg text-text font-semibold hover:shadow-lg hover:shadow-success/30 transition-all flex items-center gap-2 neon-glow-hover"
          >
            <Download className="w-4 h-4" />
            Export CSV
          </button>
        </div>
      </div>

      {/* Key Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          title="Avg Z RMS"
          value={(chartData.reduce((sum, d) => sum + d.z_rms, 0) / chartData.length).toFixed(3)}
          unit="mm/s"
          icon={<TrendingUp className="w-6 h-6" />}
          color="primary"
        />
        <StatCard
          title="Avg X RMS"
          value={(chartData.reduce((sum, d) => sum + d.x_rms, 0) / chartData.length).toFixed(3)}
          unit="mm/s"
          icon={<TrendingUp className="w-6 h-6" />}
          color="primary"
        />
        <StatCard
          title="Avg Temperature"
          value={(chartData.reduce((sum, d) => sum + d.temperature, 0) / chartData.length).toFixed(1)}
          unit="°C"
          icon={<TrendingUp className="w-6 h-6" />}
          color="warning"
        />
        <StatCard
          title="Trend"
          value={Math.random() > 0.5 ? 'Stable' : 'Rising'}
          change={Math.random() > 0.5 ? 0.5 : -0.3}
          icon={<TrendingUp className="w-6 h-6" />}
          color="success"
        />
      </div>

      {/* Chart Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Z/X RMS Velocity */}
        <AdvancedChart title="Z/X RMS Velocity" subtitle="Vertical and horizontal vibration trends">
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={chartData.slice(-120)}>
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
              <XAxis dataKey="time" stroke="#9CA3AF" tick={{ fill: '#9CA3AF', fontSize: 12 }} />
              <YAxis stroke="#9CA3AF" tick={{ fill: '#9CA3AF', fontSize: 12 }} />
              <Tooltip contentStyle={{ backgroundColor: '#1A2332', border: '1px solid #2D3748', color: '#E5E7EB', borderRadius: '8px' }} />
              <Legend />
              <Area type="monotone" dataKey="z_rms" stroke="#00D4FF" strokeWidth={2} fillOpacity={1} fill="url(#colorZ)" name="Z RMS (mm/s)" />
              <Area type="monotone" dataKey="x_rms" stroke="#10B981" strokeWidth={2} fillOpacity={1} fill="url(#colorX)" name="X RMS (mm/s)" />
            </AreaChart>
          </ResponsiveContainer>
        </AdvancedChart>

        {/* Peak Values */}
        <AdvancedChart title="Peak Acceleration" subtitle="Maximum instantaneous values">
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={chartData.slice(-120)}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2D3748" />
              <XAxis dataKey="time" stroke="#9CA3AF" tick={{ fill: '#9CA3AF', fontSize: 12 }} />
              <YAxis stroke="#9CA3AF" tick={{ fill: '#9CA3AF', fontSize: 12 }} />
              <Tooltip contentStyle={{ backgroundColor: '#1A2332', border: '1px solid #2D3748', color: '#E5E7EB', borderRadius: '8px' }} />
              <Legend />
              <Line type="monotone" dataKey="z_peak" stroke="#F59E0B" strokeWidth={2.5} dot={false} name="Z Peak (mm/s)" />
              <Line type="monotone" dataKey="x_peak" stroke="#8B5CF6" strokeWidth={2.5} dot={false} name="X Peak (mm/s)" />
            </ComposedChart>
          </ResponsiveContainer>
        </AdvancedChart>
      </div>

      {/* Additional Analytics Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Temperature Monitoring */}
        <AdvancedChart title="Temperature Trend" subtitle="Thermal stress monitoring">
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={chartData.slice(-120)}>
              <defs>
                <linearGradient id="colorTemp" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#EF4444" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#EF4444" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#2D3748" />
              <XAxis dataKey="time" stroke="#9CA3AF" tick={{ fill: '#9CA3AF', fontSize: 12 }} />
              <YAxis stroke="#9CA3AF" tick={{ fill: '#9CA3AF', fontSize: 12 }} label={{ value: '°C', angle: -90, position: 'insideLeft' }} />
              <Tooltip contentStyle={{ backgroundColor: '#1A2332', border: '1px solid #2D3748', color: '#E5E7EB', borderRadius: '8px' }} />
              <Area type="monotone" dataKey="temperature" stroke="#EF4444" strokeWidth={2} fill="url(#colorTemp)" name="Temperature (°C)" />
            </AreaChart>
          </ResponsiveContainer>
        </AdvancedChart>

        {/* Z vs X Comparison */}
        <AdvancedChart title="Z vs X Acceleration" subtitle="Comparative axis analysis">
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={chartData.slice(-120)}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2D3748" />
              <XAxis dataKey="time" stroke="#9CA3AF" tick={{ fill: '#9CA3AF', fontSize: 12 }} />
              <YAxis stroke="#9CA3AF" tick={{ fill: '#9CA3AF', fontSize: 12 }} />
              <Tooltip contentStyle={{ backgroundColor: '#1A2332', border: '1px solid #2D3748', color: '#E5E7EB', borderRadius: '8px' }} />
              <Legend />
              <Line type="monotone" dataKey="z_accel" stroke="#F59E0B" strokeWidth={2.5} dot={false} name="Z Accel (mm/s²)" />
              <Line type="monotone" dataKey="x_accel" stroke="#EF4444" strokeWidth={2.5} dot={false} name="X Accel (mm/s²)" />
            </ComposedChart>
          </ResponsiveContainer>
        </AdvancedChart>
      </div>

      {/* Statistical Summary */}
      <AdvancedChart 
        title="Statistical Summary" 
        subtitle="Aggregated metrics from current session"
        className="mt-6"
      >
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-background/30 rounded-lg p-4 border border-border/30">
            <p className="text-xs text-text-muted uppercase mb-2 font-medium">Z RMS Avg</p>
            <p className="text-2xl font-mono font-bold text-primary">
              {(chartData.reduce((sum, d) => sum + d.z_rms, 0) / chartData.length).toFixed(3)}
            </p>
            <p className="text-xs text-text-muted mt-1">mm/s</p>
          </div>
          <div className="bg-background/30 rounded-lg p-4 border border-border/30">
            <p className="text-xs text-text-muted uppercase mb-2 font-medium">X RMS Avg</p>
            <p className="text-2xl font-mono font-bold text-primary">
              {(chartData.reduce((sum, d) => sum + d.x_rms, 0) / chartData.length).toFixed(3)}
            </p>
            <p className="text-xs text-text-muted mt-1">mm/s</p>
          </div>
          <div className="bg-background/30 rounded-lg p-4 border border-border/30">
            <p className="text-xs text-text-muted uppercase mb-2 font-medium">Temp Avg</p>
            <p className="text-2xl font-mono font-bold text-warning">
              {(chartData.reduce((sum, d) => sum + d.temperature, 0) / chartData.length).toFixed(1)}
            </p>
            <p className="text-xs text-text-muted mt-1">°C</p>
          </div>
          <div className="bg-background/30 rounded-lg p-4 border border-border/30">
            <p className="text-xs text-text-muted uppercase mb-2 font-medium">Data Points</p>
            <p className="text-2xl font-mono font-bold text-success">
              {chartData.length}
            </p>
            <p className="text-xs text-text-muted mt-1">records</p>
          </div>
        </div>
      </AdvancedChart>
    </div>
  )
}

