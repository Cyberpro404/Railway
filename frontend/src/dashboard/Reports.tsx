import { useEffect, useState, useCallback } from 'react'
import { wsClient, WebSocketData } from '../lib/websocket'
import { FileSpreadsheet, Download, Clock, Activity, Thermometer } from 'lucide-react'

interface ReportEntry {
  time: string
  z_rms: number
  x_rms: number
  temperature: number
  iso_class: string
  ml_class: string
  confidence: number
}

export default function Reports() {
  const [data, setData] = useState<WebSocketData | null>(null)
  const [reportLog, setReportLog] = useState<ReportEntry[]>([])
  const [recording, setRecording] = useState(false)

  useEffect(() => {
    const unsubscribe = wsClient.subscribe((newData: WebSocketData) => {
      setData(newData)
      if (recording) {
        setReportLog(prev => {
          const entry: ReportEntry = {
            time: new Date().toLocaleTimeString('en-US', { hour12: false }),
            z_rms: newData.sensor_data?.z_rms ?? 0,
            x_rms: newData.sensor_data?.x_rms ?? 0,
            temperature: newData.sensor_data?.temperature ?? 0,
            iso_class: newData.iso_severity?.class ?? 'N/A',
            ml_class: newData.ml_prediction?.class_name ?? 'N/A',
            confidence: (newData.ml_prediction?.confidence ?? 0) * 100,
          }
          return [...prev, entry].slice(-5000)
        })
      }
    })
    return unsubscribe
  }, [recording])

  const exportCSV = useCallback(() => {
    const header = 'Time,Z_RMS,X_RMS,Temperature,ISO_Class,ML_Class,Confidence'
    const rows = reportLog.map(r =>
      `${r.time},${r.z_rms.toFixed(3)},${r.x_rms.toFixed(3)},${r.temperature.toFixed(1)},${r.iso_class},${r.ml_class},${r.confidence.toFixed(1)}`
    )
    const csv = [header, ...rows].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `gandiva_report_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }, [reportLog])

  const exportJSON = useCallback(() => {
    const json = JSON.stringify(reportLog, null, 2)
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `gandiva_report_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`
    a.click()
    URL.revokeObjectURL(url)
  }, [reportLog])

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-6">
      <div className="max-w-[1920px] mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-orange-400 to-amber-400 bg-clip-text text-transparent">
              Reports
            </h1>
            <p className="text-slate-500 text-sm mt-1">Record & export sensor data reports</p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => { setRecording(!recording); if (!recording) setReportLog([]) }}
              className={`px-4 py-2 rounded-lg border text-sm font-semibold transition flex items-center gap-2 ${
                recording ? 'bg-red-500/20 border-red-500/30 text-red-400' : 'bg-emerald-500/20 border-emerald-500/30 text-emerald-400'
              }`}>
              <div className={`w-2 h-2 rounded-full ${recording ? 'bg-red-400 animate-pulse' : 'bg-emerald-400'}`} />
              {recording ? 'Stop Recording' : 'Start Recording'}
            </button>
          </div>
        </div>

        {/* Recording Status */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-slate-900/80 border border-slate-800/50 rounded-xl p-5">
            <div className="text-xs text-slate-400 font-semibold uppercase mb-2">Status</div>
            <div className={`text-xl font-bold ${recording ? 'text-red-400' : 'text-slate-500'}`}>
              {recording ? '● Recording' : '○ Idle'}
            </div>
          </div>
          <div className="bg-slate-900/80 border border-slate-800/50 rounded-xl p-5">
            <div className="text-xs text-slate-400 font-semibold uppercase mb-2">Data Points</div>
            <div className="text-xl font-bold text-cyan-400">{reportLog.length}</div>
          </div>
          <div className="bg-slate-900/80 border border-slate-800/50 rounded-xl p-5">
            <div className="text-xs text-slate-400 font-semibold uppercase mb-2">Current Z-RMS</div>
            <div className="text-xl font-bold text-blue-400">{(data?.sensor_data?.z_rms ?? 0).toFixed(3)} mm/s</div>
          </div>
        </div>

        {/* Export Buttons */}
        <div className="flex gap-3">
          <button onClick={exportCSV} disabled={reportLog.length === 0}
            className="px-5 py-2.5 bg-orange-600/20 border border-orange-500/30 text-orange-400 rounded-lg hover:bg-orange-600/30 transition flex items-center gap-2 text-sm font-semibold disabled:opacity-30">
            <Download className="w-4 h-4" /> Export CSV
          </button>
          <button onClick={exportJSON} disabled={reportLog.length === 0}
            className="px-5 py-2.5 bg-blue-600/20 border border-blue-500/30 text-blue-400 rounded-lg hover:bg-blue-600/30 transition flex items-center gap-2 text-sm font-semibold disabled:opacity-30">
            <FileSpreadsheet className="w-4 h-4" /> Export JSON
          </button>
        </div>

        {/* Recent Recordings Preview */}
        {reportLog.length > 0 && (
          <div className="bg-slate-900/80 border border-slate-800/50 rounded-xl p-4">
            <h3 className="text-sm font-semibold text-slate-400 mb-3">Recorded Data (last 20)</h3>
            <div className="overflow-x-auto max-h-80 overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-slate-900">
                  <tr className="text-slate-500 text-xs uppercase border-b border-slate-800">
                    <th className="text-left py-2 px-3">Time</th>
                    <th className="text-right py-2 px-3">Z-RMS</th>
                    <th className="text-right py-2 px-3">X-RMS</th>
                    <th className="text-right py-2 px-3">Temp</th>
                    <th className="text-left py-2 px-3">ISO</th>
                    <th className="text-left py-2 px-3">ML</th>
                  </tr>
                </thead>
                <tbody>
                  {reportLog.slice(-20).reverse().map((r, i) => (
                    <tr key={i} className="border-b border-slate-800/30">
                      <td className="py-1.5 px-3 text-slate-300 font-mono text-xs">{r.time}</td>
                      <td className="py-1.5 px-3 text-right text-blue-400 font-mono">{r.z_rms.toFixed(3)}</td>
                      <td className="py-1.5 px-3 text-right text-emerald-400 font-mono">{r.x_rms.toFixed(3)}</td>
                      <td className="py-1.5 px-3 text-right text-amber-400 font-mono">{r.temperature.toFixed(1)}</td>
                      <td className="py-1.5 px-3 text-orange-400 text-xs">{r.iso_class}</td>
                      <td className="py-1.5 px-3 text-purple-400 text-xs">{r.ml_class}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
