import React, { useState, useEffect } from 'react'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import StatusBadge from '@/components/ui/StatusBadge'
import { 
  Activity, 
  Thermometer, 
  Zap, 
  TrendingUp, 
  Shield, 
  AlertTriangle, 
  CheckCircle, 
  XCircle,
  Database,
  Wifi,
  Clock,
  Gauge,
  Cpu,
  AlertCircle
} from 'lucide-react'

interface HealthStatus {
  overall_health: number
  connection_quality: number
  data_quality: number
  system_health: number
  anomaly_count: number
  uptime_percentage: number
  last_update: string | null
  circuit_state: string
  register_stats: Record<string, any>
  predictive_alerts: any[]
}

interface HealthDashboardProps {
  healthData: HealthStatus | null
  onRefresh?: () => void
}

export default function HealthDashboard({ healthData, onRefresh }: HealthDashboardProps) {
  const getHealthColor = (value: number) => {
    if (value >= 90) return 'text-green-500 bg-green-50 border-green-200'
    if (value >= 70) return 'text-yellow-500 bg-yellow-50 border-yellow-200'
    return 'text-red-500 bg-red-50 border-red-200'
  }

  const getHealthIcon = (value: number) => {
    if (value >= 90) return <CheckCircle className="w-5 h-5 text-green-500" />
    if (value >= 70) return <AlertTriangle className="w-5 h-5 text-yellow-500" />
    return <XCircle className="w-5 h-5 text-red-500" />
  }

  const formatTrend = (trend: number) => {
    if (Math.abs(trend) < 0.001) return '→ Stable'
    return trend > 0 ? `↗ Rising (+${trend.toFixed(4)})` : `↘ Falling (${trend.toFixed(4)})`
  }

  if (!healthData) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-text flex items-center gap-3">
            <Shield className="w-6 h-6 text-primary" />
            System Health Dashboard
          </h2>
          <p className="text-text-muted">Real-time system monitoring and analytics</p>
        </div>
        <Button onClick={onRefresh} variant="ghost" size="sm">
          <Activity className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Overall Health Score */}
      <Card className="p-6 bg-gradient-to-br from-background via-background to-background/50 backdrop-blur-sm border-0 shadow-2xl">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-text mb-2">Overall System Health</h3>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                {getHealthIcon(healthData.overall_health)}
                <span className="text-3xl font-bold" style={{ 
                  color: healthData.overall_health >= 90 ? '#22c55e' : 
                         healthData.overall_health >= 70 ? '#eab308' : '#dc2626' 
                }}>
                  {healthData.overall_health.toFixed(1)}%
                </span>
              </div>
              <div className="text-sm text-text-muted">
                <div>Circuit: {healthData.circuit_state}</div>
                <div>Uptime: {healthData.uptime_percentage.toFixed(1)}%</div>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Health Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Connection Quality */}
        <Card className={`p-4 border-2 ${getHealthColor(healthData.connection_quality)}`}>
          <div className="flex items-center gap-3 mb-3">
            <Wifi className="w-5 h-5" />
            <h4 className="font-semibold">Connection Quality</h4>
          </div>
          <div className="text-2xl font-bold mb-2">{healthData.connection_quality.toFixed(1)}%</div>
          <div className="text-sm opacity-80">Network reliability</div>
        </Card>

        {/* Data Quality */}
        <Card className={`p-4 border-2 ${getHealthColor(healthData.data_quality)}`}>
          <div className="flex items-center gap-3 mb-3">
            <Database className="w-5 h-5" />
            <h4 className="font-semibold">Data Quality</h4>
          </div>
          <div className="text-2xl font-bold mb-2">{healthData.data_quality.toFixed(1)}%</div>
          <div className="text-sm opacity-80">Signal integrity</div>
        </Card>

        {/* System Health */}
        <Card className={`p-4 border-2 ${getHealthColor(healthData.system_health)}`}>
          <div className="flex items-center gap-3 mb-3">
            <Cpu className="w-5 h-5" />
            <h4 className="font-semibold">System Health</h4>
          </div>
          <div className="text-2xl font-bold mb-2">{healthData.system_health.toFixed(1)}%</div>
          <div className="text-sm opacity-80">Parameter status</div>
        </Card>
      </div>

      {/* Register Statistics */}
      <Card className="p-6 bg-gradient-to-br from-background via-background to-background/50 backdrop-blur-sm border-0 shadow-2xl">
        <h3 className="text-lg font-semibold text-text mb-4 flex items-center gap-2">
          <Gauge className="w-5 h-5 text-primary" />
          Parameter Analytics
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.entries(healthData.register_stats).map(([key, stats]) => (
            <div key={key} className="p-3 bg-background/50 rounded-lg border border-border/30">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium text-sm capitalize">
                  {key.replace(/_/g, ' ')}
                </span>
                <StatusBadge status="pending" size="sm" label={formatTrend(stats.trend)} />
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div>
                  <div className="text-text-muted">Min</div>
                  <div className="font-mono">{stats.min === Infinity ? '---' : stats.min.toFixed(3)}</div>
                </div>
                <div>
                  <div className="text-text-muted">Avg</div>
                  <div className="font-mono">{stats.avg.toFixed(3)}</div>
                </div>
                <div>
                  <div className="text-text-muted">Max</div>
                  <div className="font-mono">{stats.max === -Infinity ? '---' : stats.max.toFixed(3)}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Anomalies and Alerts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Anomalies */}
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-5 h-5 text-yellow-500" />
            <h4 className="font-semibold">Anomaly Detection</h4>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold mb-2">{healthData.anomaly_count}</div>
            <div className="text-sm text-text-muted">Total anomalies detected</div>
          </div>
          {healthData.anomaly_count > 0 && (
            <div className="mt-3 p-2 bg-yellow-50 rounded-lg">
              <div className="text-xs text-yellow-700">
                ⚠️ {healthData.anomaly_count} anomalies detected in current session
              </div>
            </div>
          )}
        </Card>

        {/* Last Update */}
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <Clock className="w-5 h-5 text-primary" />
            <h4 className="font-semibold">System Status</h4>
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-text-muted">Last Update:</span>
              <span className="font-mono">
                {healthData.last_update ? new Date(healthData.last_update).toLocaleTimeString() : 'Never'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Predictive Alerts:</span>
              <span className="font-mono">{healthData.predictive_alerts.length}</span>
            </div>
          </div>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card className="p-4">
        <h4 className="font-semibold mb-3">Quick Actions</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <Button variant="ghost" size="sm" className="h-8">
            <Activity className="w-3 h-3 mr-1" />
            Diagnostics
          </Button>
          <Button variant="ghost" size="sm" className="h-8">
            <Database className="w-3 h-3 mr-1" />
            Export Data
          </Button>
          <Button variant="ghost" size="sm" className="h-8">
            <Shield className="w-3 h-3 mr-1" />
            Health Report
          </Button>
          <Button variant="ghost" size="sm" className="h-8">
            <AlertCircle className="w-3 h-3 mr-1" />
            View Alerts
          </Button>
        </div>
      </Card>
    </div>
  )
}
