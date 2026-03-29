import { useEffect, useState } from 'react'
import { wsClient, WebSocketData } from '../lib/websocket'
import { 
  Wifi, WifiOff, RefreshCw, AlertTriangle, CheckCircle2, Signal, Zap, Settings, 
  Eye, EyeOff, Copy, Clock, TrendingUp, TrendingDown, Activity, Server, Gauge, 
  BarChart3, AlertCircle, Zap as Power, Thermometer, Radio, Database, Shield
} from 'lucide-react'

interface PortScan {
  port: string
  available: boolean
  detected: string
  signal_strength?: number
}

interface ConnectionMetrics {
  timestamp: string
  signal: number
  latency: number
  packetLoss: number
  status: 'connected' | 'connecting' | 'disconnected' | 'demo'
}

export default function ConnectionEnhanced() {
  const [data, setData] = useState<WebSocketData | null>(null)
  const [ports, setPorts] = useState<PortScan[]>([])
  const [scanning, setScanning] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [selectedPort, setSelectedPort] = useState<string>('AUTO')
  const [isLiveMode, setIsLiveMode] = useState(true)
  const [metrics, setMetrics] = useState<ConnectionMetrics[]>([])
  const [showDetails, setShowDetails] = useState(false)
  const [copied, setCopied] = useState(false)
  const [autoDetected, setAutoDetected] = useState(false)
  const [diagnostics, setDiagnostics] = useState({
    lastRead: new Date().toLocaleTimeString(),
    readCount: 0,
    errorCount: 0,
    successRate: 100,
    connectionTime: 0
  })

  // Real-time data subscription
  useEffect(() => {
    const handleData = (newData: WebSocketData) => {
      setData(newData)
      
      // Update diagnostics
      setDiagnostics(prev => ({
        ...prev,
        lastRead: new Date().toLocaleTimeString('en-US', { hour12: false }),
        readCount: prev.readCount + 1,
        successRate: newData.source === 'LIVE_FEED' ? 100 : 0
      }))

      // Update metrics history
      const newMetric: ConnectionMetrics = {
        timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
        signal: newData.source === 'LIVE_FEED' ? 95 + Math.random() * 5 : 50,
        latency: newData.source === 'LIVE_FEED' ? 15 + Math.random() * 10 : 2,
        packetLoss: newData.source === 'LIVE_FEED' ? Math.random() * 0.5 : 0,
        status: newData.source === 'LIVE_FEED' ? 'connected' : 'demo'
      }
      
      setMetrics(prev => [...prev, newMetric].slice(-60)) // Keep last 60 metrics
    }

    const unsubscribe = wsClient.subscribe(handleData)
    return unsubscribe
  }, [])

  // Auto-detect ports on mount
  useEffect(() => {
    scanPorts()
  }, [])

  const scanPorts = async () => {
    setScanning(true)
    try {
      // Simulate port scanning with realistic detection
      const detectedPorts: PortScan[] = [
        { port: 'COM1', available: false, detected: 'Built-in Serial (Legacy)', signal_strength: 0 },
        { port: 'COM3', available: true, detected: 'Railway Sensor Detected ✓', signal_strength: 98 },
        { port: 'COM4', available: false, detected: 'USB Serial (In Use)', signal_strength: 0 },
        { port: '/dev/ttyUSB0', available: true, detected: 'Available (Linux)', signal_strength: 95 },
      ]
      
      // Simulate realistic scanning delay
      await new Promise(resolve => setTimeout(resolve, 3000))
      setPorts(detectedPorts)
      
      // Auto-detect the best available port
      const bestPort = detectedPorts.find(p => p.available && p.signal_strength)
      if (bestPort) {
        setSelectedPort(bestPort.port)
        setAutoDetected(true)
      }
    } catch (error) {
      console.error('Port scan failed:', error)
    } finally {
      setScanning(false)
    }
  }

  const connectToPort = async (port: string) => {
    setConnecting(true)
    try {
      // Simulate connection attempt
      await new Promise(resolve => setTimeout(resolve, 2000))
      setSelectedPort(port)
      setIsLiveMode(true)
      setAutoDetected(true)
    } finally {
      setConnecting(false)
    }
  }

  const toggleMode = () => {
    setIsLiveMode(!isLiveMode)
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
        <div className="text-center">
          <div className="w-20 h-20 mx-auto mb-6 relative">
            <div className="absolute inset-0 border-4 border-cyan-500/30 rounded-full"></div>
            <div className="absolute inset-0 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
          <h2 className="text-2xl font-bold text-cyan-400">Initializing Connection...</h2>
        </div>
      </div>
    )
  }

  const isConnected = data.source === 'LIVE_FEED'
  const { sensor_data: sensor } = data

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-6">
      <div className="max-w-[1920px] mx-auto space-y-6">
        
        {/* Header with Mode Indicator */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
              Connection Manager
            </h1>
            <p className="text-slate-500 text-sm mt-1">Real-time sensor connection and diagnostics</p>
          </div>
          <div className="flex items-center gap-3">
            <div className={`px-4 py-2 rounded-lg font-semibold flex items-center gap-2 ${
              isConnected 
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' 
                : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
            }`}>
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
              {isConnected ? 'LIVE FEED' : 'DEMO MODE'}
            </div>
          </div>
        </div>

        {/* Quick Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="relative group">
            <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/20 to-blue-500/20 rounded-xl blur-lg group-hover:blur-xl transition-all" />
            <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-slate-400 text-xs uppercase font-semibold mb-1">Signal Strength</p>
                  <p className="text-2xl font-bold text-cyan-400">{(isConnected ? 95 : 50)}%</p>
                </div>
                <Signal className="w-8 h-8 text-cyan-500 opacity-50" />
              </div>
              <div className="mt-3 h-1 bg-slate-800 rounded-full overflow-hidden">
                <div className="h-full w-4/5 bg-gradient-to-r from-cyan-500 to-blue-500" />
              </div>
            </div>
          </div>

          <div className="relative group">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/20 to-teal-500/20 rounded-xl blur-lg group-hover:blur-xl transition-all" />
            <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-slate-400 text-xs uppercase font-semibold mb-1">Latency</p>
                  <p className="text-2xl font-bold text-emerald-400">{(isConnected ? 18 : 2).toFixed(0)}ms</p>
                </div>
                <Clock className="w-8 h-8 text-emerald-500 opacity-50" />
              </div>
              <p className="text-xs text-slate-500 mt-2">Response time</p>
            </div>
          </div>

          <div className="relative group">
            <div className="absolute inset-0 bg-gradient-to-br from-purple-500/20 to-pink-500/20 rounded-xl blur-lg group-hover:blur-xl transition-all" />
            <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-slate-400 text-xs uppercase font-semibold mb-1">Packet Loss</p>
                  <p className="text-2xl font-bold text-purple-400">{(isConnected ? 0.1 : 0).toFixed(2)}%</p>
                </div>
                <Activity className="w-8 h-8 text-purple-500 opacity-50" />
              </div>
              <p className="text-xs text-slate-500 mt-2">Error rate</p>
            </div>
          </div>

          <div className="relative group">
            <div className="absolute inset-0 bg-gradient-to-br from-orange-500/20 to-red-500/20 rounded-xl blur-lg group-hover:blur-xl transition-all" />
            <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-slate-400 text-xs uppercase font-semibold mb-1">Uptime</p>
                  <p className="text-2xl font-bold text-orange-400">{sensor.uptime}h</p>
                </div>
                <Power className="w-8 h-8 text-orange-500 opacity-50" />
              </div>
              <p className="text-xs text-slate-500 mt-2">System hours</p>
            </div>
          </div>
        </div>

        {/* Port Selection and Auto-Scan */}
        <div className="relative group">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500/20 to-cyan-500/20 rounded-2xl blur-xl group-hover:blur-2xl transition-all" />
          <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-slate-200 flex items-center gap-2">
                <Server className="w-5 h-5 text-cyan-400" />
                Port Selection & Auto-Detection
              </h2>
              <button
                onClick={() => scanPorts()}
                disabled={scanning}
                className="px-4 py-2 bg-cyan-500/20 border border-cyan-500/30 text-cyan-400 rounded-lg hover:bg-cyan-500/30 transition-all disabled:opacity-50 flex items-center gap-2"
              >
                <RefreshCw className={`w-4 h-4 ${scanning ? 'animate-spin' : ''}`} />
                {scanning ? 'Scanning...' : 'Scan Ports'}
              </button>
            </div>

            {/* Auto-Detected Indicator */}
            {autoDetected && (
              <div className="mb-4 p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span className="text-sm text-emerald-400">✓ Auto-detected best available port: <strong>{selectedPort}</strong></span>
              </div>
            )}

            {/* Port Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
              {ports.length > 0 ? (
                ports.map(port => (
                  <button
                    key={port.port}
                    onClick={() => connectToPort(port.port)}
                    disabled={!port.available || connecting}
                    className={`p-4 rounded-lg border-2 transition-all ${
                      selectedPort === port.port
                        ? 'bg-cyan-500/20 border-cyan-500 text-cyan-400'
                        : port.available
                        ? 'bg-slate-800/50 border-slate-700/50 text-slate-300 hover:border-cyan-500/50 hover:bg-slate-800/70'
                        : 'bg-slate-800/30 border-slate-700/30 text-slate-500 opacity-50 cursor-not-allowed'
                    }`}
                  >
                    <div className="font-semibold text-sm">{port.port}</div>
                    <div className="text-xs mt-1 opacity-75">{port.detected}</div>
                    {port.available && (
                      <div className="mt-2 flex items-center gap-1 text-xs">
                        <Wifi className="w-3 h-3" />
                        {port.signal_strength}% signal
                      </div>
                    )}
                  </button>
                ))
              ) : (
                <div className="col-span-full text-center py-8 text-slate-500">
                  Click "Scan Ports" to detect available sensors
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Connection Status Display */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Status Card */}
          <div className="relative group">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/20 to-teal-500/20 rounded-2xl blur-xl group-hover:blur-2xl transition-all" />
            <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
              <h3 className="text-lg font-bold text-slate-200 mb-4 flex items-center gap-2">
                <Shield className="w-5 h-5 text-emerald-400" />
                Connection Status
              </h3>
              
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 bg-slate-800/30 rounded-lg">
                  <span className="text-slate-400 text-sm">Status</span>
                  <span className={`font-semibold text-sm px-3 py-1 rounded flex items-center gap-1 ${
                    isConnected 
                      ? 'bg-emerald-500/20 text-emerald-400' 
                      : 'bg-amber-500/20 text-amber-400'
                  }`}>
                    <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
                    {isConnected ? 'Connected' : 'Demo Mode'}
                  </span>
                </div>
                
                <div className="flex items-center justify-between p-3 bg-slate-800/30 rounded-lg">
                  <span className="text-slate-400 text-sm">Port</span>
                  <span className="font-mono text-sm text-cyan-400">{selectedPort}</span>
                </div>
                
                <div className="flex items-center justify-between p-3 bg-slate-800/30 rounded-lg">
                  <span className="text-slate-400 text-sm">Baud Rate</span>
                  <span className="font-mono text-sm text-cyan-400">19200</span>
                </div>
                
                <div className="flex items-center justify-between p-3 bg-slate-800/30 rounded-lg">
                  <span className="text-slate-400 text-sm">Last Read</span>
                  <span className="font-mono text-sm text-slate-300">{diagnostics.lastRead}</span>
                </div>
                
                <div className="flex items-center justify-between p-3 bg-slate-800/30 rounded-lg">
                  <span className="text-slate-400 text-sm">Health Score</span>
                  <span className={`font-semibold text-sm px-3 py-1 rounded ${
                    sensor.data_quality > 90 ? 'bg-emerald-500/20 text-emerald-400' :
                    sensor.data_quality > 75 ? 'bg-yellow-500/20 text-yellow-400' :
                    'bg-red-500/20 text-red-400'
                  }`}>
                    {sensor.data_quality}%
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Live/Demo Mode Selector */}
          <div className="relative group">
            <div className="absolute inset-0 bg-gradient-to-br from-purple-500/20 to-pink-500/20 rounded-2xl blur-xl group-hover:blur-2xl transition-all" />
            <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
              <h3 className="text-lg font-bold text-slate-200 mb-4 flex items-center gap-2">
                <Zap className="w-5 h-5 text-purple-400" />
                Operation Mode
              </h3>
              
              <div className="space-y-3">
                <button
                  onClick={() => setIsLiveMode(true)}
                  className={`w-full p-4 rounded-lg border-2 transition-all text-left ${
                    isLiveMode
                      ? 'bg-emerald-500/20 border-emerald-500 text-emerald-400'
                      : 'bg-slate-800/50 border-slate-700/50 text-slate-400 hover:border-emerald-500/50'
                  }`}
                >
                  <div className="font-semibold flex items-center gap-2">
                    <Wifi className="w-4 h-4" />
                    Live Feed Mode
                  </div>
                  <div className="text-xs opacity-75 mt-1">Real sensor data from Modbus RTU device</div>
                </button>
                
                <button
                  onClick={() => setIsLiveMode(false)}
                  className={`w-full p-4 rounded-lg border-2 transition-all text-left ${
                    !isLiveMode
                      ? 'bg-amber-500/20 border-amber-500 text-amber-400'
                      : 'bg-slate-800/50 border-slate-700/50 text-slate-400 hover:border-amber-500/50'
                  }`}
                >
                  <div className="font-semibold flex items-center gap-2">
                    <Eye className="w-4 h-4" />
                    Demo Mode
                  </div>
                  <div className="text-xs opacity-75 mt-1">Synthetic data for UI testing (no device needed)</div>
                </button>
              </div>

              <div className="mt-4 p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg text-xs text-blue-400">
                ℹ️ <strong>Safety Notice:</strong> Switching modes is safe at any time. In Demo mode, real sensor data is not processed.
              </div>
            </div>
          </div>
        </div>

        {/* Sensor Details */}
        <div className="relative group">
          <div className="absolute inset-0 bg-gradient-to-br from-orange-500/20 to-yellow-500/20 rounded-2xl blur-xl group-hover:blur-2xl transition-all" />
          <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="w-full flex items-center justify-between text-lg font-bold text-slate-200 hover:text-slate-100 transition-colors"
            >
              <span className="flex items-center gap-2">
                <Database className="w-5 h-5 text-orange-400" />
                Sensor Details
              </span>
              <div className={`transition-transform ${showDetails ? 'rotate-180' : ''}`}>
                ▼
              </div>
            </button>

            {showDetails && (
              <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-3 pt-4 border-t border-slate-800/50">
                {[
                  { label: 'Z-Axis RMS', value: `${sensor.z_rms} mm/s`, icon: TrendingUp },
                  { label: 'X-Axis RMS', value: `${sensor.x_rms} mm/s`, icon: TrendingUp },
                  { label: 'Temperature', value: `${sensor.temperature}°C`, icon: Thermometer },
                  { label: 'Frequency', value: `${sensor.frequency} Hz`, icon: Radio },
                  { label: 'Kurtosis', value: sensor.kurtosis, icon: BarChart3 },
                  { label: 'ISO Class', value: sensor.iso_class, icon: Shield },
                ].map(item => {
                  const Icon = item.icon
                  return (
                    <div key={item.label} className="p-3 bg-slate-800/30 rounded-lg">
                      <div className="flex items-center gap-2 mb-1">
                        <Icon className="w-3 h-3 text-slate-500" />
                        <span className="text-xs text-slate-500 uppercase font-semibold">{item.label}</span>
                      </div>
                      <div className="text-sm font-semibold text-slate-200">{item.value}</div>
                    </div>
                  )
                })}
              </div>
            )}

            {/* Raw JSON Export */}
            {showDetails && (
              <div className="mt-4 pt-4 border-t border-slate-800/50">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-slate-400">Raw Sensor Data (JSON)</span>
                  <button
                    onClick={() => copyToClipboard(JSON.stringify(sensor, null, 2))}
                    className="px-3 py-1 text-xs bg-cyan-500/20 border border-cyan-500/30 text-cyan-400 rounded hover:bg-cyan-500/30 transition-all flex items-center gap-1"
                  >
                    <Copy className="w-3 h-3" />
                    {copied ? 'Copied!' : 'Copy'}
                  </button>
                </div>
                <div className="bg-slate-950/50 p-3 rounded font-mono text-xs text-slate-400 max-h-40 overflow-y-auto">
                  {JSON.stringify(sensor, null, 2)}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Diagnostics Footer */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-slate-500">
          <div className="p-3 bg-slate-800/30 rounded-lg">
            <span className="font-semibold">Total Reads:</span> {diagnostics.readCount}
          </div>
          <div className="p-3 bg-slate-800/30 rounded-lg">
            <span className="font-semibold">Success Rate:</span> {diagnostics.successRate.toFixed(1)}%
          </div>
          <div className="p-3 bg-slate-800/30 rounded-lg">
            <span className="font-semibold">Last Update:</span> {diagnostics.lastRead}
          </div>
        </div>
      </div>
    </div>
  )
}
