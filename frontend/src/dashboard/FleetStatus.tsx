import { useEffect, useState } from 'react'
import { wsClient, WebSocketData } from '../lib/websocket'
import { Train, Activity, Thermometer, Wifi, WifiOff } from 'lucide-react'

export default function FleetStatus() {
  const [data, setData] = useState<WebSocketData | null>(null)

  useEffect(() => {
    const unsubscribe = wsClient.subscribe((newData: WebSocketData) => setData(newData))
    return unsubscribe
  }, [])

  const isConnected = data?.connection_status?.connected ?? false
  const s = data?.sensor_data

  // Build fleet cards — coach 1 uses live data, others show placeholder
  const coaches = Array.from({ length: 12 }, (_, i) => {
    const isLive = i === 0
    const zRms = isLive ? (s?.z_rms ?? 0) : 0
    const temp = isLive ? (s?.temperature ?? 0) : 0
    const status = isLive
      ? (isConnected ? (zRms > 4.5 ? 'critical' : zRms > 2.8 ? 'warning' : 'healthy') : 'offline')
      : 'offline'

    return {
      id: `COACH-${1001 + i}`,
      status,
      zRms,
      temp,
      isLive,
    }
  })

  const statusColors: Record<string, string> = {
    healthy: 'border-emerald-500/50 bg-emerald-500/5',
    warning: 'border-amber-500/50 bg-amber-500/5',
    critical: 'border-red-500/50 bg-red-500/5',
    offline: 'border-slate-700/50 bg-slate-800/30',
  }
  const statusText: Record<string, string> = {
    healthy: 'text-emerald-400',
    warning: 'text-amber-400',
    critical: 'text-red-400',
    offline: 'text-slate-500',
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-6">
      <div className="max-w-[1920px] mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-sky-400 to-blue-400 bg-clip-text text-transparent">
              Fleet Status
            </h1>
            <p className="text-slate-500 text-sm mt-1">All coach monitoring at a glance</p>
          </div>
          <div className="flex gap-3 text-xs font-semibold">
            <span className="flex items-center gap-1 text-emerald-400"><span className="w-2 h-2 rounded-full bg-emerald-400" /> Healthy</span>
            <span className="flex items-center gap-1 text-amber-400"><span className="w-2 h-2 rounded-full bg-amber-400" /> Warning</span>
            <span className="flex items-center gap-1 text-red-400"><span className="w-2 h-2 rounded-full bg-red-400" /> Critical</span>
            <span className="flex items-center gap-1 text-slate-500"><span className="w-2 h-2 rounded-full bg-slate-500" /> Offline</span>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {coaches.map(c => (
            <div key={c.id} className={`rounded-xl border p-4 transition-all ${statusColors[c.status]}`}>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Train className="w-5 h-5 text-slate-400" />
                  <span className="text-sm font-bold text-white">{c.id}</span>
                </div>
                {c.isLive && isConnected ? (
                  <Wifi className="w-4 h-4 text-emerald-400" />
                ) : (
                  <WifiOff className="w-4 h-4 text-slate-600" />
                )}
              </div>
              <div className={`text-xs font-bold uppercase mb-3 ${statusText[c.status]}`}>
                {c.status}
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-slate-950/50 rounded px-2 py-1">
                  <div className="text-[9px] text-slate-500 flex items-center gap-1"><Activity className="w-3 h-3" /> Vibration</div>
                  <div className="text-xs font-bold text-cyan-400">{c.zRms.toFixed(2)} mm/s</div>
                </div>
                <div className="bg-slate-950/50 rounded px-2 py-1">
                  <div className="text-[9px] text-slate-500 flex items-center gap-1"><Thermometer className="w-3 h-3" /> Temp</div>
                  <div className="text-xs font-bold text-orange-400">{c.temp.toFixed(1)}°C</div>
                </div>
              </div>
              {c.isLive && (
                <div className="mt-2 text-[10px] text-cyan-400/70 font-semibold">● LIVE SENSOR DATA</div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
