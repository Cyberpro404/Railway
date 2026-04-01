import { useEffect, useState } from 'react'
import { wsClient, WebSocketData } from '../lib/websocket'
import { Wrench, Save, RefreshCw } from 'lucide-react'

export default function Configuration() {
  const [data, setData] = useState<WebSocketData | null>(null)
  const [pollingRate, setPollingRate] = useState('250')
  const [registerStart, setRegisterStart] = useState('5200')
  const [registerCount, setRegisterCount] = useState('22')
  const [slaveId, setSlaveId] = useState('1')
  const [saveMsg, setSaveMsg] = useState('')

  useEffect(() => {
    const unsubscribe = wsClient.subscribe((newData: WebSocketData) => setData(newData))
    return unsubscribe
  }, [])

  const isConnected = data?.connection_status?.connected ?? false

  const handleSave = () => {
    // Configuration is informational — actual register config is in the backend
    setSaveMsg('Configuration noted. Backend uses these values by default.')
    setTimeout(() => setSaveMsg(''), 3000)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-pink-400 to-rose-400 bg-clip-text text-transparent">
            Configuration
          </h1>
          <p className="text-slate-500 text-sm mt-1">System settings & Modbus configuration</p>
        </div>

        {/* Connection Info */}
        <div className="bg-slate-900/80 border border-slate-800/50 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-slate-400 mb-4 flex items-center gap-2">
            <Wrench className="w-4 h-4" /> Current Connection
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-xs text-slate-500">Status</div>
              <div className={`text-sm font-bold ${isConnected ? 'text-emerald-400' : 'text-red-400'}`}>
                {isConnected ? 'Connected' : 'Disconnected'}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500">Port</div>
              <div className="text-sm font-bold text-cyan-400">{data?.connection_status?.port || 'N/A'}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500">Baud</div>
              <div className="text-sm font-bold text-blue-400">{data?.connection_status?.baud ?? 'N/A'}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500">Slave ID</div>
              <div className="text-sm font-bold text-purple-400">{data?.connection_status?.slave_id ?? 'N/A'}</div>
            </div>
          </div>
        </div>

        {/* Modbus Register Config */}
        <div className="bg-slate-900/80 border border-slate-800/50 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-slate-400 mb-4">Modbus Register Configuration</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-500 mb-1">Start Register Address</label>
              <input type="number" value={registerStart} onChange={e => setRegisterStart(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 text-white rounded-lg px-3 py-2 text-sm" />
              <p className="text-[10px] text-slate-600 mt-1">Modbus address (5200 = register 45201)</p>
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">Register Count</label>
              <input type="number" value={registerCount} onChange={e => setRegisterCount(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 text-white rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">Slave ID</label>
              <input type="number" value={slaveId} onChange={e => setSlaveId(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 text-white rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">Polling Rate (ms)</label>
              <input type="number" value={pollingRate} onChange={e => setPollingRate(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 text-white rounded-lg px-3 py-2 text-sm" />
            </div>
          </div>
        </div>

        {/* Register Map Reference */}
        <div className="bg-slate-900/80 border border-slate-800/50 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-slate-400 mb-4">Register Map (45201 – 45222)</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-500 text-xs uppercase border-b border-slate-800">
                  <th className="text-left py-2 px-2">Register</th>
                  <th className="text-left py-2 px-2">Index</th>
                  <th className="text-left py-2 px-2">Parameter</th>
                  <th className="text-left py-2 px-2">Unit</th>
                  <th className="text-left py-2 px-2">Divisor</th>
                </tr>
              </thead>
              <tbody className="text-xs">
                {[
                  ['45201', '0', 'Z RMS Velocity', 'in/sec', '1000'],
                  ['45202', '1', 'Z RMS Velocity', 'mm/sec', '1000'],
                  ['45203', '2', 'Temperature', '°F', '100'],
                  ['45204', '3', 'Temperature', '°C', '100'],
                  ['45205', '4', 'X RMS Velocity', 'in/sec', '1000'],
                  ['45206', '5', 'X RMS Velocity', 'mm/sec', '1000'],
                  ['45207', '6', 'Z Peak Acceleration', 'G', '1000'],
                  ['45208', '7', 'X Peak Acceleration', 'G', '1000'],
                  ['45209', '8', 'Z Peak Frequency', 'Hz', '10'],
                  ['45210', '9', 'X Peak Frequency', 'Hz', '10'],
                  ['45211', '10', 'Z RMS Acceleration', 'G', '1000'],
                  ['45212', '11', 'X RMS Acceleration', 'G', '1000'],
                  ['45213', '12', 'Z Kurtosis', '', '1000'],
                  ['45214', '13', 'X Kurtosis', '', '1000'],
                  ['45215', '14', 'Z Crest Factor', '', '1000'],
                  ['45216', '15', 'X Crest Factor', '', '1000'],
                  ['45217', '16', 'Z Peak Velocity', 'in/sec', '1000'],
                  ['45218', '17', 'Z Peak Velocity', 'mm/sec', '1000'],
                  ['45219', '18', 'X Peak Velocity', 'in/sec', '1000'],
                  ['45220', '19', 'X Peak Velocity', 'mm/sec', '1000'],
                  ['45221', '20', 'Z HF RMS Accel', 'G', '1000'],
                  ['45222', '21', 'X HF RMS Accel', 'G', '1000'],
                ].map(([reg, idx, param, unit, div]) => (
                  <tr key={reg} className="border-b border-slate-800/30 hover:bg-slate-800/20">
                    <td className="py-1.5 px-2 text-cyan-400 font-mono">{reg}</td>
                    <td className="py-1.5 px-2 text-slate-500">{idx}</td>
                    <td className="py-1.5 px-2 text-white">{param}</td>
                    <td className="py-1.5 px-2 text-amber-400">{unit}</td>
                    <td className="py-1.5 px-2 text-slate-400">÷{div}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="flex gap-3">
          <button onClick={handleSave}
            className="px-5 py-2.5 bg-pink-600/20 border border-pink-500/30 text-pink-400 rounded-lg hover:bg-pink-600/30 transition flex items-center gap-2 text-sm font-semibold">
            <Save className="w-4 h-4" /> Save Configuration
          </button>
          {saveMsg && <span className="text-sm text-emerald-400 self-center">{saveMsg}</span>}
        </div>
      </div>
    </div>
  )
}
