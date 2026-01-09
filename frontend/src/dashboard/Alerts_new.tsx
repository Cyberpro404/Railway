import { useEffect, useState } from 'react'
import { AlertTriangle, CheckCircle, Volume2, VolumeX, Bell, Clock, Filter } from 'lucide-react'
import { alertsAPI, Alert } from '@/lib/api'
import AdvancedChart from '@/components/ui/AdvancedChart'
import StatusBadge from '@/components/ui/StatusBadge'
import StatCard from '@/components/ui/StatCard'
import DataTable from '@/components/ui/DataTable'

export default function AlertsTab() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [soundEnabled, setSoundEnabled] = useState(true)
  const [filteredAlerts, setFilteredAlerts] = useState<Alert[]>([])
  const [filterType, setFilterType] = useState<'all' | 'critical' | 'warning'>('all')

  useEffect(() => {
    loadAlerts()
    const interval = setInterval(loadAlerts, 5000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (filterType === 'all') {
      setFilteredAlerts(alerts)
    } else {
      setFilteredAlerts(alerts.filter(a => a.severity === filterType))
    }
  }, [alerts, filterType])

  const loadAlerts = async () => {
    try {
      const data = await alertsAPI.getActive()
      setAlerts(data.sort((a, b) => {
        if (a.severity !== b.severity) {
          return a.severity === 'critical' ? -1 : 1
        }
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      }))
    } catch (error) {
      console.error('Error loading alerts:', error)
    }
  }

  const handleAcknowledge = async (alertId: number) => {
    try {
      await alertsAPI.acknowledge(alertId)
      await loadAlerts()
    } catch (error) {
      console.error('Error acknowledging alert:', error)
    }
  }

  const criticalCount = alerts.filter(a => a.severity === 'critical' && !a.acknowledged).length
  const warningCount = alerts.filter(a => a.severity === 'warning' && !a.acknowledged).length
  const totalAcknowledged = alerts.filter(a => a.acknowledged).length

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Enhanced Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-1 h-8 bg-gradient-to-b from-critical to-critical/50 rounded-full" />
            <h1 className="text-4xl font-bold text-text tracking-tight">Alert Center</h1>
          </div>
          <p className="text-text-muted font-medium flex items-center gap-2">
            <Bell className="w-4 h-4" />
            Real-time system notifications & severity management
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setSoundEnabled(!soundEnabled)}
            className={`px-4 py-3 rounded-lg border transition-all flex items-center gap-2 font-semibold ${
              soundEnabled
                ? 'bg-success/20 border-success/40 text-success neon-glow-hover'
                : 'bg-card border-border text-text-muted hover:border-primary/40'
            }`}
          >
            {soundEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
            Audio {soundEnabled ? 'ON' : 'OFF'}
          </button>
          <button className="px-4 py-3 bg-gradient-to-r from-critical to-critical/80 border border-critical/50 rounded-lg text-text font-semibold hover:shadow-lg transition-all">
            TEST ALERT
          </button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          title="Critical Alerts"
          value={criticalCount}
          icon={<AlertTriangle className="w-6 h-6" />}
          color={criticalCount > 0 ? 'critical' : 'success'}
          change={criticalCount > 2 ? 5.2 : -2.1}
        />
        <StatCard
          title="Warnings"
          value={warningCount}
          icon={<AlertTriangle className="w-6 h-6" />}
          color={warningCount > 0 ? 'warning' : 'success'}
          change={warningCount > 1 ? 3.4 : -0.5}
        />
        <StatCard
          title="Acknowledged"
          value={totalAcknowledged}
          icon={<CheckCircle className="w-6 h-6" />}
          color="success"
          change={1.2}
        />
        <StatCard
          title="Response Time"
          value="2.3min"
          icon={<Clock className="w-6 h-6" />}
          color="success"
          change={-0.8}
          changeLabel="vs avg"
        />
      </div>

      {/* Alert Status & Filter Controls */}
      <AdvancedChart 
        title="Alert Filter & Controls" 
        subtitle="Organize and manage alerts by severity"
        headerAction={
          <div className="flex gap-2">
            <button
              onClick={() => setFilterType('all')}
              className={`px-3 py-1.5 rounded-lg border transition-all text-sm font-medium ${
                filterType === 'all'
                  ? 'bg-primary/20 border-primary/40 text-primary'
                  : 'bg-card border-border text-text-muted hover:border-primary/40'
              }`}
            >
              All ({alerts.length})
            </button>
            <button
              onClick={() => setFilterType('critical')}
              className={`px-3 py-1.5 rounded-lg border transition-all text-sm font-medium ${
                filterType === 'critical'
                  ? 'bg-critical/20 border-critical/40 text-critical'
                  : 'bg-card border-border text-text-muted hover:border-critical/40'
              }`}
            >
              Critical ({criticalCount})
            </button>
            <button
              onClick={() => setFilterType('warning')}
              className={`px-3 py-1.5 rounded-lg border transition-all text-sm font-medium ${
                filterType === 'warning'
                  ? 'bg-warning/20 border-warning/40 text-warning'
                  : 'bg-card border-border text-text-muted hover:border-warning/40'
              }`}
            >
              Warning ({warningCount})
            </button>
          </div>
        }
      >
        <div className="text-sm text-text-muted">
          {filteredAlerts.length === 0 ? (
            <div className="py-12 text-center">
              <CheckCircle className="w-12 h-12 text-success mx-auto mb-4 opacity-50" />
              <p className="text-text-muted">All systems nominal - No active alerts</p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredAlerts.map((alert) => (
                <div
                  key={alert.id}
                  className={`bg-background/50 border rounded-lg p-4 flex items-center justify-between hover:border-primary/40 transition-all ${
                    alert.severity === 'critical'
                      ? 'border-critical/30'
                      : 'border-warning/30'
                  }`}
                >
                  <div className="flex items-start gap-4 flex-1">
                    <div className={`p-2 rounded-lg flex-shrink-0 ${
                      alert.severity === 'critical'
                        ? 'bg-critical/20 text-critical'
                        : 'bg-warning/20 text-warning'
                    }`}>
                      <AlertTriangle className="w-5 h-5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="font-semibold text-text">{alert.message}</p>
                        <StatusBadge
                          status={alert.severity === 'critical' ? 'critical' : 'warning'}
                          label={alert.severity.toUpperCase()}
                          size="sm"
                          animated
                        />
                        {alert.acknowledged && (
                          <StatusBadge status="active" label="ACK" size="sm" animated={false} />
                        )}
                      </div>
                      <p className="text-xs text-text-muted">
                        {new Date(alert.created_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  {!alert.acknowledged && (
                    <button
                      onClick={() => handleAcknowledge(alert.id)}
                      className="ml-4 px-4 py-2 bg-primary/20 border border-primary/40 text-primary rounded-lg hover:bg-primary/30 transition-all font-semibold whitespace-nowrap"
                    >
                      Acknowledge
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </AdvancedChart>

      {/* Alert History */}
      <AdvancedChart 
        title="Alert History" 
        subtitle="Recent system events and acknowledgments"
        className="mt-6"
      >
        <DataTable
          columns={[
            {
              key: 'severity',
              label: 'Severity',
              render: (value: unknown) => (
                <StatusBadge
                  status={(value as string) === 'critical' ? 'critical' : 'warning'}
                  label={(value as string).toUpperCase()}
                  size="sm"
                  animated
                />
              ),
            },
            { key: 'message', label: 'Message' },
            {
              key: 'created_at',
              label: 'Created',
              render: (value: unknown) => new Date(value as string | number | Date).toLocaleString(),
            },
            {
              key: 'acknowledged',
              label: 'Status',
              render: (value: unknown) => (
                <StatusBadge
                  status={value ? 'active' : 'pending'}
                  label={value ? 'Acknowledged' : 'Pending'}
                  size="sm"
                />
              ),
            },
          ]}
          data={alerts.slice(0, 10)}
          keyExtractor={(alert: Alert) => String(alert.id)}
        />
      </AdvancedChart>
    </div>
  )
}
