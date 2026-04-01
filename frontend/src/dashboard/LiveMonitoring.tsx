import { useEffect, useState } from 'react'
import { wsClient, WebSocketData } from '../lib/websocket'
import { Activity, Thermometer, Zap, Gauge, Radio } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'

export default function LiveMonitoring() {
  const [data, setData] = useState<WebSocketData | null>(null)
  const [waveform, setWaveform] = useState<any[]>([])

  useEffect(() => {
    const unsubscribe = wsClient.subscribe((newData: WebSocketData) => {
      setData(newData)
      const ts = new Date().toLocaleTimeString('en-US', { hour12: false })
      setWaveform(prev => {
        const updated = [...prev, {
          time: ts,
          z_rms: newData.sensor_data?.z_rms ?? 0,
          x_rms: newData.sensor_data?.x_rms ?? 0,
          temperature: newData.sensor_data?.temperature ?? 0,
          z_accel: newData.sensor_data?.z_accel ?? 0,
        }]
        return updated.slice(-60)
      })
    })
    return unsubscribe
  }, [])

  const isConnected = data?.connection_status?.connected ?? false
  const s = data?.sensor_data

  const gauges = [
    { label: 'Z-RMS', value: s?.z_rms ?? 0, unit: 'mm/s', max: 10, color: '#3b82f6', icon: Activity },
    { label: 'X-RMS', value: s?.x_rms ?? 0, unit: 'mm/s', max: 10, color: '#10b981', icon: Activity },
    { label: 'Temperature', value: s?.temperature ?? 0, unit: '°C', max: 100, color: '#f59e0b', icon: Thermometer },
    { label: 'Z-Peak Accel', value: s?.z_accel ?? 0, unit: 'G', max: 20, color: '#ef4444', icon: Zap },
    { label: 'X-Peak Accel', value: s?.x_accel ?? 0, unit: 'G', max: 20, color: '#8b5cf6', icon: Zap },
    { label: 'Frequency', value: s?.frequency ?? 0, unit: 'Hz', max: 200, color: '#06b6d4', icon: Radio },
    { label: 'Kurtosis', value: s?.kurtosis ?? 0, unit: '', max: 10, color: '#ec4899', icon: Gauge },
    { label: 'Crest Factor', value: s?.crest_factor ?? 0, unit: '', max: 10, color: '#14b8a6', icon: Gauge },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-6">
      <div className="max-w-[1920px] mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-teal-400 to-cyan-400 bg-clip-text text-transparent">
              Live Monitoring
            </h1>
            <p className="text-slate-500 text-sm mt-1">Real-time sensor data & waveforms</p>
          </div>
          <div className={`px-4 py-2 rounded-lg border text-sm font-semibold ${
            isConnected ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' : 'bg-red-500/10 border-red-500/30 text-red-400'
          }`}>
            {isConnected ? '● LIVE' : '○ OFFLINE'}
          </div>
        </div>

        {/* Gauge Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {gauges.map(g => {
            const Icon = g.icon
            const pct = Math.min((g.value / g.max) * 100, 100)
            return (
              <div key={g.label} className="bg-slate-900/80 border border-slate-800/50 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Icon className="w-4 h-4" style={{ color: g.color }} />
                  <span className="text-xs text-slate-400 font-semibold uppercase">{g.label}</span>
                </div>
                <div className="text-2xl font-bold text-white mb-2">
                  {g.value.toFixed(2)} <span className="text-sm text-slate-500">{g.unit}</span>
                </div>
                <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, backgroundColor: g.color }} />
                </div>
              </div>
            )
          })}
        </div>

        {/* Waveform Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="bg-slate-900/80 border border-slate-800/50 rounded-xl p-4">
            <h3 className="text-sm font-semibold text-slate-400 mb-3">Vibration (Z & X RMS)</h3>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={waveform}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 8 }} />
                <Line type="monotone" dataKey="z_rms" stroke="#3b82f6" strokeWidth={2} dot={false} name="Z-RMS" />
                <Line type="monotone" dataKey="x_rms" stroke="#10b981" strokeWidth={2} dot={false} name="X-RMS" />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="bg-slate-900/80 border border-slate-800/50 rounded-xl p-4">
            <h3 className="text-sm font-semibold text-slate-400 mb-3">Temperature & Acceleration</h3>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={waveform}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 8 }} />
                <Line type="monotone" dataKey="temperature" stroke="#f59e0b" strokeWidth={2} dot={false} name="Temp °C" />
                <Line type="monotone" dataKey="z_accel" stroke="#ef4444" strokeWidth={2} dot={false} name="Z-Accel G" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Raw Registers - Always show when data exists */}
        <div className="bg-slate-900/80 border border-slate-800/50 rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-slate-400">Raw Modbus Registers</h3>
            <div className="flex items-center gap-3">
              {(s as any)?.register_source && (
                <span className="text-xs bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded border border-blue-500/30">
                  Source: Addr {(s as any).register_source}
                </span>
              )}
              {(s as any)?.non_zero_registers !== undefined && (
                <span className={`text-xs px-2 py-0.5 rounded border ${
                  (s as any).non_zero_registers > 0
                    ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                    : 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
                }`}>
                  {(s as any).non_zero_registers} non-zero
                </span>
              )}
              {(s as any)?.float32_reg20_21 !== undefined && (s as any).float32_reg20_21 !== 0 && (
                <span className="text-xs bg-purple-500/20 text-purple-400 px-2 py-0.5 rounded border border-purple-500/30">
                  Float32[20:21] = {(s as any).float32_reg20_21}
                </span>
              )}
            </div>
          </div>
          {s?.raw_registers && s.raw_registers.length > 0 ? (
            <div className="grid grid-cols-4 md:grid-cols-8 lg:grid-cols-11 gap-2">
              {s.raw_registers.map((val: number, i: number) => (
                <div key={i} className={`rounded px-2 py-1 text-center ${
                  val !== 0 ? 'bg-cyan-900/40 border border-cyan-500/30' : 'bg-slate-800/80'
                }`}>
                  <div className="text-[9px] text-slate-500">R{i}</div>
                  <div className={`text-xs font-mono ${val !== 0 ? 'text-cyan-300 font-bold' : 'text-slate-600'}`}>{val}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-sm text-slate-500 text-center py-4">
              {isConnected ? 'Reading registers...' : 'Connect to a device to see register data'}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
