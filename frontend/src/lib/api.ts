/**
 * API client for backend communication
 */
import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface ThresholdConfig {
  id: string
  parameter: 'z_rms' | 'x_rms' | 'temperature' | 'z_accel' | 'x_accel' | 'kurtosis'
  parameterLabel: string
  unit: string
  minLimit: number
  maxLimit: number
}

export interface ControllerThresholdConfig {
  id: string
  parameter: 'z_rms' | 'x_rms' | 'temperature' | 'z_accel' | 'x_accel' | 'kurtosis'
  parameterLabel: string
  unit: string
  warningLimit: number
  alertLimit: number
}

export interface Alert {
  id: number
  alert_type: string
  severity: string
  message: string
  parameter?: string
  value?: number
  threshold?: number
  ml_confidence?: number
  acknowledged: boolean
  acknowledged_at?: string
  created_at: string
}

export interface ConnectionStatus {
  connected: boolean
  port: string | null
  baud: number
  slave_id: number
  uptime_seconds: number
  last_poll: string | null
  packet_loss: number
  auto_reconnect: boolean
}

export interface OfflineLogEntry {
  timestamp: string | null
  level: string
  source?: string
  message: string
  raw: string
}

export interface OfflineLogResponse {
  file: string
  count: number
  entries: OfflineLogEntry[]
}

export interface OfflineLogStats {
  file: string
  exists: boolean
  size_bytes: number
  size_mb: number
  line_count: number
  level_counts: Record<string, number>
  last_updated: string | null
}

// Connection API
export const connectionAPI = {
  getStatus: async (): Promise<ConnectionStatus> => {
    const response = await api.get('/connection/status')
    return response.data
  },
  
  scanPorts: async (): Promise<string[]> => {
    const response = await api.post('/connection/scan')
    return response.data.ports
  },
  
  connect: async (port: string, baud: number = 19200, slave_id: number = 1) => {
    const response = await api.post('/connection/connect', {
      port,
      baud,
      slave_id
    })
    return response.data
  },
  
  disconnect: async () => {
    const response = await api.post('/connection/disconnect')
    return response.data
  },
}

// Thresholds API
export const thresholdsAPI = {
  /** Fetch saved thresholds from backend (falls back to empty list). */
  getAll: async (): Promise<ThresholdConfig[]> => {
    const response = await api.get('/thresholds/get')
    return response.data?.thresholds ?? []
  },

  /** Persist the full threshold set. */
  saveAll: async (thresholds: ThresholdConfig[]): Promise<{ success: boolean; message?: string }> => {
    const response = await api.post('/thresholds/save', thresholds)
    return response.data
  },
}

export const controllerThresholdsAPI = {
  getAll: async (): Promise<ControllerThresholdConfig[]> => {
    const response = await api.get('/controller-thresholds/get')
    return response.data?.thresholds ?? []
  },
  saveAll: async (thresholds: ControllerThresholdConfig[]): Promise<{ success: boolean; message?: string }> => {
    const response = await api.post('/controller-thresholds/save', thresholds)
    return response.data
  },
}

// Alerts API
export const alertsAPI = {
  getAll: async (params?: { limit?: number; acknowledged?: boolean; severity?: string }): Promise<Alert[]> => {
    const response = await api.get('/alerts', { params })
    return response.data
  },
  
  getActive: async (): Promise<Alert[]> => {
    const response = await api.get('/alerts/active')
    return response.data
  },
  
  create: async (alert: Partial<Alert>): Promise<Alert> => {
    const response = await api.post('/alerts', alert)
    return response.data
  },
  
  acknowledge: async (alertId: number) => {
    const response = await api.post(`/alerts/${alertId}/acknowledge`)
    return response.data
  },
  
  delete: async (alertId: number) => {
    const response = await api.delete(`/alerts/${alertId}`)
    return response.data
  },
}

// Health API
export const healthAPI = {
  check: async () => {
    const response = await api.get('/health')
    return response.data
  },
}

// Logs API (offline file-backed)
export const logsAPI = {
  getOfflineLogs: async (params?: { file?: string; limit?: number; search?: string }): Promise<OfflineLogResponse> => {
    const response = await api.get('/logs/offline', { params })
    return response.data
  },
  getOfflineStats: async (file: string = 'app'): Promise<OfflineLogStats> => {
    const response = await api.get('/logs/offline/stats', { params: { file } })
    return response.data
  },
}

