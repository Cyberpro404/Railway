import { useEffect, useState } from 'react'
import { wsClient, WebSocketData } from '../lib/websocket'
import { Save, RotateCcw, Settings, Sliders, AlertTriangle, CheckCircle2 } from 'lucide-react'

interface Threshold {
  parameter: string
  unit: string
  current: number
  warning: number
  critical: number
  description: string
}

export default function ThresholdsTab() {
  const [data, setData] = useState<WebSocketData | null>(null)
  const [thresholds, setThresholds] = useState<Threshold[]>([
    { parameter: 'Z-Axis RMS', unit: 'mm/s', current: 2.5, warning: 3.0, critical: 4.0, description: 'Z-Axis vibration velocity' },
    { parameter: 'X-Axis RMS', unit: 'mm/s', current: 2.2, warning: 2.8, critical: 3.8, description: 'X-Axis vibration velocity' },
    { parameter: 'Temperature', unit: '°C', current: 35, warning: 40, critical: 50, description: 'System temperature' },
    { parameter: 'Z-Peak Accel', unit: 'G', current: 1.2, warning: 2.0, critical: 3.0, description: 'Z-Axis peak acceleration' },
    { parameter: 'X-Peak Accel', unit: 'G', current: 1.1, warning: 2.0, critical: 3.0, description: 'X-Axis peak acceleration' },
    { parameter: 'Kurtosis', unit: '', current: 3.5, warning: 5.0, critical: 7.0, description: 'Signal impulsiveness' },
  ])
  const [editingParam, setEditingParam] = useState<string | null>(null)
  const [saveMessage, setSaveMessage] = useState('')

  useEffect(() => {
    const handleData = (newData: WebSocketData) => {
      setData(newData)
      // Update current values from real data
      setThresholds(prev => prev.map(t => {
        if (t.parameter === 'Z-Axis RMS') return { ...t, current: newData.sensor_data.z_rms }
        if (t.parameter === 'X-Axis RMS') return { ...t, current: newData.sensor_data.x_rms }
        if (t.parameter === 'Temperature') return { ...t, current: newData.sensor_data.temperature }
        if (t.parameter === 'Z-Peak Accel') return { ...t, current: newData.sensor_data.z_accel }
        if (t.parameter === 'X-Peak Accel') return { ...t, current: newData.sensor_data.x_accel }
        if (t.parameter === 'Kurtosis') return { ...t, current: newData.sensor_data.kurtosis }
        return t
      }))
    }

    const unsubscribe = wsClient.subscribe(handleData)
    return unsubscribe
  }, [])

  const updateThreshold = (param: string, field: 'warning' | 'critical', value: number) => {
    setThresholds(prev => prev.map(t =>
      t.parameter === param ? { ...t, [field]: value } : t
    ))
  }

  const saveThresholds = () => {
    setSaveMessage('✓ Thresholds saved successfully')
    setTimeout(() => setSaveMessage(''), 3000)
  }

  const resetDefaults = () => {
    setThresholds([
      { parameter: 'Z-Axis RMS', unit: 'mm/s', current: 2.5, warning: 3.0, critical: 4.0, description: 'Z-Axis vibration velocity' },
      { parameter: 'X-Axis RMS', unit: 'mm/s', current: 2.2, warning: 2.8, critical: 3.8, description: 'X-Axis vibration velocity' },
      { parameter: 'Temperature', unit: '°C', current: 35, warning: 40, critical: 50, description: 'System temperature' },
      { parameter: 'Z-Peak Accel', unit: 'G', current: 1.2, warning: 2.0, critical: 3.0, description: 'Z-Axis peak acceleration' },
      { parameter: 'X-Peak Accel', unit: 'G', current: 1.1, warning: 2.0, critical: 3.0, description: 'X-Axis peak acceleration' },
      { parameter: 'Kurtosis', unit: '', current: 3.5, warning: 5.0, critical: 7.0, description: 'Signal impulsiveness' },
    ])
    setSaveMessage('✓ Reset to defaults')
    setTimeout(() => setSaveMessage(''), 3000)
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
        <div className="text-center">
          <div className="w-20 h-20 mx-auto mb-6 relative">
            <div className="absolute inset-0 border-4 border-blue-500/30 rounded-full"></div>
            <div className="absolute inset-0 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
          <h2 className="text-2xl font-bold text-blue-400">Loading Settings...</h2>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-6">
      <div className="max-w-[1920px] mx-auto space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
              Threshold Configuration
            </h1>
            <p className="text-slate-500 text-sm mt-1">Manage alert thresholds and system parameters</p>
          </div>
          {saveMessage && (
            <div className="px-4 py-2 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-sm font-semibold">
              {saveMessage}
            </div>
          )}
        </div>

        {/* Threshold Cards */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {thresholds.map((threshold) => {
            const status = threshold.current >= threshold.critical ? 'critical' :
              threshold.current >= threshold.warning ? 'warning' : 'normal'

            return (
              <div key={threshold.parameter} className="relative group">
                <div className="absolute inset-0 bg-gradient-to-br from-blue-500/20 to-cyan-500/20 rounded-2xl blur-xl group-hover:blur-2xl transition-all duration-300" />
                <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="text-lg font-bold text-slate-200">{threshold.parameter}</h3>
                      <p className="text-xs text-slate-500 mt-1">{threshold.description}</p>
                    </div>
                    <div className={`flex items-center gap-1 px-2 py-1 rounded ${status === 'critical' ? 'bg-red-500/20 text-red-400' :
                      status === 'warning' ? 'bg-amber-500/20 text-amber-400' :
                        'bg-emerald-500/20 text-emerald-400'
                      }`}>
                      <div className={`w-2 h-2 rounded-full ${status === 'critical' ? 'bg-red-400' :
                        status === 'warning' ? 'bg-amber-400' :
                          'bg-emerald-400'
                        }`} />
                      <span className="text-xs font-semibold capitalize">{status}</span>
                    </div>
                  </div>

                  {/* Current Value */}
                  <div className="mb-6 p-4 bg-slate-800/50 rounded-lg border border-slate-800/50">
                    <p className="text-xs text-slate-500 uppercase font-semibold mb-2">Current Value</p>
                    <div className="flex items-baseline gap-2">
                      <span className="text-3xl font-bold text-cyan-400">{threshold.current.toFixed(2)}</span>
                      <span className="text-slate-500">{threshold.unit}</span>
                    </div>
                    <div className="mt-3 h-2 bg-slate-900 rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all ${status === 'critical' ? 'bg-red-500' :
                          status === 'warning' ? 'bg-amber-500' :
                            'bg-emerald-500'
                          }`}
                        style={{ width: `${Math.min(100, (threshold.current / threshold.critical) * 100)}%` }}
                      />
                    </div>
                  </div>

                  {/* Warning & Critical Thresholds */}
                  <div className="space-y-4">
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <label className="text-sm text-slate-400 font-semibold">⚠️ Warning Threshold</label>
                        <span className="text-sm font-bold text-amber-400">{threshold.warning.toFixed(2)} {threshold.unit}</span>
                      </div>
                      <input
                        type="range"
                        min={threshold.current}
                        max={threshold.critical * 2}
                        step="0.1"
                        value={threshold.warning}
                        onChange={(e) => updateThreshold(threshold.parameter, 'warning', parseFloat(e.target.value))}
                        className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer"
                      />
                    </div>

                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <label className="text-sm text-slate-400 font-semibold">🔴 Critical Threshold</label>
                        <span className="text-sm font-bold text-red-400">{threshold.critical.toFixed(2)} {threshold.unit}</span>
                      </div>
                      <input
                        type="range"
                        min={threshold.warning}
                        max={threshold.critical * 2}
                        step="0.1"
                        value={threshold.critical}
                        onChange={(e) => updateThreshold(threshold.parameter, 'critical', parseFloat(e.target.value))}
                        className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer"
                      />
                    </div>
                  </div>

                  {/* Status Indicator */}
                  <div className="mt-6 pt-6 border-t border-slate-800/50 flex items-center gap-2">
                    {status === 'normal' ? (
                      <>
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        <span className="text-xs text-emerald-400 font-semibold">Normal Operation</span>
                      </>
                    ) : status === 'warning' ? (
                      <>
                        <AlertTriangle className="w-4 h-4 text-amber-400" />
                        <span className="text-xs text-amber-400 font-semibold">Monitor Closely</span>
                      </>
                    ) : (
                      <>
                        <AlertTriangle className="w-4 h-4 text-red-400" />
                        <span className="text-xs text-red-400 font-semibold">Action Required</span>
                      </>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* Threshold Summary */}
        <div className="relative group">
          <div className="absolute inset-0 bg-gradient-to-br from-purple-500/20 to-pink-500/20 rounded-2xl blur-xl group-hover:blur-2xl transition-all duration-300" />
          <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
            <h2 className="text-xl font-bold text-slate-200 mb-6">Threshold Summary</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center p-4 bg-slate-800/30 rounded-lg">
                <p className="text-xs text-slate-500 uppercase font-semibold mb-2">Normal Range</p>
                <p className="text-2xl font-bold text-emerald-400">{thresholds.filter(t => t.current < t.warning).length}</p>
                <p className="text-xs text-slate-500 mt-1">Parameters</p>
              </div>
              <div className="text-center p-4 bg-slate-800/30 rounded-lg">
                <p className="text-xs text-slate-500 uppercase font-semibold mb-2">Warning Range</p>
                <p className="text-2xl font-bold text-amber-400">{thresholds.filter(t => t.current >= t.warning && t.current < t.critical).length}</p>
                <p className="text-xs text-slate-500 mt-1">Parameters</p>
              </div>
              <div className="text-center p-4 bg-slate-800/30 rounded-lg">
                <p className="text-xs text-slate-500 uppercase font-semibold mb-2">Critical Range</p>
                <p className="text-2xl font-bold text-red-400">{thresholds.filter(t => t.current >= t.critical).length}</p>
                <p className="text-xs text-slate-500 mt-1">Parameters</p>
              </div>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-3">
          <button
            onClick={saveThresholds}
            className="px-6 py-3 bg-gradient-to-r from-cyan-500 to-blue-500 text-white rounded-lg font-semibold hover:shadow-lg hover:shadow-cyan-500/50 transition-all flex items-center"
          >
            <Save className="w-5 h-5 mr-2" />
            Save Thresholds
          </button>
          <button
            onClick={resetDefaults}
            className="px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg font-semibold hover:shadow-lg hover:shadow-purple-500/50 transition-all flex items-center"
          >
            <RotateCcw className="w-5 h-5 mr-2" />
            Reset to Defaults
          </button>
          <button className="px-6 py-3 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg font-semibold hover:bg-slate-700 transition-all flex items-center">
            <Sliders className="w-5 h-5 mr-2" />
            Advanced Settings
          </button>
          <button className="px-6 py-3 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg font-semibold hover:bg-slate-700 transition-all flex items-center">
            <Settings className="w-5 h-5 mr-2" />
            Export Config
          </button>
        </div>
      </div>
    </div>
  )
}
