import { useState, useEffect } from 'react'
import { wsClient, WebSocketData } from '@/lib/websocket'

interface ChartDataPoint {
  time: string
  z_rms: number
  x_rms: number
  z_accel: number
  x_accel: number
  temperature: number
  frequency: number
}

export function usePersistentData() {
  const [chartData, setChartData] = useState<ChartDataPoint[]>([])
  const [sensorData, setSensorData] = useState<any>({})
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Load persistent data on mount
    loadPersistentData()
    
    // Subscribe to WebSocket for real-time updates
    const unsubscribe = wsClient.subscribe((data: WebSocketData) => {
      if (data.sensor_data) {
        setSensorData(data.sensor_data)
        
        // Update chart data
        setChartData(prev => {
          const newPoint: ChartDataPoint = {
            time: data.timestamp || new Date().toISOString(),
            z_rms: data.sensor_data.z_rms || 0,
            x_rms: data.sensor_data.x_rms || 0,
            z_accel: data.sensor_data.z_accel || 0,
            x_accel: data.sensor_data.x_accel || 0,
            temperature: data.sensor_data.temperature || 0,
            frequency: data.sensor_data.frequency || 0
          }
          
          // Keep only last 100 points
          const updated = [...prev, newPoint]
          return updated.slice(-100)
        })
      }
      setIsLoading(false)
    })

    return () => unsubscribe()
  }, [])

  const loadPersistentData = async () => {
    try {
      // Load chart data from backend
      const response = await fetch('/api/v1/data/chart')
      if (response.ok) {
        const data = await response.json()
        setChartData(data || [])
      }
    } catch (error) {
      console.error('Failed to load persistent data:', error)
    } finally {
      setIsLoading(false)
    }
  }

  return {
    chartData,
    sensorData,
    isLoading,
    refreshData: loadPersistentData
  }
}
