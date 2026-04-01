import { useEffect, useState, useMemo } from 'react'
import { wsClient, WebSocketData } from '../lib/websocket'
import { Activity, Zap, Server, AlertTriangle, TrendingUp, TrendingDown, Thermometer, Train, ServerCrash, CheckCircle2 } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine } from 'recharts'

// Stable placeholder values per coach index (no Math.random — values never change unexpectedly)
const FLEET_PLACEHOLDERS = [
  { vib: '2.34', temp: '47.2', status: 'healthy' },
  { vib: '1.87', temp: '44.8', status: 'healthy' },
  { vib: '2.91', temp: '49.1', status: 'healthy' },
  { vib: '5.12', temp: '58.3', status: 'critical' },
  { vib: '2.05', temp: '46.0', status: 'healthy' },
  { vib: '2.63', temp: '48.5', status: 'healthy' },
  { vib: '3.74', temp: '53.2', status: 'warning' },
  { vib: '1.95', temp: '45.7', status: 'healthy' },
  { vib: '2.18', temp: '47.9', status: 'healthy' },
  { vib: '2.47', temp: '48.1', status: 'healthy' },
  { vib: '2.02', temp: '46.4', status: 'healthy' },
]

// Fleet Data — coach 1 always uses real WS data, others show stable placeholders
const generateFleetStatus = (realDataMap: any, isConn: boolean) => {
  const fleet = []
  for (let i = 1; i <= 12; i++) {
    const isReal = i === 1
    const id = `COACH-${1000 + i}`
    const ph = FLEET_PLACEHOLDERS[(i - 2 + 11) % 11] // stable placeholder

    fleet.push({
      id,
      status: isReal
        ? (isConn
            ? (realDataMap?.alarm_status === 'Critical' ? 'critical'
               : realDataMap?.alarm_status === 'Warning' ? 'warning' : 'healthy')
            : 'offline')
        : ph.status,
      vibration: isReal && realDataMap ? realDataMap.z_rms?.toFixed(2) : ph.vib,
      temp: isReal && realDataMap ? realDataMap.temperature?.toFixed(1) : ph.temp,
      uptime: '99.9%',
      lastPing: isReal ? '1s ago' : '—'
    })
  }
  return fleet
}

const recentEvents = [
  { id: 1, time: '10:42 AM', level: 'CRITICAL', msg: 'COACH-1004 VIBRATION SPIKE (Z-AXIS 8.4 mm/s)' },
  { id: 2, time: '10:15 AM', level: 'WARNING', msg: 'COACH-1007 TEMP ELEVATED (62°C)' },
  { id: 3, time: '09:30 AM', level: 'INFO', msg: 'SYSTEM DAILY CALIBRATION COMPLETE' },
  { id: 4, time: '08:12 AM', level: 'INFO', msg: 'NODE-3 RECONNECTION SUCCESSFUL' },
]

export default function NewDashboard() {
  const [data, setData] = useState<WebSocketData | null>(null)
  const [history, setHistory] = useState<any[]>([])
  
  // Real-time time display
  const [currentTime, setCurrentTime] = useState(new Date().toLocaleTimeString('en-US', { hour12: false }))

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date().toLocaleTimeString('en-US', { hour12: false })), 1000)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    const handleData = (newData: WebSocketData) => {
      setData(newData)
      const timestamp = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute:'2-digit', second:'2-digit' })
      
      setHistory(prev => {
        const updated = [...prev, {
          time: timestamp,
          z_rms: newData.sensor_data.z_rms || 0,
          temp: newData.sensor_data.temperature || 0,
          isAnomaly: newData.ml_prediction?.class === 1
        }]
        return updated.slice(-40) // Keep last 40 ticks for industrial compactness
      })
    }

    const unsubscribe = wsClient.subscribe(handleData)
    return unsubscribe
  }, [])

  // System States
  const isConnected = data?.connection_status?.connected ?? false

  // Fleet merged data — pass isConnected so coach 1 shows offline when disconnected
  const fleetData = useMemo(
    () => generateFleetStatus(data?.sensor_data, isConnected),
    [data, isConnected]
  )
  const activeDevice = fleetData[0]

  return (
    <div className="flex flex-col min-h-screen bg-background p-4 gap-4 overflow-x-hidden">
      
      {/* TOP BANNER */}
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-text uppercase tracking-widest">Project Gandhiva</h1>
            <span className="bg-primary/20 text-primary text-[10px] px-2 py-0.5 rounded font-bold uppercase border border-primary/30">
              Overview
            </span>
          </div>
          <span className="text-xs text-text-muted mt-1 tracking-wider uppercase">System Wide Diagnostics Panel</span>
        </div>

        <div className="flex flex-col items-end">
          <div className="font-mono text-xl text-primary tracking-widest font-bold">
            {currentTime}
          </div>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs text-text-muted uppercase">SYS STATUS:</span>
            <div className={`px-2 py-0.5 text-[10px] font-bold uppercase flex items-center gap-1 ${
              isConnected ? 'bg-success/20 text-success' : 'bg-critical/20 text-critical'
            }`}>
              <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-success animate-ping' : 'bg-critical'}`} />
              {isConnected ? 'LIVE FEED ACTIVE' : 'NO SIGNAL'}
            </div>
          </div>
        </div>
      </div>

      {/* ROW 1: KPI METRICS (4 items) */}
      <div className="grid grid-cols-4 gap-4">
        <KpiCard 
          title="ACTIVE FLEET SIZE" 
          value="12 / 12" 
          unit="Coaches" 
          icon={<Train className="text-primary w-5 h-5" />} 
          statusColor="text-primary" 
        />
        <KpiCard 
          title="PEAK VIBRATION (Z)" 
          value={activeDevice.vibration} 
          unit="mm/s" 
          icon={<Activity className={`w-5 h-5 ${activeDevice.status === 'critical' ? 'text-critical' : 'text-primary'}`} />} 
          statusColor={activeDevice.status === 'critical' ? 'text-critical' : 'text-primary'} 
          alert={activeDevice.status === 'critical'}
        />
        <KpiCard 
          title="CRITICAL ALERTS" 
          value="1" 
          unit="Active" 
          icon={<AlertTriangle className="text-critical w-5 h-5" />} 
          statusColor="text-critical" 
          alert={true}
        />
        <KpiCard 
          title="NETWORK UPTIME" 
          value="99.9" 
          unit="%" 
          icon={<Server className="text-success w-5 h-5" />} 
          statusColor="text-success" 
        />
      </div>

      {/* ROW 2: FLEET HEALTH SUMMARY (Dense grid) */}
      <div className="bg-card border border-border flex flex-col min-h-0">
        <div className="px-3 py-2 border-b border-border flex items-center justify-between bg-black/20">
          <h2 className="text-xs font-bold text-text-muted uppercase tracking-widest flex items-center gap-2">
            <Server className="w-3 h-3" /> Fleet Subsystem Health
          </h2>
        </div>
        <div className="grid grid-cols-6 gap-[1px] bg-border p-[1px]">
          {fleetData.map((node) => (
            <div key={node.id} className={`bg-card p-2 flex flex-col justify-between ${
              node.status === 'critical' ? 'border-b-2 border-critical' : 
              node.status === 'warning' ? 'border-b-2 border-warning' : 
              'border-b-2 border-success'
            }`}>
              <div className="flex justify-between items-center mb-2">
                <span className="text-[10px] font-bold text-text uppercase">{node.id}</span>
                {node.status === 'healthy' ? <CheckCircle2 className="w-3 h-3 text-success" /> : 
                 node.status === 'warning' ? <AlertTriangle className="w-3 h-3 text-warning" /> : 
                 <ServerCrash className="w-3 h-3 text-critical animate-pulse" />}
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-text-muted font-mono">V: <span className={node.status==='critical'?'text-critical':''}>{node.vibration}</span></span>
                <span className="text-text-muted font-mono">T: <span className={node.status==='warning'?'text-warning':''}>{node.temp}</span></span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 flex-1 min-h-[400px]">
        {/* ROW 3: CRITICAL EVENTS (Left Col) */}
        <div className="col-span-1 bg-card border border-border flex flex-col">
          <div className="px-3 py-2 border-b border-border bg-black/20">
            <h2 className="text-xs font-bold text-text-muted uppercase tracking-widest">Recent Events Log</h2>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {recentEvents.map(ev => (
              <div key={ev.id} className="flex flex-col p-2 bg-background border border-border rounded-sm">
                <div className="flex justify-between items-center">
                  <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded-sm ${
                    ev.level === 'CRITICAL' ? 'bg-critical/20 text-critical border border-critical/30' :
                    ev.level === 'WARNING' ? 'bg-warning/20 text-warning border border-warning/30' :
                    'bg-primary/10 text-primary border border-primary/20'
                  }`}>{ev.level}</span>
                  <span className="text-[10px] font-mono text-text-muted">{ev.time}</span>
                </div>
                <div className="mt-1 text-xs text-text font-medium">{ev.msg}</div>
              </div>
            ))}
          </div>
        </div>

        {/* ROW 4: LIVE CHARTS (Right 2 Cols) */}
        <div className="col-span-2 flex flex-col gap-4">
          {/* Vibration Chart */}
          <div className="flex-1 bg-card border border-border flex flex-col">
            <div className="px-3 py-2 border-b border-border flex justify-between items-center bg-black/20">
              <h2 className="text-xs font-bold text-text-muted uppercase tracking-widest flex items-center gap-2">
                <Activity className="w-3 h-3 text-primary" /> Live Vibration Monitor (ISO Standard)
              </h2>
              <span className="text-[10px] text-primary animate-pulse flex items-center gap-1 font-mono">SYNC: PRIMARY DMX</span>
            </div>
            <div className="flex-1 p-2">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={history} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#403f3f" vertical={false} />
                  <XAxis dataKey="time" stroke="#a0a0a0" fontSize={10} tickMargin={5} minTickGap={30} />
                  <YAxis stroke="#a0a0a0" fontSize={10} domain={[0, 'auto']} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1a1a1a', borderColor: '#404040', fontSize: '12px' }}
                    itemStyle={{ color: '#0078d4' }}
                  />
                  <ReferenceLine y={4.5} stroke="#ff9800" strokeDasharray="3 3" label={{ position: 'insideTopLeft', value: 'WARN (4.5)', fill: '#ff9800', fontSize: 10 }} />
                  <ReferenceLine y={7.1} stroke="#f44336" strokeDasharray="3 3" label={{ position: 'insideTopLeft', value: 'CRIT (7.1)', fill: '#f44336', fontSize: 10 }} />
                  <Line 
                    type="monotone" 
                    dataKey="z_rms" 
                    stroke="#0078d4" 
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Temp Chart */}
          <div className="flex-1 bg-card border border-border flex flex-col">
            <div className="px-3 py-2 border-b border-border flex justify-between items-center bg-black/20">
              <h2 className="text-xs font-bold text-text-muted uppercase tracking-widest flex items-center gap-2">
                <Thermometer className="w-3 h-3 text-warning" /> Thermal Trend
              </h2>
            </div>
            <div className="flex-1 p-2">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={history} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#403f3f" vertical={false} />
                  <XAxis dataKey="time" stroke="#a0a0a0" fontSize={10} tickMargin={5} minTickGap={30} />
                  <YAxis stroke="#a0a0a0" fontSize={10} domain={['dataMin - 5', 'auto']} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1a1a1a', borderColor: '#404040', fontSize: '12px' }}
                    itemStyle={{ color: '#ff9800' }}
                  />
                  <Line 
                    type="stepAfter" 
                    dataKey="temp" 
                    stroke="#ff9800" 
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      {/* RAW REGISTER DATA - Device Communication Status */}
      <div className="bg-card border border-border">
        <div className="px-3 py-2 border-b border-border flex items-center justify-between bg-black/20">
          <h2 className="text-xs font-bold text-text-muted uppercase tracking-widest flex items-center gap-2">
            <Zap className="w-3 h-3 text-primary" /> Modbus Register Data (Live)
          </h2>
          <div className="flex items-center gap-3">
            {data?.sensor_data && (
              <>
                <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-sm border ${
                  isConnected ? 'bg-success/10 text-success border-success/30' : 'bg-critical/10 text-critical border-critical/30'
                }`}>
                  {isConnected ? 'RECEIVING' : 'OFFLINE'}
                </span>
                {(data.sensor_data as any).register_source && (
                  <span className="text-[10px] text-primary font-mono">
                    Addr: {(data.sensor_data as any).register_source}
                  </span>
                )}
                {(data.sensor_data as any).non_zero_registers !== undefined && (
                  <span className="text-[10px] text-text-muted font-mono">
                    Non-zero: {(data.sensor_data as any).non_zero_registers}/22
                  </span>
                )}
                {(data.sensor_data as any).float32_reg20_21 !== undefined && (data.sensor_data as any).float32_reg20_21 !== 0 && (
                  <span className="text-[10px] text-warning font-mono">
                    F32[20:21]={(data.sensor_data as any).float32_reg20_21}
                  </span>
                )}
              </>
            )}
          </div>
        </div>
        <div className="p-3">
          {data?.sensor_data?.raw_registers && data.sensor_data.raw_registers.length > 0 ? (
            <div className="grid grid-cols-11 gap-1">
              {data.sensor_data.raw_registers.map((val: number, i: number) => (
                <div key={i} className={`rounded px-1 py-1 text-center ${
                  val !== 0 ? 'bg-primary/20 border border-primary/40' : 'bg-background/50'
                }`}>
                  <div className="text-[8px] text-text-muted">R{i}</div>
                  <div className={`text-[11px] font-mono ${val !== 0 ? 'text-primary font-bold' : 'text-text-muted'}`}>{val}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-xs text-text-muted text-center py-2">
              {isConnected ? 'Waiting for register data...' : 'No device connected — go to Connection tab to connect'}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function KpiCard({ title, value, unit, icon, statusColor, alert = false }: any) {
  return (
    <div className={`bg-card border ${alert ? 'border-critical/50 shadow-[0_0_15px_rgba(244,67,54,0.15)]' : 'border-border'} p-4 flex flex-col relative overflow-hidden`}>
      {alert && <div className="absolute top-0 right-0 w-8 h-8 bg-critical/10 rounded-bl-full" />}
      <div className="flex justify-between items-start mb-2 relative z-10">
        <span className="text-[10px] font-bold text-text-muted uppercase tracking-widest">{title}</span>
        {icon}
      </div>
      <div className="flex items-baseline gap-1 relative z-10">
        <span className={`text-3xl font-mono font-bold ${statusColor}`}>{value}</span>
        <span className="text-xs text-text-muted font-bold ml-1">{unit}</span>
      </div>
    </div>
  )
}
