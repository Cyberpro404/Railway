import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import Card from '@/components/ui/Card'
import { FadeIn } from '@/components/ui/AnimatedComponents'
import { X, TrendingUp, Activity, Thermometer, Zap } from 'lucide-react'
import { wsClient, WebSocketData } from '@/lib/websocket'

interface RegisterGraphPopupProps {
  register: {
    address: number
    name: string
    unit: string
    key: string
    color: string
    icon: React.ReactNode
  }
  data: any[]
  isOpen: boolean
  onClose: () => void
}

interface GraphDataPoint {
  time: string
  value: number
  timestamp: string
}

export default function RegisterGraphPopup({ register, data, isOpen, onClose }: RegisterGraphPopupProps) {
  const [graphData, setGraphData] = useState<GraphDataPoint[]>([])
  const [currentValue, setCurrentValue] = useState<number>(0)

  useEffect(() => {
    if (!isOpen) return

    const unsubscribe = wsClient.subscribe((data: WebSocketData) => {
      if (data.sensor_data && data.sensor_data[register.key as keyof typeof data.sensor_data]) {
        const value = Number(data.sensor_data[register.key as keyof typeof data.sensor_data])
        setCurrentValue(value)
        
        const timestamp = new Date(data.timestamp).toLocaleTimeString()
        const newPoint: GraphDataPoint = {
          time: timestamp,
          value: value,
          timestamp: data.timestamp
        }
        
        setGraphData(prev => {
          const updated = [...prev, newPoint]
          // Keep last 100 points
          return updated.slice(-100)
        })
      }
    })

    return unsubscribe
  }, [isOpen, register.key])

  const getIcon = () => {
    if (register.name.toLowerCase().includes('temperature')) return <Thermometer className="w-5 h-5" />
    if (register.name.toLowerCase().includes('frequency')) return <Zap className="w-5 h-5" />
    if (register.name.toLowerCase().includes('vibration') || register.name.toLowerCase().includes('rms')) return <Activity className="w-5 h-5" />
    return <TrendingUp className="w-5 h-5" />
  }

  const getColor = () => {
    if (register.name.toLowerCase().includes('temperature')) return '#ef4444'
    if (register.name.toLowerCase().includes('frequency')) return '#3b82f6'
    if (register.name.toLowerCase().includes('vibration') || register.name.toLowerCase().includes('rms')) return '#10b981'
    return '#8b5cf6'
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
      <FadeIn>
        <Card className="w-full max-w-4xl max-h-[80vh] overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-border/50">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-primary/10" style={{ color: getColor() }}>
                {getIcon()}
              </div>
              <div>
                <h3 className="text-xl font-semibold text-text">{register.name}</h3>
                <p className="text-sm text-text-muted">
                  Register {register.address} • {register.unit} • Current: {currentValue.toFixed(2)} {register.unit}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-card/50 transition-colors"
            >
              <X className="w-5 h-5 text-text-muted" />
            </button>
          </div>

          {/* Chart */}
          <div className="p-6">
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={graphData} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" strokeOpacity={0.25} />
                  <XAxis
                    dataKey="time"
                    stroke="#9ca3af"
                    tick={{ fontSize: 12 }}
                    tickLine={{ stroke: '#374151' }}
                  />
                  <YAxis
                    stroke="#9ca3af"
                    tick={{ fontSize: 12 }}
                    tickLine={{ stroke: '#374151' }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgba(31, 41, 55, 0.95)',
                      border: '1px solid #374151',
                      borderRadius: '12px',
                      backdropFilter: 'blur(10px)',
                      boxShadow: '0 10px 30px rgba(0, 0, 0, 0.3)'
                    }}
                    labelStyle={{ color: '#f3f4f6', fontWeight: 'bold' }}
                    itemStyle={{ padding: '4px 0' }}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke={getColor()}
                    strokeWidth={3}
                    dot={{ r: 3, fill: '#0b1021', stroke: getColor(), strokeWidth: 2 }}
                    activeDot={{ r: 5, strokeWidth: 0 }}
                    name={register.name}
                    animationDuration={400}
                    animationEasing="ease-in-out"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Statistics */}
          <div className="p-6 border-t border-border/50">
            <div className="grid grid-cols-4 gap-4">
              <div className="text-center">
                <p className="text-sm text-text-muted mb-1">Current</p>
                <p className="text-lg font-semibold text-text">{currentValue.toFixed(2)} {register.unit}</p>
              </div>
              <div className="text-center">
                <p className="text-sm text-text-muted mb-1">Average</p>
                <p className="text-lg font-semibold text-text">
                  {graphData.length > 0 ? (graphData.reduce((sum, d) => sum + d.value, 0) / graphData.length).toFixed(2) : '0.00'} {register.unit}
                </p>
              </div>
              <div className="text-center">
                <p className="text-sm text-text-muted mb-1">Min</p>
                <p className="text-lg font-semibold text-text">
                  {graphData.length > 0 ? Math.min(...graphData.map(d => d.value)).toFixed(2) : '0.00'} {register.unit}
                </p>
              </div>
              <div className="text-center">
                <p className="text-sm text-text-muted mb-1">Max</p>
                <p className="text-lg font-semibold text-text">
                  {graphData.length > 0 ? Math.max(...graphData.map(d => d.value)).toFixed(2) : '0.00'} {register.unit}
                </p>
              </div>
            </div>
          </div>
        </Card>
      </FadeIn>
    </div>
  )
}
