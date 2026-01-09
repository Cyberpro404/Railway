import { useEffect, useState } from 'react'
import { Save, RotateCcw, Eye } from 'lucide-react'
import { thresholdsAPI, Threshold } from '@/lib/api'

export default function ThresholdsTab() {
  const [scalarThresholds, setScalarThresholds] = useState<Threshold[]>([])
  const [bandThresholds, setBandThresholds] = useState<Threshold[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadThresholds()
  }, [])

  const loadThresholds = async () => {
    try {
      const all = await thresholdsAPI.getAll()
      setScalarThresholds(all.filter(t => t.threshold_type === 'scalar'))
      setBandThresholds(all.filter(t => t.threshold_type === 'band'))
    } catch (error) {
      console.error('Error loading thresholds:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleUpdate = async (parameter: string, field: 'warn_value' | 'alarm_value', value: number) => {
    const threshold = [...scalarThresholds, ...bandThresholds].find(t => t.parameter === parameter)
    if (!threshold) return

    try {
      await thresholdsAPI.update(parameter, { [field]: value })
      await loadThresholds()
    } catch (error) {
      console.error('Error updating threshold:', error)
    }
  }

  const handleResetDefaults = async () => {
    try {
      await thresholdsAPI.resetDefaults()
      await loadThresholds()
    } catch (error) {
      console.error('Error resetting defaults:', error)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto mb-4" />
          <div className="text-text-muted font-medium">Loading thresholds...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div>
        <h1 className="text-h1 text-text mb-2 font-bold tracking-tight">THRESHOLDS</h1>
        <p className="text-text-muted font-medium">Configure Warning & Alarm Limits</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Scalar Thresholds */}
        <div className="bg-card border border-border rounded-lg p-6 card-hover shadow-xl">
          <h3 className="text-h2 text-text mb-4 font-bold">SCALAR THRESHOLDS</h3>
          <div className="space-y-4">
            {scalarThresholds.map((threshold) => (
              <div key={threshold.id} className="space-y-3 p-4 bg-background/50 rounded-lg">
                <div className="font-semibold text-text">{threshold.parameter.toUpperCase()}</div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm text-text-muted block mb-1">Warn</label>
                    <input
                      type="number"
                      value={threshold.warn_value}
                      onChange={(e) => handleUpdate(threshold.parameter, 'warn_value', parseFloat(e.target.value))}
                      className="w-full px-3 py-2 bg-background border border-border rounded-lg text-text font-mono focus:outline-none focus:ring-2 focus:ring-primary/50"
                    />
                  </div>
                  <div>
                    <label className="text-sm text-text-muted block mb-1">Alarm</label>
                    <input
                      type="number"
                      value={threshold.alarm_value}
                      onChange={(e) => handleUpdate(threshold.parameter, 'alarm_value', parseFloat(e.target.value))}
                      className="w-full px-3 py-2 bg-background border border-border rounded-lg text-text font-mono focus:outline-none focus:ring-2 focus:ring-primary/50"
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Band Thresholds */}
        <div className="bg-card border border-border rounded-lg p-6 card-hover shadow-xl">
          <h3 className="text-h2 text-text mb-4 font-bold">BAND THRESHOLDS</h3>
          <div className="space-y-4">
            <div className="p-4 bg-background/50 rounded-lg">
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="text-sm text-text-muted block mb-1">Axis</label>
                  <select className="w-full px-3 py-2 bg-background border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-primary/50">
                    <option>Z</option>
                    <option>X</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm text-text-muted block mb-1">Band</label>
                  <input
                    type="number"
                    defaultValue={1}
                    className="w-full px-3 py-2 bg-background border border-border rounded-lg text-text font-mono focus:outline-none focus:ring-2 focus:ring-primary/50"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-text-muted block mb-1">RMS Warn</label>
                  <input
                    type="number"
                    defaultValue={0.5}
                    className="w-full px-3 py-2 bg-background border border-border rounded-lg text-text font-mono focus:outline-none focus:ring-2 focus:ring-primary/50"
                  />
                </div>
                <div>
                  <label className="text-sm text-text-muted block mb-1">RMS Alarm</label>
                  <input
                    type="number"
                    defaultValue={1.0}
                    className="w-full px-3 py-2 bg-background border border-border rounded-lg text-text font-mono focus:outline-none focus:ring-2 focus:ring-primary/50"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3">
        <button className="px-4 py-2 bg-primary/10 border border-primary/30 rounded-lg text-primary hover:bg-primary/20 transition-colors flex items-center gap-2">
          <Save className="w-4 h-4" />
          SAVE TO DB
        </button>
        <button
          onClick={handleResetDefaults}
          className="px-4 py-2 bg-card border border-border rounded-lg text-text hover:bg-primary/10 hover:border-primary/30 transition-colors flex items-center gap-2"
        >
          <RotateCcw className="w-4 h-4" />
          RESET DEFAULTS
        </button>
        <button className="px-4 py-2 bg-card border border-border rounded-lg text-text hover:bg-primary/10 hover:border-primary/30 transition-colors flex items-center gap-2">
          <Eye className="w-4 h-4" />
          PREVIEW
        </button>
        <button className="px-4 py-2 bg-card border border-border rounded-lg text-text hover:bg-primary/10 hover:border-primary/30 transition-colors">
          APPLY ALL BANDS
        </button>
      </div>
    </div>
  )
}

