import { useEffect, useState } from 'react'
import { wsClient, WebSocketData } from '../lib/websocket'
import { Save, RotateCcw, Plus, Trash2 } from 'lucide-react'
import { thresholdsAPI, controllerThresholdsAPI, ThresholdConfig, ControllerThresholdConfig } from '../lib/api'

const PARAMETER_OPTIONS = [
  { value: 'z_rms', label: 'Z-Axis RMS', unit: 'mm/s' },
  { value: 'x_rms', label: 'X-Axis RMS', unit: 'mm/s' },
  { value: 'temperature', label: 'Temperature', unit: '°C' },
  { value: 'z_accel', label: 'Z-Peak Accel', unit: 'G' },
  { value: 'x_accel', label: 'X-Peak Accel', unit: 'G' },
  { value: 'kurtosis', label: 'Kurtosis', unit: '' },
]

const DEFAULT_CONTROLLER_THRESHOLDS: ControllerThresholdConfig[] = [
  {
    id: 'ctrl-1',
    parameter: 'z_rms',
    parameterLabel: 'Z-Axis RMS',
    unit: 'mm/s',
    warningLimit: 2,
    alertLimit: 4,
  },
  {
    id: 'ctrl-2',
    parameter: 'x_rms',
    parameterLabel: 'X-Axis RMS',
    unit: 'mm/s',
    warningLimit: 2,
    alertLimit: 4,
  },
  {
    id: 'ctrl-3',
    parameter: 'temperature',
    parameterLabel: 'Temperature',
    unit: '°C',
    warningLimit: 2,
    alertLimit: 4,
  },
  {
    id: 'ctrl-4',
    parameter: 'z_accel',
    parameterLabel: 'Z-Peak Accel',
    unit: 'G',
    warningLimit: 2,
    alertLimit: 4,
  },
  {
    id: 'ctrl-5',
    parameter: 'x_accel',
    parameterLabel: 'X-Peak Accel',
    unit: 'G',
    warningLimit: 2,
    alertLimit: 4,
  },
  {
    id: 'ctrl-6',
    parameter: 'kurtosis',
    parameterLabel: 'Kurtosis',
    unit: '',
    warningLimit: 2,
    alertLimit: 4,
  },
]

const DEFAULT_THRESHOLDS: ThresholdConfig[] = [
  {
    id: '1',
    parameter: 'z_rms',
    parameterLabel: 'Z-Axis RMS',
    unit: 'mm/s',
    minLimit: -999,
    maxLimit: 4.0,
  },
  {
    id: '2',
    parameter: 'temperature',
    parameterLabel: 'Temperature',
    unit: '°C',
    minLimit: -999,
    maxLimit: 50,
  },
]

export default function ThresholdsSimple() {
  const [data, setData] = useState<WebSocketData | null>(null)
  const [thresholds, setThresholds] = useState<ThresholdConfig[]>(DEFAULT_THRESHOLDS)
  const [saveMessage, setSaveMessage] = useState('')
  const [controllerThresholds, setControllerThresholds] = useState<ControllerThresholdConfig[]>(DEFAULT_CONTROLLER_THRESHOLDS)
  const [controllerSaveMessage, setControllerSaveMessage] = useState('')

  const getSensorValue = (param: ControllerThresholdConfig['parameter']) => {
    if (!data) return 0
    if (param === 'z_rms') return data.sensor_data.z_rms
    if (param === 'x_rms') return data.sensor_data.x_rms
    if (param === 'temperature') return data.sensor_data.temperature
    if (param === 'z_accel') return data.sensor_data.z_accel
    if (param === 'x_accel') return data.sensor_data.x_accel
    if (param === 'kurtosis') return data.sensor_data.kurtosis
    return 0
  }

  const fetchThresholds = async () => {
    try {
      const payload = await thresholdsAPI.getAll()
      setThresholds(payload.length ? payload : DEFAULT_THRESHOLDS)
    } catch (error) {
      console.error('Error fetching thresholds:', error)
      setThresholds(DEFAULT_THRESHOLDS)
    }
  }

  const fetchControllerThresholds = async () => {
    try {
      const payload = await controllerThresholdsAPI.getAll()
      setControllerThresholds(payload.length ? payload : DEFAULT_CONTROLLER_THRESHOLDS)
    } catch (error) {
      console.error('Error fetching controller thresholds:', error)
      setControllerThresholds(DEFAULT_CONTROLLER_THRESHOLDS)
    }
  }

  useEffect(() => {
    const handleData = (newData: WebSocketData) => {
      setData(newData)
    }

    const unsubscribe = wsClient.subscribe(handleData)
    fetchThresholds()
    fetchControllerThresholds()
    return unsubscribe
  }, [])

  const addThreshold = () => {
    const newId = Date.now().toString()
    setThresholds([
      ...thresholds,
      {
        id: newId,
        parameter: 'z_rms',
        parameterLabel: 'Z-Axis RMS',
        unit: 'mm/s',
        minLimit: -999,
        maxLimit: 5.0,
      },
    ])
  }

  const updateThreshold = (id: string, field: string, value: any) => {
    setThresholds(thresholds.map(t => {
      if (t.id === id) {
        if (field === 'parameter') {
          const selected = PARAMETER_OPTIONS.find(p => p.value === value)
          return {
            ...t,
            parameter: value,
            parameterLabel: selected?.label || value,
            unit: selected?.unit || '',
          }
        }
        return { ...t, [field]: value }
      }
      return t
    }))
  }

  const deleteThreshold = (id: string) => {
    setThresholds(thresholds.filter(t => t.id !== id))
  }

  const saveThresholds = async () => {
    try {
      const response = await thresholdsAPI.saveAll(thresholds)
      if (response?.success) {
        setSaveMessage('✅ Thresholds saved successfully!')
      } else {
        setSaveMessage('❌ Failed to save thresholds')
      }
    } catch (error) {
      setSaveMessage('❌ Error saving thresholds')
    } finally {
      setTimeout(() => setSaveMessage(''), 3000)
    }
  }

  const resetDefaults = () => {
    setThresholds([
      {
        id: '1',
        parameter: 'z_rms',
        parameterLabel: 'Z-Axis RMS',
        unit: 'mm/s',
        minLimit: -999,
        maxLimit: 4.0,
      },
      {
        id: '2',
        parameter: 'temperature',
        parameterLabel: 'Temperature',
        unit: '°C',
        minLimit: -999,
        maxLimit: 50,
      },
    ])
    setSaveMessage('✅ Reset to defaults')
    setTimeout(() => setSaveMessage(''), 3000)
  }

  const updateControllerThreshold = (id: string, field: keyof ControllerThresholdConfig, value: number) => {
    setControllerThresholds(prev => prev.map(t => (t.id === id ? { ...t, [field]: value } : t)))
  }

  const saveControllerThresholds = async () => {
    try {
      const response = await controllerThresholdsAPI.saveAll(controllerThresholds)
      if (response?.success) {
        setControllerSaveMessage('✅ ESP32 thresholds saved')
      } else {
        setControllerSaveMessage('❌ Failed to save ESP32 thresholds')
      }
    } catch (error) {
      setControllerSaveMessage('❌ Error saving ESP32 thresholds')
    } finally {
      setTimeout(() => setControllerSaveMessage(''), 3000)
    }
  }

  const resetControllerThresholds = () => {
    setControllerThresholds(DEFAULT_CONTROLLER_THRESHOLDS)
    setControllerSaveMessage('✅ Reset ESP32 thresholds to defaults (2 warning / 4 alert)')
    setTimeout(() => setControllerSaveMessage(''), 3000)
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
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
              Threshold Configuration
            </h1>
            <p className="text-slate-500 text-sm mt-1">Set limits for each parameter. When crossed, alerts will trigger</p>
          </div>
          {saveMessage && (
            <div className="px-4 py-2 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-sm font-semibold">
              {saveMessage}
            </div>
          )}
        </div>

        {/* Threshold List */}
        <div className="space-y-4">
          {thresholds.map((threshold) => (
            <div key={threshold.id} className="relative group">
              <div className="absolute inset-0 bg-gradient-to-br from-blue-500/20 to-cyan-500/20 rounded-xl blur-xl group-hover:blur-2xl transition-all duration-300" />
              <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-xl p-6">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
                  {/* Parameter Selector */}
                  <div>
                    <label className="block text-sm font-semibold text-slate-400 mb-2">Select Parameter</label>
                    <select
                      value={threshold.parameter}
                      onChange={(e) => updateThreshold(threshold.id, 'parameter', e.target.value)}
                      className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                    >
                      {PARAMETER_OPTIONS.map(option => (
                        <option key={option.value} value={option.value}>
                          {option.label} ({option.unit})
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Min Limit */}
                  <div>
                    <label className="block text-sm font-semibold text-slate-400 mb-2">
                      Min Limit ({threshold.unit})
                    </label>
                    <input
                      type="number"
                      value={threshold.minLimit}
                      onChange={(e) => updateThreshold(threshold.id, 'minLimit', parseFloat(e.target.value))}
                      step="0.1"
                      className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                    />
                  </div>

                  {/* Max Limit */}
                  <div>
                    <label className="block text-sm font-semibold text-slate-400 mb-2">
                      Max Limit ({threshold.unit})
                    </label>
                    <input
                      type="number"
                      value={threshold.maxLimit}
                      onChange={(e) => updateThreshold(threshold.id, 'maxLimit', parseFloat(e.target.value))}
                      step="0.1"
                      className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                    />
                  </div>

                  {/* Delete Button */}
                  <div className="flex gap-2">
                    <button
                      onClick={() => deleteThreshold(threshold.id)}
                      className="px-4 py-2 bg-red-500/20 border border-red-500/50 text-red-400 rounded-lg hover:bg-red-500/30 transition-all flex items-center justify-center"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Current Value Display */}
                <div className="mt-4 pt-4 border-t border-slate-800/50">
                  <p className="text-xs text-slate-500 uppercase font-semibold mb-2">Current Value</p>
                  <div className="flex items-baseline gap-2">
                    {threshold.parameter === 'z_rms' && (
                      <>
                        <span className="text-2xl font-bold text-cyan-400">
                          {data.sensor_data.z_rms.toFixed(2)}
                        </span>
                        <span className="text-slate-500 text-sm">mm/s</span>
                      </>
                    )}
                    {threshold.parameter === 'x_rms' && (
                      <>
                        <span className="text-2xl font-bold text-cyan-400">
                          {data.sensor_data.x_rms.toFixed(2)}
                        </span>
                        <span className="text-slate-500 text-sm">mm/s</span>
                      </>
                    )}
                    {threshold.parameter === 'temperature' && (
                      <>
                        <span className="text-2xl font-bold text-cyan-400">
                          {data.sensor_data.temperature.toFixed(1)}
                        </span>
                        <span className="text-slate-500 text-sm">°C</span>
                      </>
                    )}
                    {threshold.parameter === 'z_accel' && (
                      <>
                        <span className="text-2xl font-bold text-cyan-400">
                          {data.sensor_data.z_accel.toFixed(2)}
                        </span>
                        <span className="text-slate-500 text-sm">G</span>
                      </>
                    )}
                    {threshold.parameter === 'x_accel' && (
                      <>
                        <span className="text-2xl font-bold text-cyan-400">
                          {data.sensor_data.x_accel.toFixed(2)}
                        </span>
                        <span className="text-slate-500 text-sm">G</span>
                      </>
                    )}
                    {threshold.parameter === 'kurtosis' && (
                      <>
                        <span className="text-2xl font-bold text-cyan-400">
                          {data.sensor_data.kurtosis.toFixed(2)}
                        </span>
                        <span className="text-slate-500 text-sm">-</span>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* ESP32 Controller Thresholds */}
        <div className="relative group">
          <div className="absolute inset-0 bg-gradient-to-br from-amber-500/15 to-orange-500/15 rounded-xl blur-xl group-hover:blur-2xl transition-all duration-300" />
          <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-xl p-6 space-y-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-2xl font-bold text-slate-100">ESP32 Controller Thresholds</h2>
                <p className="text-slate-500 text-sm mt-1">Hardware-only limits: warning = 1 blink, alert = 2 blinks. Defaults are 2 (warning) and 4 (alert) for all parameters.</p>
              </div>
              {controllerSaveMessage && (
                <div className="px-4 py-2 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-sm font-semibold">
                  {controllerSaveMessage}
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {controllerThresholds.map((threshold) => (
                <div key={threshold.id} className="bg-slate-800/70 border border-slate-800/70 rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-slate-400 font-semibold">{threshold.parameterLabel}</p>
                      <p className="text-xs text-slate-500">Current: {getSensorValue(threshold.parameter).toFixed(2)} {threshold.unit}</p>
                    </div>
                    <span className="text-xs px-2 py-1 rounded bg-amber-500/10 text-amber-300">ESP32</span>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-amber-300 mb-1">Warning (1 blink)</label>
                    <input
                      type="number"
                      value={threshold.warningLimit}
                      step="0.1"
                      onChange={(e) => updateControllerThreshold(threshold.id, 'warningLimit', parseFloat(e.target.value))}
                      className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-slate-200 focus:outline-none focus:border-amber-400"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-orange-300 mb-1">Alert (2 blinks)</label>
                    <input
                      type="number"
                      value={threshold.alertLimit}
                      step="0.1"
                      onChange={(e) => updateControllerThreshold(threshold.id, 'alertLimit', parseFloat(e.target.value))}
                      className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-slate-200 focus:outline-none focus:border-orange-400"
                    />
                  </div>
                </div>
              ))}
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                onClick={saveControllerThresholds}
                className="px-6 py-3 bg-gradient-to-r from-orange-500 to-amber-500 text-white rounded-lg font-semibold hover:shadow-lg hover:shadow-orange-500/40 transition-all flex items-center"
              >
                <Save className="w-5 h-5 mr-2" />
                Save ESP32 Thresholds
              </button>
              <button
                onClick={resetControllerThresholds}
                className="px-6 py-3 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg font-semibold hover:bg-slate-700 transition-all flex items-center"
              >
                <RotateCcw className="w-5 h-5 mr-2" />
                Reset to 2 / 4 Defaults
              </button>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-3">
          <button
            onClick={addThreshold}
            className="px-6 py-3 bg-gradient-to-r from-emerald-500 to-teal-500 text-white rounded-lg font-semibold hover:shadow-lg hover:shadow-emerald-500/50 transition-all flex items-center"
          >
            <Plus className="w-5 h-5 mr-2" />
            Add Threshold
          </button>
          <button
            onClick={saveThresholds}
            className="px-6 py-3 bg-gradient-to-r from-cyan-500 to-blue-500 text-white rounded-lg font-semibold hover:shadow-lg hover:shadow-cyan-500/50 transition-all flex items-center"
          >
            <Save className="w-5 h-5 mr-2" />
            Save All Thresholds
          </button>
          <button
            onClick={resetDefaults}
            className="px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg font-semibold hover:shadow-lg hover:shadow-purple-500/50 transition-all flex items-center"
          >
            <RotateCcw className="w-5 h-5 mr-2" />
            Reset to Defaults
          </button>
        </div>
      </div>
    </div>
  )
}
