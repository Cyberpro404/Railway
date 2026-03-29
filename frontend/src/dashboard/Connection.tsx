import { useEffect, useState } from 'react'
import { wsClient, WebSocketData } from '../lib/websocket'
import { 
  Wifi, WifiOff, RefreshCw, AlertTriangle, CheckCircle2, Signal, Zap, Settings, 
  Eye, EyeOff, Copy, Clock, TrendingUp, TrendingDown, Activity, Server, Gauge, 
  BarChart3, AlertCircle, Zap as Power, Thermometer, Radio, Database, Shield
} from 'lucide-react'

interface SensorPort {
  port: string
  available: boolean
  detected?: string
}

export default function ConnectionTab() {
  const [data, setData] = useState<WebSocketData | null>(null)
  const [ports, setPorts] = useState<SensorPort[]>([])
  const [selectedPort, setSelectedPort] = useState<string>('COM3')
  const [scanning, setScanning] = useState(false)
  const [isLiveMode, setIsLiveMode] = useState(true)
  const [connectionHistory, setConnectionHistory] = useState<any[]>([])
  const [showDetails, setShowDetails] = useState(false)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    const handleData = (newData: WebSocketData) => {
      setData(newData)
      
      setConnectionHistory(prev => {
        const new_entry = {
          time: new Date().toLocaleTimeString('en-US', { hour12: false }),
          status: newData.sensor_data.alarm_status,
          signal: 92 + Math.random() * 8,
          latency: (Math.random() * 30 + 15).toFixed(1)
        }
        return [...prev, new_entry].slice(-100)
      })
    }

    const unsubscribe = wsClient.subscribe(handleData)
    return unsubscribe
  }, [])

  const scanPorts = async () => {
    setScanning(true)
    try {
      const response = await fetch('http://localhost:8000/api/v1/connection/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      const result = await response.json()
      const portList = result.ports?.map((p: string) => ({
        port: p,
        available: true,
        detected: 'Available'
      })) || []
      setPorts(portList)
    } catch (error) {
      console.error('Scan error:', error)
    }
    setScanning(false)
  }

  const autoDetectPort = async () => {
    setScanning(true)
    try {
      const response = await fetch('http://localhost:8000/api/v1/connection/auto-detect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      const result = await response.json()
      
      if (result.success && result.port) {
        setSelectedPort(result.port)
        setPorts([{ 
          port: result.port, 
          available: true, 
          detected: `✅ Sensor Detected! (Signal: ${result.signal_strength || 95}%)`
        }])
      } else {
        const testedPorts = result.tested_ports?.map((p: string) => ({ 
          port: p, 
          available: false, 
          detected: 'No sensor' 
        })) || []
        setPorts(testedPorts)
      }
    } catch (error) {
      console.error('Auto-detect error:', error)
    }
    setScanning(false)
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
          <h2 className="text-2xl font-bold text-cyan-400">Connecting...</h2>
        </div>
      </div>
    )
  }

  const { sensor_data: sensor, source, connection_status } = data
  const connectionStatus = {
    isConnected: connection_status?.connected || false,
    port: connection_status?.port || 'N/A',
    baud: connection_status?.baud || 19200,
    signal_strength: source === 'LIVE_FEED' ? 95 : 50,
    latency: source === 'LIVE_FEED' ? 25 : 2,
    packet_loss: connection_status?.packet_loss || 0,
    uptime: connection_status?.uptime_seconds || 0,
    last_read: connection_status?.last_poll || new Date().toISOString(),
    circuit_state: 'CLOSED',
    health_score: sensor.data_quality || 95
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-6">
      <div className="max-w-[1920px] mx-auto space-y-6">
        
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
              Connection Management
            </h1>
            <p className="text-slate-500 text-sm mt-1">Sensor connection, diagnostics & configuration</p>
          </div>
          <div className={`px-4 py-2 rounded-lg border ${
            connectionStatus.isConnected 
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' 
              : 'bg-red-500/10 border-red-500/30 text-red-400'
          }`}>
            <div className="flex items-center gap-2">
              {connectionStatus.isConnected ? (
                <>
                  <Wifi className="w-5 h-5" />
                  <span className="font-semibold">Connected</span>
                </>
              ) : (
                <>
                  <WifiOff className="w-5 h-5" />
                  <span className="font-semibold">Disconnected</span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Quick Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatusCard 
            icon={<Signal className="w-5 h-5" />}
            label="Signal Strength"
            value={`${connectionStatus.signal_strength}%`}
            status={connectionStatus.signal_strength > 80 ? 'good' : 'warning'}
            trend="stable"
          />
          <StatusCard 
            icon={<Zap className="w-5 h-5" />}
            label="Latency"
            value={`${connectionStatus.latency}ms`}
            status={connectionStatus.latency < 100 ? 'good' : 'warning'}
            trend="stable"
          />
          <StatusCard 
            icon={<CheckCircle2 className="w-5 h-5" />}
            label="Packet Loss"
            value={`${connectionStatus.packet_loss}%`}
            status={connectionStatus.packet_loss < 1 ? 'good' : 'warning'}
            trend="improving"
          />
          <StatusCard 
            icon={<Clock className="w-5 h-5" />}
            label="Uptime"
            value={`${connectionStatus.uptime}h`}
            status="good"
            trend="stable"
          />
        </div>

        {/* Connection Details Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* Connection Configuration */}
          <div className="relative group">
            <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/20 to-blue-500/20 rounded-2xl blur-xl group-hover:blur-2xl transition-all duration-300" />
            <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
              <h2 className="text-xl font-bold text-slate-200 mb-6 flex items-center gap-2">
                <Settings className="w-5 h-5 text-cyan-400" />
                Connection Configuration
              </h2>

              <div className="space-y-4">
                <div>
                  <label className="text-sm text-slate-400 font-semibold uppercase tracking-wider">Serial Port</label>
                  <div className="mt-2 flex gap-2">
                    <select 
                      value={selectedPort}
                      onChange={(e) => setSelectedPort(e.target.value)}
                      className="flex-1 px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-200 focus:outline-none focus:border-cyan-500"
                    >
                      <option>COM1</option>
                      <option>COM3</option>
                      <option>COM4</option>
                      <option>COM5</option>
                      <option>/dev/ttyUSB0</option>
                      <option>/dev/ttyACM0</option>
                    </select>
                    <button
                      onClick={scanPorts}
                      disabled={scanning}
                      className="px-4 py-2 bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 rounded-lg hover:bg-cyan-500/20 transition-all disabled:opacity-50"
                    >
                      <RefreshCw className={`w-5 h-5 ${scanning ? 'animate-spin' : ''}`} />
                    </button>
                    <button
                      onClick={autoDetectPort}
                      disabled={scanning}
                      className="px-6 py-2 bg-gradient-to-r from-emerald-500/20 to-cyan-500/20 border border-emerald-500/40 text-emerald-400 rounded-lg hover:from-emerald-500/30 hover:to-cyan-500/30 transition-all disabled:opacity-50 flex items-center gap-2 font-semibold"
                    >
                      <Zap className={`w-5 h-5 ${scanning ? 'animate-pulse' : ''}`} />
                      {scanning ? 'Detecting...' : 'Auto-Detect'}
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm text-slate-400 font-semibold uppercase tracking-wider">Baud Rate</label>
                    <select className="w-full px-4 py-2 mt-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-200">
                      <option>9600</option>
                      <option selected>19200</option>
                      <option>38400</option>
                      <option>57600</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-sm text-slate-400 font-semibold uppercase tracking-wider">Slave ID</label>
                    <input type="number" value={1} className="w-full px-4 py-2 mt-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-200" />
                  </div>
                </div>

                <div className="pt-4 flex gap-2">
                  <button className="flex-1 px-4 py-3 bg-gradient-to-r from-emerald-500 to-teal-500 text-white rounded-lg font-semibold hover:shadow-lg hover:shadow-emerald-500/50 transition-all">
                    <CheckCircle2 className="w-5 h-5 inline mr-2" />
                    Connect
                  </button>
                  <button className="flex-1 px-4 py-3 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg font-semibold hover:border-slate-600 transition-all">
                    <WifiOff className="w-5 h-5 inline mr-2" />
                    Disconnect
                  </button>
                </div>
              </div>

              {/* Port Scan Results */}
              {ports.length > 0 && (
                <div className="mt-6 pt-6 border-t border-slate-800/50">
                  <h3 className="text-sm font-semibold text-slate-300 mb-3">Available Ports</h3>
                  <div className="space-y-2">
                    {ports.map((p) => (
                      <div key={p.port} className="flex items-center justify-between p-3 bg-slate-800/30 rounded-lg hover:bg-slate-800/50 transition-all cursor-pointer">
                        <div className="flex items-center gap-3">
                          <div className={`w-2 h-2 rounded-full ${p.available ? 'bg-emerald-400' : 'bg-red-400'}`} />
                          <div>
                            <p className="font-semibold text-slate-200">{p.port}</p>
                            <p className="text-xs text-slate-500">{p.detected}</p>
                          </div>
                        </div>
                        <span className={`text-xs font-semibold px-2 py-1 rounded ${
                          p.available 
                            ? 'bg-emerald-500/20 text-emerald-400' 
                            : 'bg-slate-700/50 text-slate-400'
                        }`}>
                          {p.available ? 'Available' : 'In Use'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Real-time Connection Status */}
          <div className="relative group">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/20 to-teal-500/20 rounded-2xl blur-xl group-hover:blur-2xl transition-all duration-300" />
            <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
              <h2 className="text-xl font-bold text-slate-200 mb-6 flex items-center gap-2">
                <Wifi className="w-5 h-5 text-emerald-400" />
                Connection Status
              </h2>

              <div className="space-y-4">
                <div className="p-4 bg-slate-800/50 rounded-lg border border-emerald-500/30">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-slate-400 font-semibold">System Status</span>
                    <div className={`flex items-center gap-2 px-3 py-1 rounded-full ${
                      connectionStatus.isConnected
                        ? 'bg-emerald-500/10 text-emerald-400'
                        : 'bg-red-500/10 text-red-400'
                    }`}>
                      <div className={`w-2 h-2 rounded-full ${connectionStatus.isConnected ? 'bg-emerald-400' : 'bg-red-400'} animate-pulse`} />
                      <span className="text-sm font-semibold">{connectionStatus.isConnected ? 'Active' : 'Inactive'}</span>
                    </div>
                  </div>
                </div>

                <div className="space-y-3">
                  <StatusRow label="Port" value={connectionStatus.port} />
                  <StatusRow label="Baud Rate" value={`${connectionStatus.baud} bps`} />
                  <StatusRow label="Last Read" value={connectionStatus.last_read} />
                  <StatusRow label="Circuit State" value={connectionStatus.circuit_state} />
                  <StatusRow label="Health Score" value={`${connectionStatus.health_score}%`} />
                </div>

                <div className="pt-4 border-t border-slate-800/50">
                  <p className="text-sm text-slate-400 font-semibold mb-3">Overall Health</p>
                  <div className="space-y-2">
                    <div className="h-4 bg-slate-800 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-emerald-500 to-teal-500 transition-all duration-500"
                        style={{ width: `${connectionStatus.health_score}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-xs text-slate-500">
                      <span>0%</span>
                      <span className="text-emerald-400 font-semibold">{connectionStatus.health_score}%</span>
                      <span>100%</span>
                    </div>
                  </div>
                </div>
              </div>

              <button
                onClick={() => setShowDetails(!showDetails)}
                className="w-full mt-6 px-4 py-2 bg-slate-800/50 border border-slate-700/50 text-slate-300 rounded-lg hover:bg-slate-800 transition-all text-sm font-semibold flex items-center justify-center gap-2"
              >
                {showDetails ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                {showDetails ? 'Hide Details' : 'Show Details'}
              </button>
            </div>
          </div>
        </div>

        {/* Sensor Details (Collapsible) */}
        {showDetails && (
          <div className="relative group">
            <div className="absolute inset-0 bg-gradient-to-br from-purple-500/20 to-pink-500/20 rounded-2xl blur-xl" />
            <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
              <h2 className="text-xl font-bold text-slate-200 mb-6">Sensor Details & Diagnostics</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <DetailCard label="Z-Axis RMS" value={`${sensor.z_rms} mm/s`} />
                <DetailCard label="X-Axis RMS" value={`${sensor.x_rms} mm/s`} />
                <DetailCard label="Temperature" value={`${sensor.temperature} °C`} />
                <DetailCard label="Frequency" value={`${sensor.frequency} Hz`} />
                <DetailCard label="Kurtosis" value={sensor.kurtosis} />
                <DetailCard label="Crest Factor" value={sensor.crest_factor} />
                <DetailCard label="ISO Class" value={sensor.iso_class} />
                <DetailCard label="Bearing Health" value={`${sensor.bearing_health}%`} />
                <DetailCard label="Alarm Status" value={sensor.alarm_status} />
              </div>

              <div className="mt-6 pt-6 border-t border-slate-800/50">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-slate-300">Raw Data (JSON)</h3>
                  <button
                    onClick={() => copyToClipboard(JSON.stringify(sensor, null, 2))}
                    className="text-xs px-3 py-1 bg-slate-800/50 border border-slate-700/50 text-slate-400 rounded hover:text-cyan-400 transition-all flex items-center gap-1"
                  >
                    <Copy className="w-3 h-3" />
                    {copied ? 'Copied!' : 'Copy'}
                  </button>
                </div>
                <pre className="bg-slate-950/50 border border-slate-800/50 rounded-lg p-4 text-xs text-slate-400 overflow-x-auto max-h-64">
{JSON.stringify({ port: connectionStatus.port, baud: connectionStatus.baud, sensor_data: sensor }, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        )}

        {/* Mode Selection (Bottom) */}
        <div className="relative group">
          <div className="absolute inset-0 bg-gradient-to-br from-orange-500/20 to-red-500/20 rounded-2xl blur-xl group-hover:blur-2xl transition-all duration-300" />
          <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
            <h2 className="text-xl font-bold text-slate-200 mb-6 flex items-center gap-2">
              <Zap className="w-5 h-5 text-orange-400" />
              Operation Mode
            </h2>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="flex items-stretch gap-4">
                <button
                  onClick={() => setIsLiveMode(true)}
                  className={`flex-1 p-6 rounded-xl border-2 transition-all ${
                    isLiveMode
                      ? 'bg-emerald-500/20 border-emerald-500 shadow-lg shadow-emerald-500/30'
                      : 'bg-slate-800/50 border-slate-700/50 hover:border-slate-600/50'
                  }`}
                >
                  <Wifi className={`w-6 h-6 mx-auto mb-2 ${isLiveMode ? 'text-emerald-400' : 'text-slate-500'}`} />
                  <p className={`font-bold text-center ${isLiveMode ? 'text-emerald-400' : 'text-slate-400'}`}>Live Feed</p>
                  <p className="text-xs text-slate-500 mt-1 text-center">Real sensor data</p>
                </button>

                <button
                  onClick={() => setIsLiveMode(false)}
                  className={`flex-1 p-6 rounded-xl border-2 transition-all ${
                    !isLiveMode
                      ? 'bg-blue-500/20 border-blue-500 shadow-lg shadow-blue-500/30'
                      : 'bg-slate-800/50 border-slate-700/50 hover:border-slate-600/50'
                  }`}
                >
                  <Zap className={`w-6 h-6 mx-auto mb-2 ${!isLiveMode ? 'text-blue-400' : 'text-slate-500'}`} />
                  <p className={`font-bold text-center ${!isLiveMode ? 'text-blue-400' : 'text-slate-400'}`}>Demo Mode</p>
                  <p className="text-xs text-slate-500 mt-1 text-center">Simulated data</p>
                </button>
              </div>

              <div className={`p-6 rounded-xl border ${
                isLiveMode
                  ? 'bg-emerald-500/10 border-emerald-500/30'
                  : 'bg-blue-500/10 border-blue-500/30'
              }`}>
                <h3 className={`font-bold mb-2 ${isLiveMode ? 'text-emerald-400' : 'text-blue-400'}`}>
                  {isLiveMode ? 'Live Mode' : 'Demo Mode'}
                </h3>
                <p className="text-sm text-slate-400 mb-4">
                  {isLiveMode
                    ? 'Reading real-time data from the Modbus sensor device. Ensure device is connected to the specified port.'
                    : 'Using simulated sensor data for testing and development. All values are generated synthetically for demonstration purposes.'}
                </p>
                <div className="space-y-2 text-xs">
                  {isLiveMode ? (
                    <>
                      <p><span className="text-emerald-400 font-semibold">✓</span> <span className="text-slate-400">Device connected to {selectedPort}</span></p>
                      <p><span className="text-emerald-400 font-semibold">✓</span> <span className="text-slate-400">Data updates at 2 Hz</span></p>
                      <p><span className="text-emerald-400 font-semibold">✓</span> <span className="text-slate-400">Real vibration measurements</span></p>
                    </>
                  ) : (
                    <>
                      <p><span className="text-blue-400 font-semibold">✓</span> <span className="text-slate-400">Synthetic data generation</span></p>
                      <p><span className="text-blue-400 font-semibold">✓</span> <span className="text-slate-400">No device required</span></p>
                      <p><span className="text-blue-400 font-semibold">✓</span> <span className="text-slate-400">Perfect for testing UI</span></p>
                    </>
                  )}
                </div>
              </div>
            </div>

            <div className="mt-6 pt-6 border-t border-slate-800/50 p-4 bg-slate-800/30 rounded-lg flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-semibold text-slate-200">Safety Notice</p>
                <p className="text-xs text-slate-400 mt-1">
                  Switching between Live and Demo modes is safe. In Demo mode, real sensor data is not processed. Always verify sensor connection before relying on live measurements for critical operations.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function StatusCard({ icon, label, value, status, trend }: any) {
  return (
    <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-xl p-4 hover:border-slate-700/50 transition-all">
      <div className="flex items-center justify-between mb-2">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
          status === 'good' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'
        }`}>
          {icon}
        </div>
        <span className={`text-xs font-bold px-2 py-1 rounded ${
          status === 'good' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'
        }`}>
          {status === 'good' ? '✓' : '⚠'}
        </span>
      </div>
      <p className="text-xs text-slate-500 uppercase font-semibold">{label}</p>
      <p className="text-2xl font-bold text-slate-200 mt-1">{value}</p>
      <p className="text-xs text-slate-500 mt-2 capitalize">{trend}</p>
    </div>
  )
}

function StatusRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-2 px-3 bg-slate-800/30 rounded-lg">
      <span className="text-sm text-slate-400">{label}</span>
      <span className="text-sm font-semibold text-slate-200">{value}</span>
    </div>
  )
}

function DetailCard({ label, value }: { label: string; value: any }) {
  return (
    <div className="p-4 bg-slate-800/30 rounded-lg border border-slate-800/50">
      <p className="text-xs text-slate-500 uppercase font-semibold mb-1">{label}</p>
      <p className="text-lg font-bold text-slate-200">{value}</p>
    </div>
  )
}

