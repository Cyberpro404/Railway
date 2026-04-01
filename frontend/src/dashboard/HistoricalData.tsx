import { useEffect, useState, useCallback } from 'react'
import { wsClient, WebSocketData } from '../lib/websocket'
import { Clock, Download, RefreshCw } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts'

export default function HistoricalData() {
  const [batchData, setBatchData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [liveHistory, setLiveHistory] = useState<any[]>([])
  const [limit, setLimit] = useState(200)

  // Also collect live data for comparison
  useEffect(() => {
    const unsubscribe = wsClient.subscribe((newData: WebSocketData) => {
      const ts = new Date().toLocaleTimeString('en-US', { hour12: false })
      setLiveHistory(prev => {
        const updated = [...prev, {
          time: ts,
          z_rms: newData.sensor_data?.z_rms ?? 0,
          x_rms: newData.sensor_data?.x_rms ?? 0,
          temperature: newData.sensor_data?.temperature ?? 0,
        }]
        return updated.slice(-200)
      })
    })
    return unsubscribe
  }, [])

  const fetchBatch = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`/api/v1/data/batch?limit=${limit}`)
      if (res.ok) {
        const json = await res.json()
        setBatchData(json.data || [])
      }
    } catch (e) {
      console.error('Failed to fetch batch data:', e)
    } finally {
      setLoading(false)
    }
  }, [limit])

  useEffect(() => { fetchBatch() }, [fetchBatch])

  const displayData = batchData.length > 0 ? batchData : liveHistory

  const handleExport = () => {
    const csv = ['time,z_rms,x_rms,temperature', ...displayData.map(d =>
      `${d.time},${d.z_rms},${d.x_rms},${d.temperature}`
    )].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `vibration_data_${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-6">
      <div className="max-w-[1920px] mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-violet-400 to-purple-400 bg-clip-text text-transparent">
              Historical Data
            </h1>
            <p className="text-slate-500 text-sm mt-1">Browse past vibration & temperature readings</p>
          </div>
          <div className="flex gap-2">
            <select value={limit} onChange={e => setLimit(Number(e.target.value))}
              className="bg-slate-800 border border-slate-700 text-slate-300 rounded-lg px-3 py-2 text-sm">
              <option value={50}>Last 50</option>
              <option value={100}>Last 100</option>
              <option value={200}>Last 200</option>
              <option value={500}>Last 500</option>
            </select>
            <button onClick={fetchBatch} disabled={loading}
              className="px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg hover:bg-slate-700 transition flex items-center gap-2 text-sm">
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
            </button>
            <button onClick={handleExport}
              className="px-4 py-2 bg-violet-600/20 border border-violet-500/30 text-violet-400 rounded-lg hover:bg-violet-600/30 transition flex items-center gap-2 text-sm">
              <Download className="w-4 h-4" /> Export CSV
            </button>
          </div>
        </div>

        {/* Charts */}
        <div className="bg-slate-900/80 border border-slate-800/50 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-slate-400 mb-3 flex items-center gap-2">
            <Clock className="w-4 h-4" /> Vibration History ({displayData.length} points)
          </h3>
          <ResponsiveContainer width="100%" height={350}>
            <LineChart data={displayData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
              <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
              <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 8 }} />
              <Legend />
              <Line type="monotone" dataKey="z_rms" stroke="#3b82f6" strokeWidth={1.5} dot={false} name="Z-RMS (mm/s)" />
              <Line type="monotone" dataKey="x_rms" stroke="#10b981" strokeWidth={1.5} dot={false} name="X-RMS (mm/s)" />
              <Line type="monotone" dataKey="temperature" stroke="#f59e0b" strokeWidth={1.5} dot={false} name="Temp (°C)" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Data Table */}
        <div className="bg-slate-900/80 border border-slate-800/50 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-slate-400 mb-3">Raw Data ({displayData.length} records)</h3>
          <div className="overflow-x-auto max-h-96 overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-slate-900">
                <tr className="text-slate-500 text-xs uppercase border-b border-slate-800">
                  <th className="text-left py-2 px-3">#</th>
                  <th className="text-left py-2 px-3">Time</th>
                  <th className="text-right py-2 px-3">Z-RMS</th>
                  <th className="text-right py-2 px-3">X-RMS</th>
                  <th className="text-right py-2 px-3">Temp °C</th>
                </tr>
              </thead>
              <tbody>
                {displayData.slice(-50).reverse().map((d, i) => (
                  <tr key={i} className="border-b border-slate-800/30 hover:bg-slate-800/30">
                    <td className="py-1.5 px-3 text-slate-600">{displayData.length - i}</td>
                    <td className="py-1.5 px-3 text-slate-300 font-mono text-xs">{d.time}</td>
                    <td className="py-1.5 px-3 text-right text-blue-400 font-mono">{Number(d.z_rms || 0).toFixed(3)}</td>
                    <td className="py-1.5 px-3 text-right text-emerald-400 font-mono">{Number(d.x_rms || 0).toFixed(3)}</td>
                    <td className="py-1.5 px-3 text-right text-amber-400 font-mono">{Number(d.temperature || 0).toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
