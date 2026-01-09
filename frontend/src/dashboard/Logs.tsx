import { useEffect, useState } from 'react'
import { Search, Download, Filter } from 'lucide-react'

interface LogEntry {
  id: number
  level: string
  message: string
  source?: string
  created_at: string
}

export default function LogsTab() {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [filter, setFilter] = useState<string>('ALL')
  const [search, setSearch] = useState('')

  useEffect(() => {
    // Simulate log entries
    const mockLogs: LogEntry[] = [
      { id: 1, level: 'INFO', message: 'System initialized', source: 'backend', created_at: new Date().toISOString() },
      { id: 2, level: 'MODBUS', message: 'Connected to COM5', source: 'modbus', created_at: new Date().toISOString() },
      { id: 3, level: 'DEBUG', message: 'Reading registers 45201-45217', source: 'modbus', created_at: new Date().toISOString() },
    ]
    setLogs(mockLogs)
  }, [])

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'ERROR': return 'text-critical'
      case 'WARN': return 'text-warning'
      case 'INFO': return 'text-success'
      case 'DEBUG': return 'text-text-muted'
      case 'MODBUS': return 'text-primary'
      default: return 'text-text'
    }
  }

  const filteredLogs = logs.filter(log => {
    const matchesFilter = filter === 'ALL' || log.level === filter
    const matchesSearch = search === '' || log.message.toLowerCase().includes(search.toLowerCase())
    return matchesFilter && matchesSearch
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-h1 text-text mb-2">OPERATION LOGS</h1>
          <p className="text-text-muted">Real-time Log Stream & Filters</p>
        </div>
        <button className="px-4 py-2 bg-card border border-border rounded-lg text-text hover:bg-primary/10 hover:border-primary/30 transition-colors flex items-center gap-2">
          <Download className="w-4 h-4" />
          Export CSV
        </button>
      </div>

      <div className="bg-card border border-border rounded-lg p-6">
        <div className="flex gap-3 mb-4">
          <div className="flex-1 relative">
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
        </div>

        <div className="space-y-2 max-h-[600px] overflow-y-auto">
          {filteredLogs.map((log) => (
            <div
              key={log.id}
              className="flex items-start gap-4 p-3 bg-background/50 rounded-lg hover:bg-background transition-colors"
            >
              <div className={`text-xs font-mono font-semibold min-w-[80px] ${getLevelColor(log.level)}`}>
                {log.level}
              </div>
              <div className="flex-1">
                <div className="text-text">{log.message}</div>
                <div className="text-xs text-text-muted mt-1">
                  {new Date(log.created_at).toLocaleString()} {log.source && `• ${log.source}`}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

