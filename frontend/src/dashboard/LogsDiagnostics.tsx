import { useEffect, useState, useCallback } from 'react'
import { FileText, RefreshCw, Search, AlertTriangle, CheckCircle2, Info } from 'lucide-react'
import { logsAPI, OfflineLogStats } from '@/lib/api'

export default function LogsDiagnostics() {
  const [logs, setLogs] = useState<string[]>([])
  const [stats, setStats] = useState<OfflineLogStats | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [logLines, setLogLines] = useState(100)
  const [logFile, setLogFile] = useState('app')

  const fetchLogs = useCallback(async () => {
    setLoading(true)
    try {
      const response = await logsAPI.getOfflineLogs({ file: logFile, limit: logLines, search: searchQuery.trim() || undefined })
      setLogs(response.entries.map((entry) => entry.raw))
    } catch (err) {
      setLogs([`Failed to read ${logFile} logs. Ensure backend is running and log files are accessible.`])
    } finally {
      setLoading(false)
    }
  }, [logFile, logLines, searchQuery])

  const fetchStats = useCallback(async () => {
    try {
      const data = await logsAPI.getOfflineStats(logFile)
      setStats(data)
    } catch (err) {
      setStats(null)
    }
  }, [logFile])

  const searchLogs = async () => {
    await fetchLogs()
  }

  useEffect(() => {
    fetchLogs()
    fetchStats()

    // Auto-refresh logs every 3 seconds if enabled
    let interval: ReturnType<typeof setInterval>
    if (autoRefresh) {
      interval = setInterval(() => {
        fetchLogs()
        fetchStats()
      }, 3000)
    }

    return () => {
      if (interval) clearInterval(interval)
    }
  }, [autoRefresh, logLines, fetchLogs, fetchStats])

  const getSeverityColor = (log: string) => {
    if (log.includes('ERROR')) return 'text-red-400'
    if (log.includes('WARNING')) return 'text-amber-400'
    if (log.includes('INFO')) return 'text-cyan-400'
    return 'text-slate-400'
  }

  const getSeverityBg = (log: string) => {
    if (log.includes('ERROR')) return 'bg-red-500/10'
    if (log.includes('WARNING')) return 'bg-amber-500/10'
    if (log.includes('INFO')) return 'bg-cyan-500/10'
    return 'bg-slate-800/30'
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-blue-500/20 rounded-lg">
              <FileText className="w-6 h-6 text-blue-400" />
            </div>
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
                Logs & Diagnostics
              </h1>
              <p className="text-slate-500 text-sm mt-1">Logs are stored offline on the server; view files directly from the log folder.</p>
            </div>
          </div>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div className="relative group">
              <div className="absolute inset-0 bg-gradient-to-br from-blue-500/20 to-cyan-500/20 rounded-xl blur-xl group-hover:blur-2xl transition-all duration-300" />
              <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-xl p-4">
                <p className="text-slate-500 text-xs uppercase font-semibold">Total Lines</p>
                <p className="text-2xl font-bold text-cyan-400 mt-2">{stats.line_count.toLocaleString()}</p>
              </div>
            </div>

            <div className="relative group">
              <div className="absolute inset-0 bg-gradient-to-br from-red-500/20 to-orange-500/20 rounded-xl blur-xl group-hover:blur-2xl transition-all duration-300" />
              <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-xl p-4">
                <p className="text-slate-500 text-xs uppercase font-semibold">Errors</p>
                <p className="text-2xl font-bold text-red-400 mt-2">{stats.level_counts?.ERROR ?? 0}</p>
              </div>
            </div>

            <div className="relative group">
              <div className="absolute inset-0 bg-gradient-to-br from-amber-500/20 to-yellow-500/20 rounded-xl blur-xl group-hover:blur-2xl transition-all duration-300" />
              <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-xl p-4">
                <p className="text-slate-500 text-xs uppercase font-semibold">Warnings</p>
                <p className="text-2xl font-bold text-amber-400 mt-2">{stats.level_counts?.WARNING ?? stats.level_counts?.WARN ?? 0}</p>
              </div>
            </div>

            <div className="relative group">
              <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/20 to-teal-500/20 rounded-xl blur-xl group-hover:blur-2xl transition-all duration-300" />
              <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-xl p-4">
                <p className="text-slate-500 text-xs uppercase font-semibold">Info Logs</p>
                <p className="text-2xl font-bold text-emerald-400 mt-2">{stats.level_counts?.INFO ?? 0}</p>
              </div>
            </div>

            <div className="relative group">
              <div className="absolute inset-0 bg-gradient-to-br from-purple-500/20 to-pink-500/20 rounded-xl blur-xl group-hover:blur-2xl transition-all duration-300" />
              <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-xl p-4">
                <p className="text-slate-500 text-xs uppercase font-semibold">File Size</p>
                <p className="text-2xl font-bold text-purple-400 mt-2">{stats.size_mb.toFixed(2)} MB</p>
              </div>
            </div>
          </div>
        )}

        {/* Controls */}
        <div className="relative group">
          <div className="absolute inset-0 bg-gradient-to-br from-slate-500/20 to-slate-500/20 rounded-xl blur-xl group-hover:blur-2xl transition-all duration-300" />
          <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-xl p-6">
            <div className="flex flex-wrap gap-4 items-end">
              <div>
                <label className="block text-sm font-semibold text-slate-400 mb-2">Log File</label>
                <select
                  value={logFile}
                  onChange={(e) => setLogFile(e.target.value)}
                  className="px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-200 focus:outline-none focus:border-blue-500"
                >
                  <option value="app">App</option>
                  <option value="errors">Errors</option>
                  <option value="modbus">Modbus</option>
                  <option value="readings">Readings</option>
                </select>
              </div>

              <div className="flex-1 min-w-[200px]">
                <label className="block text-sm font-semibold text-slate-400 mb-2">Search Logs</label>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && searchLogs()}
                  placeholder="Search ERROR, WARNING, parameter name..."
                  className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-400 mb-2">Lines</label>
                <select
                  value={logLines}
                  onChange={(e) => setLogLines(parseInt(e.target.value))}
                  className="px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-200 focus:outline-none focus:border-blue-500"
                >
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                  <option value={200}>200</option>
                  <option value={500}>500</option>
                </select>
              </div>

              <button
                onClick={searchLogs}
                disabled={loading}
                className="px-6 py-2 bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-lg hover:shadow-lg hover:shadow-blue-500/50 transition-all flex items-center gap-2 disabled:opacity-50"
              >
                <Search className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                Search
              </button>

              <button
                onClick={fetchLogs}
                disabled={loading}
                className="px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg hover:bg-slate-700 transition-all flex items-center gap-2"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </button>

              <button
                onClick={() => setAutoRefresh(!autoRefresh)}
                className={`px-4 py-2 border rounded-lg transition-all flex items-center gap-2 ${
                  autoRefresh
                    ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-400'
                    : 'bg-slate-800 border-slate-700 text-slate-300'
                }`}
              >
                <div className={`w-2 h-2 rounded-full ${autoRefresh ? 'bg-emerald-400' : 'bg-slate-500'}`} />
                {autoRefresh ? 'Auto ON' : 'Auto OFF'}
              </button>
            </div>
          </div>
        </div>

        {/* Logs Display */}
        <div className="relative group">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500/20 to-cyan-500/20 rounded-xl blur-xl group-hover:blur-2xl transition-all duration-300" />
          <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-xl overflow-hidden">
            <div className="bg-slate-800/50 px-6 py-3 border-b border-slate-800/50 flex items-center justify-between">
              <h2 className="text-lg font-bold text-slate-200 flex items-center gap-2">
                <FileText className="w-5 h-5 text-blue-400" />
                Live Logs ({logs.length})
              </h2>
              {loading && <div className="w-3 h-3 rounded-full bg-blue-400 animate-pulse"></div>}
            </div>

            {logs.length === 0 ? (
              <div className="p-8 text-center">
                <p className="text-slate-500">No logs available</p>
              </div>
            ) : (
              <div className="max-h-[600px] overflow-y-auto font-mono text-sm">
                {logs.map((log, idx) => (
                  <div
                    key={idx}
                    className={`px-6 py-2 border-b border-slate-800/30 hover:bg-slate-800/20 transition-colors ${getSeverityBg(log)}`}
                  >
                    <div className="flex items-start gap-3">
                      <span className={`flex-shrink-0 mt-0.5 ${getSeverityColor(log)}`}>
                        {log.includes('ERROR') && <AlertTriangle className="w-4 h-4" />}
                        {log.includes('WARNING') && <AlertTriangle className="w-4 h-4" />}
                        {log.includes('INFO') && <Info className="w-4 h-4" />}
                      </span>
                      <code className="flex-1 text-slate-300 break-all">{log}</code>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Info Box */}
        <div className="relative group">
          <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/20 to-blue-500/20 rounded-xl blur-xl group-hover:blur-2xl transition-all duration-300" />
          <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-xl p-6">
            <div className="flex items-start gap-4">
              <CheckCircle2 className="w-6 h-6 text-cyan-400 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-bold text-slate-200 mb-2">Logging System Status</h3>
                <ul className="space-y-1 text-slate-400 text-sm">
                  <li>✅ Log viewer tails disk files even if DB connectivity is unavailable.</li>
                  <li>✅ Location: backend/logs/*.log with rotation handled by the backend.</li>
                  <li>✅ Use tail -f backend/logs/app.log for live monitoring when SSHing.</li>
                  <li>✅ Frontend search filters locally to avoid extra backend load.</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
