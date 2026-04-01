import { useEffect, useState } from 'react'
import { wsClient, WebSocketData } from '../lib/websocket'
import { Search, AlertTriangle, CheckCircle2, Clock, XCircle } from 'lucide-react'

interface DefectEntry {
  time: string
  type: string
  confidence: number
  z_rms: number
  kurtosis: number
  severity: string
}

export default function DefectAnalysis() {
  const [data, setData] = useState<WebSocketData | null>(null)
  const [defects, setDefects] = useState<DefectEntry[]>([])

  useEffect(() => {
    const unsubscribe = wsClient.subscribe((newData: WebSocketData) => {
      setData(newData)
      // If anomaly detected, log it
      if (newData.ml_prediction?.class === 1 && newData.ml_prediction.confidence > 0.3) {
        const entry: DefectEntry = {
          time: new Date().toLocaleTimeString('en-US', { hour12: false }),
          type: newData.ml_prediction.class_name || 'Anomaly',
          confidence: newData.ml_prediction.confidence * 100,
          z_rms: newData.sensor_data?.z_rms ?? 0,
          kurtosis: newData.sensor_data?.kurtosis ?? 0,
          severity: newData.ml_prediction.confidence > 0.7 ? 'Critical' : 'Warning',
        }
        setDefects(prev => [entry, ...prev].slice(0, 100))
      }
    })
    return unsubscribe
  }, [])

  const isConnected = data?.connection_status?.connected ?? false
  const ml = data?.ml_prediction
  const isAnomaly = ml?.class === 1

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-6">
      <div className="max-w-[1920px] mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-rose-400 to-red-400 bg-clip-text text-transparent">
              Defect Analysis
            </h1>
            <p className="text-slate-500 text-sm mt-1">AI-detected anomalies & vibration defects</p>
          </div>
          <div className={`px-4 py-2 rounded-lg border text-sm font-semibold flex items-center gap-2 ${
            !isConnected ? 'bg-slate-800 border-slate-700 text-slate-500'
              : isAnomaly ? 'bg-red-500/10 border-red-500/30 text-red-400'
              : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
          }`}>
            {!isConnected ? <XCircle className="w-4 h-4" /> : isAnomaly ? <AlertTriangle className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
            {!isConnected ? 'No Data' : isAnomaly ? 'ANOMALY DETECTED' : 'NORMAL'}
          </div>
        </div>

        {/* Current Status */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-slate-900/80 border border-slate-800/50 rounded-xl p-5">
            <div className="text-xs text-slate-400 font-semibold uppercase mb-2">Current Classification</div>
            <div className={`text-2xl font-bold ${isAnomaly ? 'text-red-400' : 'text-emerald-400'}`}>
              {ml?.class_name ?? 'Waiting...'}
            </div>
          </div>
          <div className="bg-slate-900/80 border border-slate-800/50 rounded-xl p-5">
            <div className="text-xs text-slate-400 font-semibold uppercase mb-2">Confidence</div>
            <div className="text-2xl font-bold text-cyan-400">
              {ml ? `${(ml.confidence * 100).toFixed(1)}%` : '--'}
            </div>
          </div>
          <div className="bg-slate-900/80 border border-slate-800/50 rounded-xl p-5">
            <div className="text-xs text-slate-400 font-semibold uppercase mb-2">Total Defects Logged</div>
            <div className="text-2xl font-bold text-amber-400">{defects.length}</div>
          </div>
        </div>

        {/* Defect Log Table */}
        <div className="bg-slate-900/80 border border-slate-800/50 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-slate-400 mb-3 flex items-center gap-2">
            <Search className="w-4 h-4" /> Detected Defects
          </h3>
          {defects.length === 0 ? (
            <div className="text-center py-12 text-slate-600">
              <CheckCircle2 className="w-12 h-12 mx-auto mb-3" />
              <p className="text-sm">No defects detected yet. System is monitoring...</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-slate-500 text-xs uppercase border-b border-slate-800">
                    <th className="text-left py-2 px-3">Time</th>
                    <th className="text-left py-2 px-3">Type</th>
                    <th className="text-left py-2 px-3">Confidence</th>
                    <th className="text-left py-2 px-3">Z-RMS</th>
                    <th className="text-left py-2 px-3">Kurtosis</th>
                    <th className="text-left py-2 px-3">Severity</th>
                  </tr>
                </thead>
                <tbody>
                  {defects.map((d, i) => (
                    <tr key={i} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                      <td className="py-2 px-3 text-slate-300 font-mono flex items-center gap-1">
                        <Clock className="w-3 h-3 text-slate-500" /> {d.time}
                      </td>
                      <td className="py-2 px-3 text-white">{d.type}</td>
                      <td className="py-2 px-3 text-cyan-400">{d.confidence.toFixed(1)}%</td>
                      <td className="py-2 px-3 text-blue-400">{d.z_rms.toFixed(3)}</td>
                      <td className="py-2 px-3 text-purple-400">{d.kurtosis.toFixed(3)}</td>
                      <td className="py-2 px-3">
                        <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                          d.severity === 'Critical' ? 'bg-red-500/20 text-red-400' : 'bg-amber-500/20 text-amber-400'
                        }`}>{d.severity}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
