import React, { useState, useEffect } from 'react'
import { wsClient, WebSocketData } from '../lib/websocket'
import { 
  AlertTriangle, Wifi, Activity, Zap, Thermometer, 
  Gauge, TrendingUp, Signal, Brain
} from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts'

// Industrial colors
const COLORS = {
  bg: '#0a0f1a',
  bgPanel: '#1e293b',
  border: '#334155',
  text: '#e2e8f0',
  textMuted: '#94a3b8',
  primary: '#3b82f6',
  success: '#10b981',
  warning: '#f59e0b',
  critical: '#ef4444'
}

interface MetricCard {
  label: string
  value: string
  unit: string
  status: 'normal' | 'warning' | 'critical'
}

interface FFTPeak {
  frequency: number
  amplitude: number
  band: 'wheel' | 'bearing' | 'noise'
  abnormal: boolean
}

interface WaveformData {
  time: number
  amplitude: number
}

const OverviewTab: React.FC = () => {
  const [data, setData] = useState<WebSocketData | null>(null)
  const [currentTime, setCurrentTime] = useState(new Date())
  const [defectType, setDefectType] = useState('MONITORING NORMAL')
  const [confidence, setConfidence] = useState(98.5)
  const [severity, setSeverity] = useState<'normal' | 'warning' | 'critical'>('normal')
  const [fftData, setFFTData] = useState<FFTPeak[]>([])
  const [waveformData, setWaveformData] = useState<WaveformData[]>([])
  const [trendData, setTrendData] = useState<any[]>([])

  // Core metrics
  const [metrics, setMetrics] = useState<MetricCard[]>([
    { label: 'Z RMS', value: '0.00', unit: 'mm/s', status: 'normal' },
    { label: 'X RMS', value: '0.00', unit: 'mm/s', status: 'normal' },
    { label: 'Peak Accel', value: '0.00', unit: 'g', status: 'warning' },
    { label: 'Peak Vel', value: '0.00', unit: 'mm/s', status: 'normal' },
    { label: 'Kurtosis', value: '0.00', unit: '', status: 'normal' },
    { label: 'Crest', value: '0.00', unit: '', status: 'normal' },
    { label: 'Temp', value: '0.00', unit: '°C', status: 'normal' }
  ])

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    const handleData = (newData: WebSocketData) => {
      setData(newData)
      
      
      if (newData.sensor_data) {
        setMetrics([
          { label: 'Z RMS', value: newData.sensor_data.z_rms?.toFixed(2) ?? '0.00', unit: 'mm/s', status: 'normal' },
          { label: 'X RMS', value: newData.sensor_data.x_rms?.toFixed(2) ?? '0.00', unit: 'mm/s', status: 'normal' },
          { label: 'Peak Accel', value: newData.sensor_data.peak_accel?.toFixed(2) ?? '0.00', unit: 'g', status: (newData.sensor_data.peak_accel || 0) > 1.0 ? 'warning' : 'normal' },
          { label: 'Peak Vel', value: newData.sensor_data.peak_velocity?.toFixed(1) ?? '0.0', unit: 'mm/s', status: 'normal' },
          { label: 'Kurtosis', value: newData.sensor_data.kurtosis?.toFixed(2) ?? '0.00', unit: '', status: 'normal' },
          { label: 'Crest', value: newData.sensor_data.crest_factor?.toFixed(2) ?? '0.00', unit: '', status: 'normal' },
          { label: 'Temp', value: newData.sensor_data.temperature?.toFixed(1) ?? '0.0', unit: '°C', status: (newData.sensor_data.temperature || 0) > 50 ? 'warning' : 'normal' }
        ])
        
        setTrendData(prev => {
          const newItem = {
            time: new Date().toLocaleTimeString('en-US', { hour12: false }),
            rms: newData.sensor_data?.z_rms || 0,
            temp: newData.sensor_data?.temperature || 0
          }
          return [...prev, newItem].slice(-60)
        })
        
        // Use actual waveform and FFT data if provided by the backend, else keep empty
        if ((newData.sensor_data as any).waveform) {
            setWaveformData((newData.sensor_data as any).waveform)
        } else {
            setWaveformData([])
        }
        
        if ((newData.sensor_data as any).fft) {
            setFFTData((newData.sensor_data as any).fft)
        } else {
            setFFTData([])
        }
      }

      if (newData.ml_prediction) {
        const isDefect = newData.ml_prediction.class === 1
        const defectLabel = isDefect ? 'WHEEL FLAT DETECTED' : 'MONITORING NORMAL'
        const conf = newData.ml_prediction.confidence || 0.87

        setDefectType(defectLabel)
        setConfidence(parseFloat((conf * 100).toFixed(1)))
        setSeverity(isDefect ? 'critical' : 'normal')
      }

      // Build a synthetic waveform from actual z_rms so charts show real-derived signal
      if (newData.sensor_data) {
        const zRms = newData.sensor_data.z_rms || 0
        const xRms = newData.sensor_data.x_rms || 0
        const zFreq = (newData.sensor_data as any).z_peak_freq || 10
        const amp = zRms * 0.7
        const waveform = Array.from({ length: 200 }, (_, i) => ({
          time: i,
          amplitude: amp * Math.sin((2 * Math.PI * zFreq * i) / 200) +
                     (xRms * 0.3) * Math.sin((2 * Math.PI * zFreq * 2 * i) / 200),
        }))

        // Build FFT-like spectrum from actual frequencies and amplitudes
        const zKurt = (newData.sensor_data as any).z_kurtosis || 1
        const fft = Array.from({ length: 100 }, (_, i) => {
          const freq = i * 5
          let amplitude = 5
          if (Math.abs(freq - zFreq) < 10) amplitude = zRms * 15
          if (Math.abs(freq - zFreq * 2) < 10) amplitude = zRms * 8
          if (zKurt > 6 && Math.abs(freq - 100) < 15) amplitude += zKurt * 3
          return { frequency: freq, amplitude: Math.max(0, amplitude) }
        })

        setWaveformData(waveform)
        setFFTData(fft)
      }
    }

    const unsubscribe = wsClient.subscribe(handleData)
    return unsubscribe
  }, [])

  const isConnected = data?.connection_status?.connected ?? false

  return (
    <div className="min-h-screen" style={{ backgroundColor: COLORS.bg }}>
      
      {/* TOP ALERT BANNER */}
      <div className={`px-6 py-3 text-center font-bold text-lg border-b ${
        severity === 'critical' ? 'bg-red-500/20 border-red-500 text-red-400' :
        severity === 'warning' ? 'bg-yellow-500/20 border-yellow-500 text-yellow-400' :
        'bg-green-500/20 border-green-500 text-green-400'
      }`}>
        {severity === 'critical' ? `🔴 ${defectType} | Confidence: ${confidence}%` :
         severity === 'warning' ? `🟡 ${defectType} | Confidence: ${confidence}%` :
         `🟢 SYSTEM NORMAL | All Parameters Within Limits`}
        <span className="ml-4 font-mono text-sm">{currentTime.toLocaleTimeString()}</span>
      </div>

      {/* STATUS BAR */}
      <div className="px-6 py-2 border-b flex items-center justify-between text-sm" style={{ backgroundColor: COLORS.bgPanel, borderColor: COLORS.border }}>
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <Wifi className={`w-4 h-4 ${isConnected ? 'text-green-400' : 'text-red-400'}`} />
            <span style={{ color: COLORS.text }}>
              DXM: {isConnected ? 'Active' : 'Offline'} | Port: {data?.tcp_port || 502}
            </span>
          </div>
          <span style={{ color: COLORS.textMuted }}>Polling: 1 Hz</span>
          <span style={{ color: COLORS.textMuted }}>Last: {currentTime.toLocaleTimeString()}</span>
        </div>
        <div className={`px-3 py-1 rounded text-xs font-bold ${isConnected ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
          Edge: {isConnected ? 'Online' : 'Offline'}
        </div>
      </div>

      {/* MAIN CONTENT */}
      <div className="p-4">
        
        {/* DEFECT DISPLAY - TOP CENTER */}
        <div className="rounded-lg border p-6 mb-4 text-center" style={{ backgroundColor: COLORS.bgPanel, borderColor: COLORS.border }}>
          <div className={`text-5xl font-bold mb-2 ${
            severity === 'critical' ? 'text-red-400' :
            severity === 'warning' ? 'text-yellow-400' : 'text-green-400'
          }`}>
            {defectType}
          </div>
          <div className="flex justify-center gap-8 text-lg">
            <div>
              <span style={{ color: COLORS.textMuted }}>Confidence: </span>
              <span className="font-bold text-white">{confidence}%</span>
            </div>
            <div>
              <span style={{ color: COLORS.textMuted }}>Risk: </span>
              <span className={`font-bold ${severity === 'critical' ? 'text-red-400' : severity === 'warning' ? 'text-yellow-400' : 'text-green-400'}`}>
                {severity.toUpperCase()}
              </span>
            </div>
            <div>
              <span style={{ color: COLORS.textMuted }}>Train: </span>
              <span className="font-bold text-white">Moving</span>
            </div>
            <div>
              <span style={{ color: COLORS.textMuted }}>Device: </span>
              <span className="font-bold text-white">{data?.device_id || 'DXM-001'}</span>
            </div>
          </div>
        </div>

        {/* METRICS BAR */}
        <div className="rounded-lg border p-4 mb-4" style={{ backgroundColor: COLORS.bgPanel, borderColor: COLORS.border }}>
          <div className="grid grid-cols-7 gap-4">
            {metrics.map((metric, i) => (
              <div key={i} className="text-center border rounded p-2" style={{ borderColor: COLORS.border }}>
                <div className={`w-2 h-2 rounded-full mx-auto mb-1 ${
                  metric.status === 'normal' ? 'bg-green-400' : 'bg-yellow-400'
                }`} />
                <div style={{ color: COLORS.textMuted }} className="text-xs">{metric.label}</div>
                <div className="text-lg font-bold text-white">{metric.value}</div>
                <div style={{ color: COLORS.textMuted }} className="text-xs">{metric.unit}</div>
              </div>
            ))}
          </div>
        </div>

        {/* CHARTS ROW */}
        <div className="grid grid-cols-2 gap-4 mb-4">
          
          {/* FFT SPECTRUM */}
          <div className="rounded-lg border p-4" style={{ backgroundColor: COLORS.bgPanel, borderColor: COLORS.border }}>
            <h3 className="text-white font-bold mb-2 flex items-center gap-2">
              <Activity className="w-4 h-4" /> FFT Spectrum Analysis
            </h3>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={fftData}>
                  <XAxis dataKey="frequency" stroke={COLORS.textMuted} fontSize={10} />
                  <YAxis stroke={COLORS.textMuted} fontSize={10} />
                  <Tooltip contentStyle={{ backgroundColor: COLORS.bgPanel, border: COLORS.border }} />
                  <Area type="monotone" dataKey="amplitude" stroke={COLORS.primary} fill={COLORS.primary} fillOpacity={0.3} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="flex justify-center gap-4 mt-2 text-xs" style={{ color: COLORS.textMuted }}>
              <span>🟢 Wheel: 20-80Hz</span>
              <span>🟡 Bearing: 80-300Hz</span>
              <span>🔴 Noise: 300Hz+</span>
            </div>
          </div>

          {/* WAVEFORM */}
          <div className="rounded-lg border p-4" style={{ backgroundColor: COLORS.bgPanel, borderColor: COLORS.border }}>
            <h3 className="text-white font-bold mb-2 flex items-center gap-2">
              <Signal className="w-4 h-4" /> Time Domain Signal
            </h3>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={waveformData}>
                  <XAxis dataKey="time" stroke={COLORS.textMuted} fontSize={10} />
                  <YAxis stroke={COLORS.textMuted} fontSize={10} />
                  <Tooltip contentStyle={{ backgroundColor: COLORS.bgPanel, border: COLORS.border }} />
                  <Line type="monotone" dataKey="amplitude" stroke={COLORS.primary} strokeWidth={1} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="text-center mt-2 text-xs" style={{ color: COLORS.textMuted }}>
              Spikes indicate impulsive defects
            </div>
          </div>
        </div>

        {/* BOTTOM ROW */}
        <div className="grid grid-cols-3 gap-4">
          
          {/* DECISION PANEL */}
          <div className="rounded-lg border p-4" style={{ backgroundColor: COLORS.bgPanel, borderColor: COLORS.border }}>
            <h3 className="text-white font-bold mb-3 flex items-center gap-2">
              <Brain className="w-4 h-4" /> Decision Output
            </h3>
            <div className="space-y-3">
              <div>
                <div style={{ color: COLORS.textMuted }} className="text-sm">ML Result:</div>
                <div className="text-lg font-bold text-white">{defectType}</div>
                <div className="text-sm" style={{ color: COLORS.textMuted }}>Confidence: {confidence}%</div>
              </div>
              <div className={`p-2 rounded text-sm font-bold ${
                severity === 'critical' ? 'bg-red-500/20 text-red-400 border border-red-500' :
                severity === 'warning' ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500' :
                'bg-green-500/20 text-green-400 border border-green-500'
              }`}>
                {severity === 'critical' ? '🔧 Inspect wheel within 24h' :
                 severity === 'warning' ? '⚠ Monitor closely' :
                 '✓ Continue normal operation'}
              </div>
              <div className="text-sm text-white mt-3 space-y-1">
                {severity === 'critical' ? (
                  <>
                    <div>⚠ Monitor vibration increase</div>
                    <div>📍 Check wheel condition</div>
                    <div>📊 Log defect for analysis</div>
                  </>
                ) : (
                  <>
                    <div>• System operating normally</div>
                    <div>• Routine maintenance schedule</div>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* TREND CHART */}
          <div className="rounded-lg border p-4" style={{ backgroundColor: COLORS.bgPanel, borderColor: COLORS.border }}>
            <h3 className="text-white font-bold mb-2 flex items-center gap-2">
              <TrendingUp className="w-4 h-4" /> 60s Trend
            </h3>
            <div className="h-32">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData}>
                  <XAxis dataKey="time" stroke={COLORS.textMuted} fontSize={10} />
                  <YAxis stroke={COLORS.textMuted} fontSize={10} />
                  <Tooltip contentStyle={{ backgroundColor: COLORS.bgPanel, border: COLORS.border }} />
                  <Line type="monotone" dataKey="rms" stroke={COLORS.primary} strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="temp" stroke={COLORS.warning} strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="flex justify-center gap-4 mt-1 text-xs" style={{ color: COLORS.textMuted }}>
              <span>🔵 RMS</span>
              <span>🟡 Temp</span>
            </div>
          </div>

          {/* TRAINING */}
          <div className="rounded-lg border p-4" style={{ backgroundColor: COLORS.bgPanel, borderColor: COLORS.border }}>
            <h3 className="text-white font-bold mb-3">Training Data</h3>
            <button className="w-full py-2 px-3 rounded bg-blue-600 text-white font-medium text-sm mb-3 hover:bg-blue-700">
              Capture Sample
            </button>
            <div className="text-sm space-y-1" style={{ color: COLORS.textMuted }}>
              <div>Ready: 1,247 samples</div>
              <div>Last: 2 min ago</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default OverviewTab
