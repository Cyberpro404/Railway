import { useCallback, useEffect, useMemo, useState } from 'react'
import { Search, Download, RefreshCw } from 'lucide-react'
import { logsAPI, OfflineLogEntry, OfflineLogStats } from '@/lib/api'

const LOG_FILES = [
  { value: 'app', label: 'App' },
  { value: 'errors', label: 'Errors' },
  { value: 'modbus', label: 'Modbus' },
  { value: 'readings', label: 'Readings' },
]

export default function LogsTab() {
  const [logs, setLogs] = useState<OfflineLogEntry[]>([])
  const [stats, setStats] = useState<OfflineLogStats | null>(null)
  const [filter, setFilter] = useState<string>('ALL')
  const [search, setSearch] = useState('')
  const [logFile, setLogFile] = useState<string>('app')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadStats = useCallback(async () => {
    try {
      const data = await logsAPI.getOfflineStats(logFile)
      setStats(data)
    } catch (err) {
      setStats(null)
    }
  }, [logFile])

  const loadLogs = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await logsAPI.getOfflineLogs({ file: logFile, limit: 400, search: search.trim() || undefined })
      setLogs(data.entries)
    } catch (err) {
      setError('Unable to load offline logs. Check backend availability or log file permissions.')
    } finally {
      setLoading(false)
    }
  }, [logFile, search])

  useEffect(() => {
    loadStats()
    loadLogs()
  }, [loadLogs, loadStats])

  const getLevelColor = (level: string) => {
    const normalized = level?.toUpperCase?.() || ''
    switch (normalized) {
      case 'ERROR': return 'text-critical'
      case 'WARN':
      case 'WARNING': return 'text-warning'
      case 'INFO': return 'text-success'
      case 'DEBUG': return 'text-text-muted'
      case 'MODBUS': return 'text-primary'
      default: return 'text-text'
    }
  }

  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      const level = log.level?.toUpperCase?.() || ''
      const matchesFilter = filter === 'ALL' || level === filter
      const matchesSearch = search === '' || log.message.toLowerCase().includes(search.toLowerCase()) || log.raw.toLowerCase().includes(search.toLowerCase())
      return matchesFilter && matchesSearch
    })
  }, [logs, filter, search])

  const exportCsv = () => {
    if (filteredLogs.length === 0) return
    const header = 'timestamp,level,source,message\n'
    const rows = filteredLogs
      .map((log) => {
        const safeMsg = log.message.replace(/"/g, '""')
        return `"${log.timestamp || ''}","${log.level}","${log.source || ''}","${safeMsg}"`
      })
      .join('\n')
    const blob = new Blob([header + rows], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `${logFile}-logs.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-h1 text-text mb-2">OPERATION LOGS</h1>
          <p className="text-text-muted">Offline log reader (file-backed)</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={logFile}
            onChange={(e) => setLogFile(e.target.value)}
            className="px-3 py-2 bg-background border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-primary/50"
          >
            {LOG_FILES.map((file) => (
              <option key={file.value} value={file.value}>{file.label}</option>
            ))}
          </select>
          <button
            onClick={exportCsv}
            className="px-4 py-2 bg-card border border-border rounded-lg text-text hover:bg-primary/10 hover:border-primary/30 transition-colors flex items-center gap-2"
            disabled={filteredLogs.length === 0}
          >
            <Download className="w-4 h-4" />
            Export CSV
          </button>
        </div>
      </div>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="bg-card border border-border rounded-lg p-3">
            <p className="text-xs text-text-muted">Lines</p>
            <p className="text-lg font-semibold text-text">{stats.line_count}</p>
          </div>
          <div className="bg-card border border-border rounded-lg p-3">
            <p className="text-xs text-text-muted">Size</p>
            <p className="text-lg font-semibold text-text">{stats.size_mb.toFixed(3)} MB</p>
          </div>
          <div className="bg-card border border-border rounded-lg p-3">
            <p className="text-xs text-text-muted">Errors</p>
            <p className="text-lg font-semibold text-critical">{stats.level_counts?.ERROR || 0}</p>
          </div>
          <div className="bg-card border border-border rounded-lg p-3">
            <p className="text-xs text-text-muted">Warnings</p>
            <p className="text-lg font-semibold text-warning">{stats.level_counts?.WARNING || stats.level_counts?.WARN || 0}</p>
          </div>
        </div>
      )}

      <div className="bg-card border border-border rounded-lg p-6">
        <div className="flex flex-wrap gap-3 mb-4 items-center">
          <div className="flex-1 min-w-[200px] relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-text-muted" />
            <input
              type="text"
              placeholder="Search logs..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-background border border-border rounded-lg text-text placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
          </div>
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="px-4 py-2 bg-background border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-primary/50"
          >
            <option value="ALL">ALL</option>
            <option value="DEBUG">DEBUG</option>
            <option value="INFO">INFO</option>
            <option value="WARN">WARN</option>
            <option value="ERROR">ERROR</option>
            <option value="MODBUS">MODBUS</option>
          </select>
          <button
            onClick={loadLogs}
            disabled={loading}
            className="px-4 py-2 bg-background border border-border rounded-lg text-text hover:bg-primary/10 transition-colors flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {error && (
          <div className="mb-3 text-critical text-sm">{error}</div>
        )}

        <div className="space-y-2 max-h-[600px] overflow-y-auto">
          {loading && (
            <div className="text-text-muted text-sm">Loading logs...</div>
          )}
          {!loading && filteredLogs.length === 0 && (
            <div className="text-text-muted text-sm">No logs match your filters.</div>
          )}
          {filteredLogs.map((log, idx) => (
            <div
              key={`${log.timestamp}-${idx}`}
              className="flex items-start gap-4 p-3 bg-background/50 rounded-lg hover:bg-background transition-colors"
            >
              <div className={`text-xs font-mono font-semibold min-w-[80px] ${getLevelColor(log.level)}`}>
                {log.level}
              </div>
              <div className="flex-1">
                <div className="text-text">{log.message}</div>
                <div className="text-xs text-text-muted mt-1">
                  {log.timestamp ? new Date(log.timestamp).toLocaleString() : '—'} {log.source && `• ${log.source}`}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

