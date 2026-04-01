import { useEffect, useState } from 'react'
import { wsClient, WebSocketData } from '../lib/websocket'
import { Server, Wifi, WifiOff, Activity, Clock, Database, Cpu, HardDrive } from 'lucide-react'

export default function SystemStatus() {
  const [data, setData] = useState<WebSocketData | null>(null)
  const [uptime, setUptime] = useState(0)
  const [packetCount, setPacketCount] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => setUptime(prev => prev + 1), 1000)
    const unsubscribe = wsClient.subscribe((newData: WebSocketData) => {
      setData(newData)
      setPacketCount(prev => prev + 1)
    })
    return () => { clearInterval(timer); unsubscribe() }
  }, [])

  const cs = data?.connection_status
  const isConnected = cs?.connected ?? false

  const formatUptime = (seconds: number) => {
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    const s = seconds % 60
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }

  const items = [
    { label: 'Device Connection', value: isConnected ? 'Connected' : 'Disconnected', color: isConnected ? 'text-emerald-400' : 'text-red-400', icon: isConnected ? Wifi : WifiOff },
    { label: 'Port / Host', value: cs?.port || 'N/A', color: 'text-cyan-400', icon: Server },
    { label: 'Baud Rate', value: cs?.baud?.toString() ?? 'N/A', color: 'text-blue-400', icon: Activity },
    { label: 'Slave ID', value: cs?.slave_id?.toString() ?? 'N/A', color: 'text-purple-400', icon: Cpu },
    { label: 'Device Uptime', value: cs?.uptime_seconds ? formatUptime(cs.uptime_seconds) : 'N/A', color: 'text-amber-400', icon: Clock },
    { label: 'Last Poll', value: cs?.last_poll ?? 'N/A', color: 'text-slate-300', icon: Clock },
    { label: 'Packet Loss', value: `${(cs?.packet_loss ?? 0).toFixed(1)}%`, color: cs && cs.packet_loss > 5 ? 'text-red-400' : 'text-emerald-400', icon: Database },
    { label: 'Auto Reconnect', value: cs?.auto_reconnect ? 'Enabled' : 'Disabled', color: 'text-cyan-400', icon: Activity },
    { label: 'Frontend Uptime', value: formatUptime(uptime), color: 'text-sky-400', icon: Clock },
    { label: 'Packets Received', value: packetCount.toString(), color: 'text-teal-400', icon: HardDrive },
    { label: 'Data Source', value: data?.source ?? 'N/A', color: 'text-indigo-400', icon: Database },
    { label: 'ISO Class', value: data?.iso_severity?.class ?? 'N/A', color: 'text-orange-400', icon: Activity },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-6">
      <div className="max-w-[1920px] mx-auto space-y-6">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-green-400 to-emerald-400 bg-clip-text text-transparent">
            System Status
          </h1>
          <p className="text-slate-500 text-sm mt-1">Infrastructure health & connection diagnostics</p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {items.map(item => {
            const Icon = item.icon
            return (
              <div key={item.label} className="bg-slate-900/80 border border-slate-800/50 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Icon className="w-4 h-4 text-slate-500" />
                  <span className="text-xs text-slate-400 font-semibold uppercase">{item.label}</span>
                </div>
                <div className={`text-lg font-bold ${item.color} truncate`}>{item.value}</div>
              </div>
            )
          })}
        </div>

        {/* ML Model Status */}
        <div className="bg-slate-900/80 border border-slate-800/50 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-slate-400 mb-4">ML Engine Status</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-xs text-slate-500">Model</div>
              <div className="text-sm font-bold text-purple-400">{data?.ml_prediction ? 'Loaded' : 'Not Loaded'}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500">Current Prediction</div>
              <div className="text-sm font-bold text-white">{data?.ml_prediction?.class_name ?? 'N/A'}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500">Confidence</div>
              <div className="text-sm font-bold text-cyan-400">{data?.ml_prediction ? `${(data.ml_prediction.confidence * 100).toFixed(1)}%` : 'N/A'}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500">ISO Severity</div>
              <div className="text-sm font-bold text-amber-400">{data?.iso_severity?.level ?? 'N/A'}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
