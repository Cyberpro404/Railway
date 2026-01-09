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

export interface Threshold {
  id: number
  parameter: string
  warn_value: number
  alarm_value: number
  threshold_type: string
  axis?: string
  band_number?: number
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
  getAll: async (): Promise<Threshold[]> => {
    const response = await api.get('/thresholds')
    return response.data
  },
  
  get: async (parameter: string): Promise<Threshold> => {
    const response = await api.get(`/thresholds/${parameter}`)
    return response.data
  },
  
  create: async (threshold: Partial<Threshold>): Promise<Threshold> => {
    const response = await api.post('/thresholds', threshold)
    return response.data
  },
  
  update: async (parameter: string, threshold: Partial<Threshold>): Promise<Threshold> => {
    const response = await api.put(`/thresholds/${parameter}`, threshold)
    return response.data
  },
  
  delete: async (parameter: string) => {
    const response = await api.delete(`/thresholds/${parameter}`)
    return response.data
  },
  
  resetDefaults: async () => {
    const response = await api.post('/thresholds/reset-defaults')
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

