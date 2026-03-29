import { useEffect, useState } from 'react'
import { wsClient, WebSocketData } from '../lib/websocket'
import { Activity, Zap, Thermometer, AlertCircle, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'

export default function NewDashboard() {
  const [data, setData] = useState<WebSocketData | null>(null)
  const [history, setHistory] = useState<any[]>([])
  const [zHistory, setZHistory] = useState<any[]>([])
  const [xHistory, setXHistory] = useState<any[]>([])
  const [tempHistory, setTempHistory] = useState<any[]>([])

  useEffect(() => {
    const handleData = (newData: WebSocketData) => {
      setData(newData)
      const timestamp = new Date().toLocaleTimeString('en-US', { hour12: false })
      
      setHistory(prev => {
        const updated = [...prev, {
          time: timestamp,
          z_rms: newData.sensor_data.z_rms,
          x_rms: newData.sensor_data.x_rms,
          temp: newData.sensor_data.temperature,
          z_accel: newData.sensor_data.z_accel,
          x_accel: newData.sensor_data.x_accel,
        }]
        return updated.slice(-60) // Keep last 60 points
      })

      setZHistory(prev => [...prev, { time: timestamp, value: newData.sensor_data.z_rms }].slice(-30))
      setXHistory(prev => [...prev, { time: timestamp, value: newData.sensor_data.x_rms }].slice(-30))
      setTempHistory(prev => [...prev, { time: timestamp, value: newData.sensor_data.temperature }].slice(-30))
    }

    const unsubscribe = wsClient.subscribe(handleData)
    return unsubscribe
  }, [])

  if (!data) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
        <div className="text-center">
          <div className="relative w-20 h-20 mx-auto mb-6">
            <div className="absolute inset-0 border-4 border-cyan-500/30 rounded-full"></div>
            <div className="absolute inset-0 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin"></div>
            <Zap className="absolute inset-0 m-auto w-8 h-8 text-cyan-400" />
          </div>
          <h2 className="text-2xl font-bold text-cyan-400 animate-pulse">Initializing System</h2>
          <p className="text-slate-500 text-sm mt-2">Connecting to sensors...</p>
        </div>
      </div>
    )
  }

  const { sensor_data: sensor, ml_prediction } = data
  const isHealthy = sensor.alarm_status === 'OK'
  const isCritical = sensor.alarm_status === 'Critical'

  // Calculate trends
  const zTrend = zHistory.length > 2 ? zHistory[zHistory.length - 1].value - zHistory[0].value : 0
  const xTrend = xHistory.length > 2 ? xHistory[xHistory.length - 1].value - xHistory[0].value : 0
  const tempTrend = tempHistory.length > 2 ? tempHistory[tempHistory.length - 1].value - tempHistory[0].value : 0

  const TrendIcon = (trend: number) => {
    if (trend > 0.05) return <TrendingUp className="w-4 h-4 text-red-400" />
    if (trend < -0.05) return <TrendingDown className="w-4 h-4 text-emerald-400" />
    return <Minus className="w-4 h-4 text-slate-500" />
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-6">
      <div className="max-w-[1920px] mx-auto space-y-6">
        
        {/* Header Status Bar */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
              System Overview
            </h1>
            <p className="text-slate-500 text-sm mt-1">Real-time railway monitoring dashboard</p>
          </div>
          <div className="flex items-center gap-4">
            <div className={`px-4 py-2 rounded-lg border ${
              isHealthy ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' :
              isCritical ? 'bg-red-500/10 border-red-500/30 text-red-400' :
              'bg-amber-500/10 border-amber-500/30 text-amber-400'
            }`}>
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${
                  isHealthy ? 'bg-emerald-400' : isCritical ? 'bg-red-400' : 'bg-amber-400'
                } animate-pulse`} />
                <span className="font-semibold text-sm">{sensor.alarm_status}</span>
              </div>
            </div>
            <div className="px-4 py-2 rounded-lg bg-slate-800/50 border border-slate-700/50">
              <div className="flex items-center gap-2 text-slate-300">
                <Activity className="w-4 h-4 text-cyan-400" />
                <span className="font-semibold text-sm">{data.source === 'LIVE_FEED' ? 'Live' : 'Demo'}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Primary Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          
          {/* Z-Axis Vibration */}
          <div className="relative group">
            <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/20 to-blue-500/20 rounded-2xl blur-xl group-hover:blur-2xl transition-all duration-300" />
            <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6 hover:border-cyan-500/50 transition-all duration-300">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <p className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-1">Z-Axis RMS</p>
                  <div className="flex items-baseline gap-2">
                    <span className="text-4xl font-bold text-cyan-400">{sensor.z_rms.toFixed(3)}</span>
                    <span className="text-slate-500 text-sm">mm/s</span>
                  </div>
                </div>
                {TrendIcon(zTrend)}
              </div>
              <div className="h-16 -mx-2">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={zHistory}>
                    <defs>
                      <linearGradient id="colorZ" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#22d3ee" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <Area type="monotone" dataKey="value" stroke="#22d3ee" strokeWidth={2} fillOpacity={1} fill="url(#colorZ)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-4 pt-4 border-t border-slate-800/50 flex items-center justify-between text-xs">
                <span className="text-slate-500">Peak: <span className="text-cyan-400 font-semibold">{sensor.z_peak.toFixed(2)}</span></span>
                <span className="text-slate-500">Accel: <span className="text-cyan-400 font-semibold">{sensor.z_accel.toFixed(2)}G</span></span>
              </div>
            </div>
          </div>

          {/* X-Axis Vibration */}
          <div className="relative group">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/20 to-teal-500/20 rounded-2xl blur-xl group-hover:blur-2xl transition-all duration-300" />
            <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6 hover:border-emerald-500/50 transition-all duration-300">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <p className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-1">X-Axis RMS</p>
                  <div className="flex items-baseline gap-2">
                    <span className="text-4xl font-bold text-emerald-400">{sensor.x_rms.toFixed(3)}</span>
                    <span className="text-slate-500 text-sm">mm/s</span>
                  </div>
                </div>
                {TrendIcon(xTrend)}
              </div>
              <div className="h-16 -mx-2">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={xHistory}>
                    <defs>
                      <linearGradient id="colorX" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <Area type="monotone" dataKey="value" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#colorX)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-4 pt-4 border-t border-slate-800/50 flex items-center justify-between text-xs">
                <span className="text-slate-500">Peak: <span className="text-emerald-400 font-semibold">{sensor.x_peak.toFixed(2)}</span></span>
                <span className="text-slate-500">Accel: <span className="text-emerald-400 font-semibold">{sensor.x_accel.toFixed(2)}G</span></span>
              </div>
            </div>
          </div>

          {/* Temperature */}
          <div className="relative group">
            <div className="absolute inset-0 bg-gradient-to-br from-orange-500/20 to-red-500/20 rounded-2xl blur-xl group-hover:blur-2xl transition-all duration-300" />
            <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6 hover:border-orange-500/50 transition-all duration-300">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <p className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-1">Temperature</p>
                  <div className="flex items-baseline gap-2">
                    <span className="text-4xl font-bold text-orange-400">{sensor.temperature.toFixed(1)}</span>
                    <span className="text-slate-500 text-sm">°C</span>
                  </div>
                </div>
                <Thermometer className="w-5 h-5 text-orange-400" />
              </div>
              <div className="h-16 -mx-2">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={tempHistory}>
                    <defs>
                      <linearGradient id="colorTemp" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#fb923c" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#fb923c" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <Area type="monotone" dataKey="value" stroke="#fb923c" strokeWidth={2} fillOpacity={1} fill="url(#colorTemp)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-4 pt-4 border-t border-slate-800/50 flex items-center justify-between text-xs">
                <span className="text-slate-500">Trend: <span className={`font-semibold ${tempTrend > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                  {tempTrend > 0 ? '+' : ''}{tempTrend.toFixed(2)}°C
                </span></span>
                <span className="text-slate-500">Normal</span>
              </div>
            </div>
          </div>

          {/* System Health */}
          <div className="relative group">
            <div className="absolute inset-0 bg-gradient-to-br from-purple-500/20 to-pink-500/20 rounded-2xl blur-xl group-hover:blur-2xl transition-all duration-300" />
            <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6 hover:border-purple-500/50 transition-all duration-300">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <p className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-1">Health Score</p>
                  <div className="flex items-baseline gap-2">
                    <span className="text-4xl font-bold text-purple-400">{sensor.data_quality?.toFixed(0) || '98'}</span>
                    <span className="text-slate-500 text-sm">%</span>
                  </div>
                </div>
                <Zap className="w-5 h-5 text-purple-400" />
              </div>
              <div className="h-16 flex items-center">
                <div className="w-full">
                  <div className="h-3 bg-slate-800 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all duration-500 ease-out"
                      style={{ width: `${sensor.data_quality || 98}%` }}
                    />
                  </div>
                  <div className="flex justify-between mt-2 text-[10px] text-slate-600 font-semibold">
                    <span>0%</span>
                    <span>50%</span>
                    <span>100%</span>
                  </div>
                </div>
              </div>
              <div className="mt-4 pt-4 border-t border-slate-800/50 flex items-center justify-between text-xs">
                <span className="text-slate-500">Uptime</span>
                <span className="text-purple-400 font-semibold">{sensor.uptime}h</span>
              </div>
            </div>
          </div>
        </div>

        {/* Large Combined Chart */}
        <div className="relative group">
          <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/10 to-purple-500/10 rounded-2xl blur-2xl" />
          <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-slate-200">Vibration Analysis</h2>
              <div className="flex items-center gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-cyan-400" />
                  <span className="text-slate-400">Z-Axis</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-emerald-400" />
                  <span className="text-slate-400">X-Axis</span>
                </div>
              </div>
            </div>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={history} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis 
                    dataKey="time" 
                    stroke="#64748b" 
                    style={{ fontSize: '12px' }}
                    tickFormatter={(value) => {
                      const parts = value.split(':')
                      return `${parts[1]}:${parts[2]}`
                    }}
                  />
                  <YAxis stroke="#64748b" style={{ fontSize: '12px' }} />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#0f172a', 
                      border: '1px solid #334155',
                      borderRadius: '8px',
                      padding: '12px'
                    }}
                    labelStyle={{ color: '#94a3b8', marginBottom: '8px' }}
                    itemStyle={{ color: '#e2e8f0' }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="z_rms" 
                    stroke="#22d3ee" 
                    strokeWidth={2}
                    dot={false}
                    name="Z-Axis RMS"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="x_rms" 
                    stroke="#10b981" 
                    strokeWidth={2}
                    dot={false}
                    name="X-Axis RMS"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Bottom Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <StatCard label="Frequency" value={`${sensor.frequency?.toFixed(1) || '0'} Hz`} color="text-blue-400" />
          <StatCard label="Kurtosis" value={sensor.kurtosis?.toFixed(2) || '0'} color="text-violet-400" />
          <StatCard label="Crest Factor" value={sensor.crest_factor?.toFixed(2) || '0'} color="text-pink-400" />
          <StatCard label="RMS Overall" value={`${sensor.rms_overall?.toFixed(3) || '0'} mm/s`} color="text-cyan-400" />
          <StatCard label="ISO Class" value={sensor.iso_class || 'Zone A'} color="text-emerald-400" />
          <StatCard label="Bearing Health" value={`${sensor.bearing_health?.toFixed(0) || '98'}%`} color="text-amber-400" />
        </div>

        {/* ML Prediction Card */}
        {ml_prediction && (
          <div className="relative group">
            <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-pink-500/10 rounded-2xl blur-xl" />
            <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                  <AlertCircle className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-200">AI Intelligence</h3>
                  <p className="text-sm text-slate-500">Machine learning prediction</p>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-slate-800/30 rounded-lg p-4">
                  <p className="text-xs text-slate-500 mb-1">Classification</p>
                  <p className={`text-lg font-bold ${ml_prediction.class === 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {ml_prediction.class_name}
                  </p>
                </div>
                <div className="bg-slate-800/30 rounded-lg p-4">
                  <p className="text-xs text-slate-500 mb-1">Confidence</p>
                  <p className="text-lg font-bold text-purple-400">{(ml_prediction.confidence * 100).toFixed(1)}%</p>
                </div>
                <div className="bg-slate-800/30 rounded-lg p-4">
                  <p className="text-xs text-slate-500 mb-1">Status</p>
                  <p className="text-lg font-bold text-cyan-400">Monitoring</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function StatCard({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-xl p-4 hover:border-slate-700/50 transition-all duration-300">
      <p className="text-xs text-slate-500 uppercase font-semibold mb-2">{label}</p>
      <p className={`text-xl font-bold ${color}`}>{value}</p>
    </div>
  )
}
