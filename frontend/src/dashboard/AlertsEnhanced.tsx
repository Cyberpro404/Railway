import { useEffect, useState } from 'react'
import { Bell, AlertTriangle, AlertCircle, Trash2, RefreshCw } from 'lucide-react'

interface Alert {
  timestamp: string
  parameter: string
  parameterLabel: string
  current_value: number
  threshold_limit: number
  alert_type: string
  severity: string
}

export default function AlertsEnhanced() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(true)

  const fetchAlerts = async () => {
    try {
      setLoading(true)
      const response = await fetch('http://localhost:8000/api/v1/alerts/active')
      if (response.ok) {
        const data = await response.json()
        setAlerts(data.alerts || [])
      }
    } catch (error) {
      console.error('Error fetching alerts:', error)
    } finally {
      setLoading(false)
    }
  }

  const clearAllAlerts = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/alerts/clear', {
        method: 'POST'
      })
      if (response.ok) {
        setAlerts([])
      }
    } catch (error) {
      console.error('Error clearing alerts:', error)
    }
  }

  useEffect(() => {
    fetchAlerts()

    // Auto-refresh alerts every 2 seconds if enabled
    let interval: ReturnType<typeof setInterval>
    if (autoRefresh) {
      interval = setInterval(() => {
        fetchAlerts()
      }, 2000)
    }

    return () => {
      if (interval) clearInterval(interval)
    }
  }, [autoRefresh])

  const criticalAlerts = alerts.filter(a => a.severity === 'critical')
  const warningAlerts = alerts.filter(a => a.severity === 'warning')

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-red-500/20 rounded-lg">
              <Bell className="w-6 h-6 text-red-400" />
            </div>
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-red-400 to-orange-400 bg-clip-text text-transparent">
                Alert Dashboard
              </h1>
              <p className="text-slate-500 text-sm mt-1">Real-time monitoring of threshold breaches</p>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={fetchAlerts}
              disabled={loading}
              className="px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg hover:bg-slate-700 transition-all flex items-center gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`px-4 py-2 border rounded-lg transition-all flex items-center gap-2 ${
                autoRefresh
                  ? 'bg-blue-500/20 border-blue-500/50 text-blue-400'
                  : 'bg-slate-800 border-slate-700 text-slate-300'
              }`}
            >
              <div className={`w-2 h-2 rounded-full ${autoRefresh ? 'bg-blue-400' : 'bg-slate-500'}`} />
              {autoRefresh ? 'Auto-Refresh ON' : 'Auto-Refresh OFF'}
            </button>
          </div>
        </div>

        {/* Alert Summary */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="relative group">
            <div className="absolute inset-0 bg-gradient-to-br from-red-500/20 to-orange-500/20 rounded-xl blur-xl group-hover:blur-2xl transition-all duration-300" />
            <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-xl p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-slate-500 text-sm uppercase font-semibold">Critical Alerts</p>
                  <p className="text-3xl font-bold text-red-400 mt-2">{criticalAlerts.length}</p>
                </div>
                <AlertTriangle className="w-8 h-8 text-red-400/50" />
              </div>
            </div>
          </div>

          <div className="relative group">
            <div className="absolute inset-0 bg-gradient-to-br from-amber-500/20 to-yellow-500/20 rounded-xl blur-xl group-hover:blur-2xl transition-all duration-300" />
            <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-xl p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-slate-500 text-sm uppercase font-semibold">Warning Alerts</p>
                  <p className="text-3xl font-bold text-amber-400 mt-2">{warningAlerts.length}</p>
                </div>
                <AlertCircle className="w-8 h-8 text-amber-400/50" />
              </div>
            </div>
          </div>

          <div className="relative group">
            <div className="absolute inset-0 bg-gradient-to-br from-blue-500/20 to-cyan-500/20 rounded-xl blur-xl group-hover:blur-2xl transition-all duration-300" />
            <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-xl p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-slate-500 text-sm uppercase font-semibold">Total Alerts</p>
                  <p className="text-3xl font-bold text-cyan-400 mt-2">{alerts.length}</p>
                </div>
                <Bell className="w-8 h-8 text-cyan-400/50" />
              </div>
            </div>
          </div>
        </div>

        {/* Alerts List */}
        <div className="space-y-3">
          {alerts.length === 0 ? (
            <div className="relative group">
              <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/20 to-teal-500/20 rounded-xl blur-xl group-hover:blur-2xl transition-all duration-300" />
              <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-xl p-12 text-center">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-emerald-500/20 flex items-center justify-center">
                  <Bell className="w-8 h-8 text-emerald-400" />
                </div>
                <p className="text-slate-300 font-semibold">No Active Alerts</p>
                <p className="text-slate-500 text-sm mt-1">All parameters are within normal limits</p>
              </div>
            </div>
          ) : (
            alerts.map((alert, idx) => (
              <div key={idx} className="relative group">
                <div className={`absolute inset-0 bg-gradient-to-br ${
                  alert.severity === 'critical'
                    ? 'from-red-500/20 to-orange-500/20'
                    : 'from-amber-500/20 to-yellow-500/20'
                } rounded-xl blur-xl group-hover:blur-2xl transition-all duration-300`} />
                <div className={`relative bg-slate-900/90 backdrop-blur-xl border rounded-xl p-4 ${
                  alert.severity === 'critical'
                    ? 'border-red-500/30'
                    : 'border-amber-500/30'
                }`}>
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-4 flex-1">
                      <div className={`mt-1 p-2 rounded-lg ${
                        alert.severity === 'critical'
                          ? 'bg-red-500/20'
                          : 'bg-amber-500/20'
                      }`}>
                        {alert.severity === 'critical' ? (
                          <AlertTriangle className={`w-5 h-5 ${alert.severity === 'critical' ? 'text-red-400' : 'text-amber-400'}`} />
                        ) : (
                          <AlertCircle className={`w-5 h-5 ${alert.severity === 'critical' ? 'text-red-400' : 'text-amber-400'}`} />
                        )}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-3">
                          <h3 className="text-lg font-bold text-slate-200">{alert.parameterLabel}</h3>
                          <span className={`px-2 py-1 rounded text-xs font-semibold ${
                            alert.severity === 'critical'
                              ? 'bg-red-500/20 text-red-400'
                              : 'bg-amber-500/20 text-amber-400'
                          }`}>
                            {alert.severity.toUpperCase()}
                          </span>
                        </div>
                        <div className="mt-2 grid grid-cols-3 gap-4">
                          <div>
                            <p className="text-xs text-slate-500 uppercase">Current Value</p>
                            <p className="text-xl font-bold text-cyan-400">{alert.current_value.toFixed(2)}</p>
                          </div>
                          <div>
                            <p className="text-xs text-slate-500 uppercase">Threshold</p>
                            <p className="text-xl font-bold text-orange-400">{alert.threshold_limit.toFixed(2)}</p>
                          </div>
                          <div>
                            <p className="text-xs text-slate-500 uppercase">Time</p>
                            <p className="text-sm text-slate-400">
                              {new Date(alert.timestamp).toLocaleTimeString()}
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className={`px-3 py-1 rounded text-xs font-semibold ${
                      alert.alert_type === 'max_exceeded'
                        ? 'bg-red-500/20 text-red-400'
                        : 'bg-blue-500/20 text-blue-400'
                    }`}>
                      {alert.alert_type === 'max_exceeded' ? '↑ Over' : '↓ Under'}
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Clear Button */}
        {alerts.length > 0 && (
          <button
            onClick={clearAllAlerts}
            className="w-full px-6 py-3 bg-red-500/20 border border-red-500/50 text-red-400 rounded-lg hover:bg-red-500/30 transition-all flex items-center justify-center gap-2 font-semibold"
          >
            <Trash2 className="w-5 h-5" />
            Clear All Alerts
          </button>
        )}
      </div>
    </div>
  )
}
