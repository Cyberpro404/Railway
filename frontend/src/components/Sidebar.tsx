import { NavLink, useLocation } from 'react-router-dom'
import {
  Wifi,
  TrendingUp,
  Brain,
  AlertTriangle,
  Settings,
  Activity,
  Zap,
  FileText
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useEffect, useState } from 'react'
import { wsClient, WebSocketData } from '@/lib/websocket'

const tabs = [
  { path: '/', label: 'Overview', icon: Activity, color: 'text-cyan-400', description: 'Real-time system overview' },
  { path: '/analytics', label: 'Analytics', icon: TrendingUp, color: 'text-emerald-400', description: 'Advanced analytics & insights' },
  { path: '/ml', label: 'Intelligence', icon: Brain, color: 'text-purple-400', description: 'AI predictions & anomaly detection' },
  { path: '/alerts', label: 'Alerts', icon: AlertTriangle, color: 'text-amber-400', description: 'Active alerts & notifications' },
  { path: '/connection', label: 'Connection', icon: Wifi, color: 'text-blue-400', description: 'Device connection management' },
  { path: '/settings', label: 'Settings', icon: Settings, color: 'text-slate-400', description: 'System configuration' },
  { path: '/logs', label: 'Logs', icon: FileText, color: 'text-indigo-400', description: 'System logs & diagnostics' },
]

export default function Sidebar() {
  const [connectionStatus, setConnectionStatus] = useState(false)
  const [hasAlerts, setHasAlerts] = useState(false)
  const [sensorData, setSensorData] = useState<any>(null)
  const location = useLocation()

  useEffect(() => {
    const unsubscribe = wsClient.subscribe((data: WebSocketData) => {
      setConnectionStatus(data.connection_status?.connected || false)
      setSensorData(data.sensor_data)
      if (data.ml_prediction?.class === 1 && data.ml_prediction.confidence > 0.3) {
        setHasAlerts(true)
      }
    })
    return unsubscribe
  }, [])

  return (
    <aside className="w-64 bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 border-r border-slate-800/50 flex flex-col shadow-2xl relative overflow-hidden">
      {/* Animated background gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 via-transparent to-purple-500/5 pointer-events-none" />
      <div className="absolute top-0 right-0 w-64 h-64 bg-cyan-500/10 rounded-full blur-3xl" />
      <div className="absolute bottom-0 left-0 w-64 h-64 bg-purple-500/10 rounded-full blur-3xl" />

      {/* Header */}
      <div className="p-6 border-b border-slate-800/50 relative z-10">
        <div className="flex items-center gap-3 mb-3">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 shadow-lg shadow-cyan-500/30">
            <Zap className="w-5 h-5 text-white" />
            <div className="absolute inset-0 rounded-xl bg-cyan-400/20 animate-pulse" />
          </div>
          <div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
              Gandiva Pro
            </h1>
            <p className="text-[10px] text-slate-400 font-medium">Railway Monitoring</p>
          </div>
        </div>

        {/* Live Status Card */}
        <div className="mt-4 p-3 rounded-lg bg-slate-900/50 backdrop-blur-sm border border-slate-800/50">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-400">System Status</span>
            <div className={cn(
              "flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold",
              connectionStatus 
                ? "bg-emerald-500/20 text-emerald-400" 
                : "bg-slate-700/50 text-slate-400"
            )}>
              <div className={cn(
                "w-1.5 h-1.5 rounded-full",
                connectionStatus ? "bg-emerald-400" : "bg-slate-500"
              )}>
                {connectionStatus && (
                  <div className="absolute w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                )}
              </div>
              {connectionStatus ? 'ONLINE' : 'OFFLINE'}
            </div>
          </div>
          
          {sensorData && (
            <div className="grid grid-cols-2 gap-2 mt-2">
              <div className="bg-slate-950/50 rounded px-2 py-1.5">
                <div className="text-[9px] text-slate-500 uppercase font-semibold">Vibration</div>
                <div className="text-xs font-bold text-cyan-400">{sensorData.z_rms?.toFixed(2)} mm/s</div>
              </div>
              <div className="bg-slate-950/50 rounded px-2 py-1.5">
                <div className="text-[9px] text-slate-500 uppercase font-semibold">Temp</div>
                <div className="text-xs font-bold text-emerald-400">{sensorData.temperature?.toFixed(1)}°C</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto relative z-10">
        {tabs.map((tab, index) => {
          const Icon = tab.icon
          const isAlertTab = tab.path === '/alerts'
          const isActive = location.pathname === tab.path

          return (
            <NavLink
              key={tab.path}
              to={tab.path}
              className={({ isActive: active }) =>
                cn(
                  "group flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200",
                  "relative overflow-hidden",
                  active
                    ? "bg-gradient-to-r from-cyan-500/20 to-blue-500/10 text-cyan-400 shadow-lg shadow-cyan-500/10"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
                )
              }
            >
              {/* Active indicator */}
              {isActive && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-gradient-to-b from-cyan-400 to-blue-500 rounded-r-full" />
              )}

              <div className={cn(
                "flex items-center justify-center w-8 h-8 rounded-lg transition-all duration-200",
                isActive 
                  ? "bg-cyan-500/10 shadow-lg shadow-cyan-500/20" 
                  : "bg-slate-800/30 group-hover:bg-slate-800/50"
              )}>
                <Icon className={cn(
                  "w-4 h-4 transition-all duration-200",
                  tab.color,
                  isActive && "scale-110"
                )} />
              </div>

              <div className="flex-1">
                <div className="text-sm font-semibold">
                  {tab.label}
                </div>
                {!isActive && (
                  <div className="text-[10px] text-slate-500 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                    {tab.description}
                  </div>
                )}
              </div>

              {/* Alert badge */}
              {isAlertTab && hasAlerts && (
                <div className="relative">
                  <div className="w-2 h-2 rounded-full bg-amber-400" />
                  <div className="absolute inset-0 w-2 h-2 rounded-full bg-amber-400 animate-ping opacity-75" />
                </div>
              )}

              {/* Hover effect */}
              <div className={cn(
                "absolute inset-0 bg-gradient-to-r from-transparent via-cyan-500/5 to-transparent",
                "opacity-0 group-hover:opacity-100 transition-opacity duration-300",
                "-skew-x-12"
              )} />
            </NavLink>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-slate-800/50 relative z-10">
        <div className="text-[10px] text-slate-500 text-center">
          <div className="font-semibold">v4.0.0</div>
          <div className="text-slate-600 mt-0.5">© 2026 Gandiva Pro</div>
        </div>
      </div>
    </aside>
  )
}
