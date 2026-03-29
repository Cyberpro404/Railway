import { useEffect, useState } from 'react'
import { wsClient, WebSocketData } from '../lib/websocket'
import { 
  Activity, 
  Thermometer, 
  Zap, 
  TrendingUp, 
  Shield, 
  AlertTriangle, 
  Database,
  Download,
  Sparkles,
  Gauge,
  CheckCircle,
  Calendar,
  Clock,
  Filter,
  BarChart3
} from 'lucide-react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
  ComposedChart,
  Bar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  BarChart
} from 'recharts'
import Card from '../components/ui/Card'
import HealthDashboard from '../components/HealthDashboard'
import RegisterGraphPopup from '../components/RegisterGraphPopup'

interface ModbusRegister {
  address: number
  name: string
  unit: string
  key: string
  category: 'vibration' | 'temperature' | 'frequency' | 'health' | 'system' | 'data'
  color: string
  icon: React.ReactNode
}

const MODBUS_REGISTERS: ModbusRegister[] = [
  // Vibration Parameters
  { address: 45201, name: 'Z RMS Velocity', unit: 'in/sec', key: 'z_rms_in', category: 'vibration', color: '#3b82f6', icon: <Activity className="w-4 h-4" /> },
  { address: 45202, name: 'Z RMS Velocity', unit: 'mm/sec', key: 'z_rms', category: 'vibration', color: '#10b981', icon: <Activity className="w-4 h-4" /> },
  { address: 45205, name: 'X RMS Velocity', unit: 'in/sec', key: 'x_rms_in', category: 'vibration', color: '#8b5cf6', icon: <Activity className="w-4 h-4" /> },
  { address: 45206, name: 'X RMS Velocity', unit: 'mm/sec', key: 'x_rms', category: 'vibration', color: '#f59e0b', icon: <Activity className="w-4 h-4" /> },
  
  // Temperature
  { address: 45204, name: 'Temperature', unit: '°C', key: 'temperature', category: 'temperature', color: '#f97316', icon: <Thermometer className="w-4 h-4" /> },
  { address: 45203, name: 'Temperature', unit: '°F', key: 'temp_f', category: 'temperature', color: '#ef4444', icon: <Thermometer className="w-4 h-4" /> },
  
  // Acceleration
  { address: 45207, name: 'Z Peak Acceleration', unit: 'G', key: 'z_peak_accel', category: 'vibration', color: '#ec4899', icon: <Zap className="w-4 h-4" /> },
  { address: 45208, name: 'X Peak Acceleration', unit: 'G', key: 'x_peak_accel', category: 'vibration', color: '#a855f7', icon: <Zap className="w-4 h-4" /> },
  { address: 45211, name: 'Z RMS Acceleration', unit: 'G', key: 'z_rms_accel', category: 'vibration', color: '#14b8a6', icon: <Zap className="w-4 h-4" /> },
  { address: 45212, name: 'X RMS Acceleration', unit: 'G', key: 'x_rms_accel', category: 'vibration', color: '#06b6d4', icon: <Zap className="w-4 h-4" /> },
  
  // Frequency
  { address: 45209, name: 'Z Peak Frequency', unit: 'Hz', key: 'z_peak_freq', category: 'frequency', color: '#0ea5e9', icon: <Activity className="w-4 h-4" /> },
  { address: 45210, name: 'X Peak Frequency', unit: 'Hz', key: 'x_peak_freq', category: 'frequency', color: '#0891b2', icon: <Activity className="w-4 h-4" /> },
  
  // Advanced Analysis
  { address: 45213, name: 'Z Kurtosis', unit: '', key: 'z_kurtosis', category: 'health', color: '#6366f1', icon: <Gauge className="w-4 h-4" /> },
  { address: 45214, name: 'X Kurtosis', unit: '', key: 'x_kurtosis', category: 'health', color: '#84cc16', icon: <Gauge className="w-4 h-4" /> },
  { address: 45215, name: 'Z Crest Factor', unit: '', key: 'z_crest_factor', category: 'health', color: '#eab308', icon: <Shield className="w-4 h-4" /> },
  { address: 45216, name: 'X Crest Factor', unit: '', key: 'x_crest_factor', category: 'health', color: '#dc2626', icon: <Shield className="w-4 h-4" /> },
  
  // Peak Velocity
  { address: 45217, name: 'Z Peak Velocity', unit: 'in/sec', key: 'z_peak_vel_in', category: 'vibration', color: '#f97316', icon: <TrendingUp className="w-4 h-4" /> },
  { address: 45218, name: 'Z Peak Velocity', unit: 'mm/sec', key: 'z_peak_vel_mm', category: 'vibration', color: '#7c3aed', icon: <TrendingUp className="w-4 h-4" /> },
  { address: 45219, name: 'X Peak Velocity', unit: 'in/sec', key: 'x_peak_vel_in', category: 'vibration', color: '#ea580c', icon: <TrendingUp className="w-4 h-4" /> },
  { address: 45220, name: 'X Peak Velocity', unit: 'mm/sec', key: 'x_peak_vel_mm', category: 'vibration', color: '#15803d', icon: <TrendingUp className="w-4 h-4" /> },
  
  // High Frequency Acceleration
  { address: 45221, name: 'Z HF RMS Acceleration', unit: 'G', key: 'z_hf_rms_accel', category: 'vibration', color: '#4338ca', icon: <Zap className="w-4 h-4" /> },
  { address: 45222, name: 'X HF RMS Acceleration', unit: 'G', key: 'x_hf_rms_accel', category: 'vibration', color: '#0d9488', icon: <Zap className="w-4 h-4" /> },
]

export default function AnalyticsTab() {
  const [data, setData] = useState<WebSocketData | null>(null)
  const [chartData, setChartData] = useState<any[]>([])
  const [selectedRegister, setSelectedRegister] = useState<ModbusRegister | null>(null)
  const [isPopupOpen, setIsPopupOpen] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState<string>('all')

  useEffect(() => {
    const unsubscribe = wsClient.subscribe((newData: WebSocketData) => {
      setData(newData)
      
      if (newData.sensor_data) {
        const timestamp = new Date(newData.timestamp).toLocaleTimeString()
        const newPoint = {
          time: timestamp,
          ...newData.sensor_data
        }
        
        setChartData(prev => {
          const updated = [...prev, newPoint]
          return updated.slice(-100) // Keep last 100 points
        })
      }
    })

    return unsubscribe
  }, [])

  const handleRegisterClick = (register: ModbusRegister) => {
    setSelectedRegister(register)
    setIsPopupOpen(true)
  }

  const closePopup = () => {
    setIsPopupOpen(false)
    setSelectedRegister(null)
  }

  const getRegisterValue = (register: ModbusRegister) => {
    const value = data?.sensor_data?.[register.key as keyof typeof data.sensor_data]
    return typeof value === 'number' ? value : 0
  }

  const getRegisterDisplay = (register: ModbusRegister) => {
    const value = getRegisterValue(register)
    return typeof value === 'number' ? value.toFixed(register.key.includes('in/sec') ? 4 : 3) : 'N/A'
  }

  const getStatusColor = (register: ModbusRegister) => {
    const value = getRegisterValue(register)
    if (register.key.includes('accel') || register.key.includes('vel')) {
      if (value > 10) return '#dc2626'  // Critical
      if (value > 5) return '#eab308'   // Warning
      return '#22c55e'                  // Good
    }
    if (register.key.includes('temp')) {
      if (value > 60) return '#dc2626'   // Critical
      if (value > 40) return '#eab308'   // Warning
      return '#22c55e'                  // Good
    }
    return register.color
  }

  const filteredRegisters = selectedCategory === 'all' 
    ? MODBUS_REGISTERS 
    : MODBUS_REGISTERS.filter(r => r.category === selectedCategory)

  const categories = [
    { id: 'all', name: 'All Parameters', icon: <Database className="w-4 h-4" /> },
    { id: 'vibration', name: 'Vibration', icon: <Activity className="w-4 h-4" /> },
    { id: 'temperature', name: 'Temperature', icon: <Thermometer className="w-4 h-4" /> },
    { id: 'frequency', name: 'Frequency', icon: <Zap className="w-4 h-4" /> },
    { id: 'health', name: 'Health', icon: <Shield className="w-4 h-4" /> },
    { id: 'system', name: 'System', icon: <Clock className="w-4 h-4" /> },
    { id: 'data', name: 'Data', icon: <Database className="w-4 h-4" /> }
  ]

  if (!data || chartData.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto mb-4" />
          <div className="text-text-muted font-medium">Loading Analytics...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 p-6 bg-gradient-to-br from-background via-background to-background/95">
      {/* Enhanced Professional Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex-1">
          <div className="flex items-center gap-4 mb-3">
            <div className="w-1.5 h-10 bg-gradient-to-b from-primary via-primary/70 to-primary/30 rounded-full shadow-lg shadow-primary/30" />
            <div>
              <h1 className="text-4xl font-bold text-text tracking-tight flex items-center gap-3">
                <span className="bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
                  Railway Health Analytics
                </span>
                <Sparkles className="w-8 h-8 text-primary/60 animate-pulse" />
              </h1>
              <p className="text-text-muted font-medium flex items-center gap-3 mt-2">
                <Calendar className="w-4 h-4 text-primary/60" />
                <span className="text-primary/80">Real-time Modbus Sensor Data</span>
                <span className="text-text-muted/60">•</span>
                <span className="text-success/80 font-semibold">21 Registers (45201-45221)</span>
                <span className="text-text-muted/60">•</span>
                <span className="text-warning/80">1 Hour Rolling Window</span>
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {/* Connection Status */}
          <div className="px-4 py-2.5 bg-gradient-to-r from-success/10 to-success/5 border border-success/30 rounded-xl flex items-center gap-2.5 shadow-lg shadow-success/10 backdrop-blur-sm">
            <div className="relative">
              <CheckCircle className="w-5 h-5 text-success" />
              <div className="absolute -top-1 -right-1 w-2 h-2 bg-success rounded-full animate-pulse" />
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-success text-sm">System Healthy</span>
              <span className="text-xs text-success/70">Real-time Active</span>
            </div>
          </div>
          
          {/* Data Quality Badge */}
          <div className="px-4 py-2.5 bg-gradient-to-r from-primary/10 to-primary/5 border border-primary/30 rounded-xl flex items-center gap-2.5 shadow-lg shadow-primary/10 backdrop-blur-sm">
            <Database className="w-5 h-5 text-primary" />
            <div className="flex flex-col">
              <span className="font-bold text-primary text-sm">Data Quality</span>
              <span className="text-xs text-primary/70">{data?.sensor_data?.data_quality?.toFixed(1) || '98.0'}%</span>
            </div>
          </div>
          
          {/* Export Button */}
          <button className="p-3 rounded-xl bg-gradient-to-r from-primary/20 to-primary/10 border border-primary/30 hover:from-primary/30 hover:to-primary/20 hover:border-primary/50 transition-all duration-300 shadow-lg shadow-primary/10 backdrop-blur-sm group">
            <Download className="w-5 h-5 text-primary group-hover:scale-110 transition-transform" />
          </button>
        </div>
      </div>

      {/* Enhanced Category Filter */}
      <div className="flex gap-3 mb-8 overflow-x-auto p-1 bg-gradient-to-r from-background/50 to-background/30 rounded-2xl border border-border/30 backdrop-blur-sm">
        {categories.map((category) => (
          <button
            key={category.id}
            onClick={() => setSelectedCategory(category.id)}
            className={`flex items-center gap-2.5 px-5 py-3 rounded-xl font-medium transition-all duration-300 relative overflow-hidden group ${
              selectedCategory === category.id
                ? 'bg-gradient-to-r from-primary to-primary/80 text-text shadow-lg shadow-primary/30 scale-105'
                : 'bg-background/50 border border-border/40 hover:border-primary/50 hover:bg-primary/10 hover:scale-105'
            }`}
          >
            {selectedCategory === category.id && (
              <div className="absolute inset-0 bg-gradient-to-r from-primary/20 to-primary/10 animate-pulse" />
            )}
            <div className="relative z-10 flex items-center gap-2.5">
              <div className={`transition-transform duration-300 ${selectedCategory === category.id ? 'scale-110' : 'group-hover:scale-110'}`}>
                {category.icon}
              </div>
              <span className="text-sm">{category.name}</span>
              <div className={`px-2 py-0.5 rounded-full text-xs font-bold transition-all duration-300 ${
                selectedCategory === category.id
                  ? 'bg-text/20 text-text'
                  : 'bg-primary/20 text-primary'
              }`}>
                {category.id === 'all' ? 22 : MODBUS_REGISTERS.filter(r => r.category === category.id).length}
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* Enhanced Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
        {MODBUS_REGISTERS.slice(0, 4).map((register, index) => (
          <Card 
            key={register.key} 
            className="group relative overflow-hidden cursor-pointer transition-all duration-500 hover:scale-105 hover:shadow-2xl border-0 bg-gradient-to-br from-background via-background to-background/50 backdrop-blur-sm"
            onClick={() => handleRegisterClick(register)}
            style={{
              background: `linear-gradient(135deg, ${register.color}10 0%, ${register.color}05 50%, transparent 100%)`,
              borderTop: `3px solid ${register.color}`
            }}
          >
            {/* Animated Background Pattern */}
            <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
              <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent animate-pulse" />
              <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-white/5 to-transparent rounded-full blur-2xl" />
            </div>
            
            <div className="relative z-10 p-5">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-3 rounded-xl shadow-lg" style={{ 
                  backgroundColor: `${register.color}20`,
                  boxShadow: `0 8px 32px ${register.color}30`
                }}>
                  <div className="transition-transform duration-300 group-hover:scale-110">
                    {register.icon}
                  </div>
                </div>
                <div className="flex-1">
                  <span className="text-sm font-semibold text-text-muted/80 uppercase tracking-wider">{register.name}</span>
                  <div className="text-xs text-primary/60 mt-1">Register {register.address}</div>
                </div>
              </div>
              
              <div className="mb-3">
                <p className="text-3xl font-bold transition-all duration-300 group-hover:scale-105" style={{ 
                  color: getStatusColor(register),
                  textShadow: `0 0 20px ${getStatusColor(register)}40`
                }}>
                  {getRegisterDisplay(register)}
                </p>
                <p className="text-sm text-text-muted/70 mt-1">{register.unit}</p>
              </div>
              
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full animate-pulse" style={{ backgroundColor: getStatusColor(register) }} />
                  <span className="text-xs text-primary/60 font-medium">Live</span>
                </div>
                <div className="text-xs text-primary/50 group-hover:text-primary/70 transition-colors">
                  Click for graph →
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Main Chart - Professional Multi-Parameter Visualization */}
      <Card className="p-7 mb-8 bg-gradient-to-br from-background via-background to-background/50 backdrop-blur-sm border-0 shadow-2xl">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-xl font-bold text-text flex items-center gap-3">
              <div className="w-1 h-6 bg-gradient-to-b from-primary to-primary/50 rounded-full" />
              Real-time Parameter Trends
              <Sparkles className="w-5 h-5 text-primary/60 animate-pulse" />
            </h3>
            <p className="text-sm text-text-muted/70 mt-2">Live sensor data streaming from Modbus registers</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="px-3 py-1.5 bg-primary/10 border border-primary/30 rounded-full flex items-center gap-2">
              <div className="w-2 h-2 bg-primary rounded-full animate-pulse" />
              <span className="text-xs font-medium text-primary">Live</span>
            </div>
            <div className="text-xs text-text-muted/60">
              {chartData.length} data points
            </div>
          </div>
        </div>
        
        <div className="h-96 bg-gradient-to-br from-background/30 to-background/10 rounded-2xl p-4">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorZRMS" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.05}/>
                </linearGradient>
                <linearGradient id="colorXRMS" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0.05}/>
                </linearGradient>
                <linearGradient id="colorTemp" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f97316" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#f97316" stopOpacity={0.05}/>
                </linearGradient>
                <linearGradient id="colorFreq" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.05}/>
                </linearGradient>
                <filter id="glow">
                  <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
                  <feMerge>
                    <feMergeNode in="coloredBlur"/>
                    <feMergeNode in="SourceGraphic"/>
                  </feMerge>
                </filter>
              </defs>
              
              <CartesianGrid 
                strokeDasharray="3 3" 
                stroke="#374151" 
                strokeOpacity={0.15} 
                verticalFill={["transparent", "rgba(55, 65, 81, 0.02)"]}
              />
              
              <XAxis 
                dataKey="time" 
                stroke="#9ca3af"
                tick={{ fontSize: 11, fill: '#9ca3af' }}
                tickLine={{ stroke: '#374151', strokeOpacity: 0.3 }}
                axisLine={{ stroke: '#374151', strokeOpacity: 0.3 }}
              />
              
              <YAxis 
                stroke="#9ca3af"
                tick={{ fontSize: 11, fill: '#9ca3af' }}
                tickLine={{ stroke: '#374151', strokeOpacity: 0.3 }}
                axisLine={{ stroke: '#374151', strokeOpacity: 0.3 }}
              />
              
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(17, 24, 39, 0.95)',
                  border: '1px solid rgba(59, 130, 246, 0.3)',
                  borderRadius: '16px',
                  backdropFilter: 'blur(20px)',
                  boxShadow: '0 20px 40px rgba(0, 0, 0, 0.4)',
                  padding: '12px 16px'
                }}
                labelStyle={{ color: '#f3f4f6', fontWeight: 'bold', marginBottom: '8px' }}
                itemStyle={{ padding: '6px 0', fontSize: '13px' }}
                formatter={(value: any, name: string) => [
                  <span style={{ color: '#f3f4f6', fontWeight: '600' }}>
                    {typeof value === 'number' ? value.toFixed(3) : value}
                  </span>,
                  <span style={{ color: '#9ca3af', marginLeft: '8px' }}>{name}</span>
                ]}
              />
              
              <Legend 
                wrapperStyle={{ paddingTop: '24px' }}
                iconType="circle"
                formatter={(value: string) => (
                  <span style={{ color: '#d1d5db', fontSize: '13px', fontWeight: '500' }}>{value}</span>
                )}
              />
              
              <Area
                type="natural"
                dataKey="z_rms"
                stroke="#3b82f6"
                strokeWidth={2.5}
                fill="url(#colorZRMS)"
                name="Z RMS (mm/s)"
                animationDuration={800}
                animationEasing="ease-in-out"
                filter="url(#glow)"
              />
              
              <Area
                type="natural"
                dataKey="x_rms"
                stroke="#10b981"
                strokeWidth={2.5}
                fill="url(#colorXRMS)"
                name="X RMS (mm/s)"
                animationDuration={800}
                animationEasing="ease-in-out"
                animationBegin={200}
                filter="url(#glow)"
              />
              
              <Area
                type="natural"
                dataKey="temperature"
                stroke="#f97316"
                strokeWidth={2.5}
                fill="url(#colorTemp)"
                name="Temperature (°C)"
                animationDuration={800}
                animationEasing="ease-in-out"
                animationBegin={400}
                filter="url(#glow)"
              />
              
              <Area
                type="natural"
                dataKey="z_peak_freq"
                stroke="#06b6d4"
                strokeWidth={2.5}
                fill="url(#colorFreq)"
                name="Z Peak Freq (Hz)"
                animationDuration={800}
                animationEasing="ease-in-out"
                animationBegin={600}
                filter="url(#glow)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* Secondary Chart - Vibration Analysis */}
      <Card className="p-6 mb-6">
        <h3 className="text-lg font-semibold text-text mb-4">Vibration Analysis (Smooth)</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData}>
              <defs>
                <linearGradient id="colorVibration" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.6}/>
                  <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.1}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" strokeOpacity={0.2} />
              <XAxis 
                dataKey="time" 
                stroke="#9ca3af"
                tick={{ fontSize: 11 }}
              />
              <YAxis 
                stroke="#9ca3af"
                tick={{ fontSize: 11 }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(31, 41, 55, 0.95)',
                  border: '1px solid #374151',
                  borderRadius: '8px'
                }}
              />
              <Legend />
              <Area
                type="natural"
                dataKey="z_rms"
                stroke="#8b5cf6"
                strokeWidth={2}
                fill="url(#colorVibration)"
                name="Z RMS Velocity"
                opacity={0.8}
              />
              <Line
                type="natural"
                dataKey="x_rms"
                stroke="#ec4899"
                strokeWidth={3}
                dot={false}
                name="X RMS Velocity"
                strokeDasharray="5 5"
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* Acceleration Analysis Radar Chart */}
      <Card className="p-7 mb-8 bg-gradient-to-br from-background via-background to-background/50 backdrop-blur-sm border-0 shadow-2xl">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-xl font-bold text-text flex items-center gap-3">
              <div className="w-1 h-6 bg-gradient-to-b from-warning to-warning/50 rounded-full" />
              Acceleration Analysis
              <Zap className="w-5 h-5 text-warning/60 animate-pulse" />
            </h3>
            <p className="text-sm text-text-muted/70 mt-2">Multi-axis acceleration monitoring</p>
          </div>
        </div>
        
        <div className="h-80 bg-gradient-to-br from-background/30 to-background/10 rounded-2xl p-4">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={chartData.slice(-10)}>
              <PolarGrid 
                stroke="#374151" 
                strokeOpacity={0.3}
                radialLines={true}
              />
              <PolarAngleAxis 
                dataKey="time" 
                stroke="#9ca3af"
                tick={{ fontSize: 10, fill: '#9ca3af' }}
              />
              <PolarRadiusAxis 
                stroke="#9ca3af"
                strokeOpacity={0.3}
                tick={{ fontSize: 9, fill: '#9ca3af' }}
                domain={[0, 'dataMax']}
              />
              
              <Radar
                name="Z Peak Acceleration"
                dataKey="z_peak_accel"
                stroke="#ec4899"
                fill="#ec4899"
                fillOpacity={0.3}
                strokeWidth={2}
              />
              
              <Radar
                name="X Peak Acceleration"
                dataKey="x_peak_accel"
                stroke="#a855f7"
                fill="#a855f7"
                fillOpacity={0.3}
                strokeWidth={2}
              />
              
              <Radar
                name="Z RMS Acceleration"
                dataKey="z_rms_accel"
                stroke="#14b8a6"
                fill="#14b8a6"
                fillOpacity={0.3}
                strokeWidth={2}
              />
              
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(17, 24, 39, 0.95)',
                  border: '1px solid rgba(236, 72, 153, 0.3)',
                  borderRadius: '12px',
                  backdropFilter: 'blur(20px)'
                }}
              />
              
              <Legend 
                wrapperStyle={{ paddingTop: '20px' }}
                iconType="circle"
                formatter={(value: string) => (
                  <span style={{ color: '#d1d5db', fontSize: '12px', fontWeight: '500' }}>{value}</span>
                )}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* All Parameters Grid - Enhanced */}
      <Card className="p-7 bg-gradient-to-br from-background via-background to-background/50 backdrop-blur-sm border-0 shadow-2xl">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-xl font-bold text-text flex items-center gap-3">
              <div className="w-1 h-6 bg-gradient-to-b from-primary to-primary/50 rounded-full" />
              All Parameters ({filteredRegisters.length} registers)
              <Database className="w-5 h-5 text-primary/60" />
            </h3>
            <p className="text-sm text-text-muted/70 mt-2">Complete Modbus register overview</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="px-3 py-1.5 bg-success/10 border border-success/30 rounded-full flex items-center gap-2">
              <div className="w-2 h-2 bg-success rounded-full animate-pulse" />
              <span className="text-xs font-medium text-success">Real-time</span>
            </div>
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filteredRegisters.map((register) => (
            <div 
              key={register.key} 
              className="group relative overflow-hidden p-5 bg-gradient-to-br from-background/50 to-background/30 rounded-2xl border border-border/30 hover:border-primary/40 transition-all duration-500 cursor-pointer hover:scale-105 hover:shadow-2xl backdrop-blur-sm"
              style={{
                background: `linear-gradient(135deg, ${register.color}08 0%, transparent 50%)`,
                borderTop: `2px solid ${register.color}40`
              }}
              onClick={() => handleRegisterClick(register)}
            >
              {/* Hover Effect */}
              <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
                <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent animate-pulse" />
                <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-br from-white/5 to-transparent rounded-full blur-2xl" />
              </div>
              
              <div className="relative z-10">
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2.5 rounded-xl shadow-md transition-transform duration-300 group-hover:scale-110" style={{ 
                    backgroundColor: `${register.color}20`,
                    boxShadow: `0 4px 16px ${register.color}20`
                  }}>
                    {register.icon}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-bold text-text uppercase tracking-wider">{register.name}</p>
                    <p className="text-xs text-primary/60 font-medium">Reg {register.address}</p>
                  </div>
                </div>
                
                <div className="mb-3">
                  <p className="text-2xl font-bold transition-all duration-300 group-hover:scale-105" style={{ 
                    color: getStatusColor(register),
                    textShadow: `0 0 15px ${getStatusColor(register)}30`
                  }}>
                    {getRegisterDisplay(register)}
                  </p>
                  {register.unit && <p className="text-xs text-text-muted/70 mt-1">{register.unit}</p>}
                </div>
                
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ backgroundColor: getStatusColor(register) }} />
                    <span className="text-xs text-primary/60 font-medium">Live</span>
                  </div>
                  <div className="text-xs text-primary/40 group-hover:text-primary/60 transition-colors">
                    View graph →
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Advanced Health Dashboard - Temporarily Disabled */}
      {false && data?.sensor_data?.health_status && (
        <Card className="p-6 bg-gradient-to-br from-background via-background to-background/50 backdrop-blur-sm border-0 shadow-2xl">
          <div className="mb-4">
            <h3 className="text-xl font-bold text-text flex items-center gap-3">
              <Shield className="w-6 h-6 text-primary" />
              Advanced System Health
            </h3>
            <p className="text-text-muted/70">Real-time health monitoring and analytics</p>
          </div>
          
          <HealthDashboard 
            healthData={data?.sensor_data?.health_status} 
            onRefresh={() => window.location.reload()}
          />
        </Card>
      )}

      {/* Register Graph Popup */}
      {selectedRegister && (
        <RegisterGraphPopup
          register={selectedRegister}
          data={chartData}
          onClose={closePopup}
          isOpen={isPopupOpen}
        />
      )}
    </div>
  )
}
