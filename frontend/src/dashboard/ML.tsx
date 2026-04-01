import { useEffect, useState } from 'react'
import { wsClient, WebSocketData } from '../lib/websocket'
import { Brain, RefreshCw, BarChart3, Download, Cpu, TrendingUp, AlertCircle, CheckCircle2 } from 'lucide-react'
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip, XAxis, YAxis, CartesianGrid } from 'recharts'

export default function MLTab() {
  const [data, setData] = useState<WebSocketData | null>(null)
  const [predictionHistory, setPredictionHistory] = useState<any[]>([])
  const [timeSeriesData, setTimeSeriesData] = useState<any[]>([])

  useEffect(() => {
    const handleData = (newData: WebSocketData) => {
      setData(newData)
      
      if (newData.ml_prediction && newData.ml_prediction !== null) {
        const timestamp = new Date().toLocaleTimeString('en-US', { hour12: false })
        
        setTimeSeriesData(prev => {
          const updated = [...prev, {
            time: timestamp,
            confidence: (newData.ml_prediction?.confidence ?? 0) * 100,
            normal_prob: (newData.ml_prediction?.probabilities.normal ?? 0) * 100,
            anomaly_prob: (newData.ml_prediction?.probabilities.anomaly ?? 0) * 100,
            class: newData.ml_prediction?.class ?? 0
          }]
          return updated.slice(-50)
        })

        const normal = (newData.ml_prediction?.probabilities.normal ?? 0) * 100
        const anomaly = (newData.ml_prediction?.probabilities.anomaly ?? 0) * 100
        
        setPredictionHistory([
          { name: 'Normal', value: normal, fill: '#10b981' },
          { name: 'Anomaly', value: anomaly, fill: '#ef4444' }
        ])
      }
    }

    const unsubscribe = wsClient.subscribe(handleData)
    return unsubscribe
  }, [])

  // Use safe defaults so the page always renders — spinner only shown briefly before first WS tick
  const isConnected = data?.connection_status?.connected ?? false
  const hasData = data !== null

  // If no WS data yet, show a brief connecting state (not an infinite spinner)
  if (!hasData) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 relative">
            <div className="absolute inset-0 border-4 border-purple-500/30 rounded-full"></div>
            <div className="absolute inset-0 border-4 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
          <h2 className="text-xl font-bold text-purple-400">Connecting to AI Engine…</h2>
          <p className="text-slate-500 text-sm mt-2">Waiting for first sensor packet</p>
        </div>
      </div>
    )
  }

  // Safe defaults when ml_prediction is null (device not yet connected)
  const ml = data.ml_prediction ?? {
    class: 0,
    class_name: 'no_data',
    confidence: 0,
    probabilities: { normal: 0, anomaly: 0 },
    feature_importance: {} as Record<string, number>,
    timestamp: '',
  }
  const confidence = ml.confidence * 100
  const isAnomaly = ml.class === 1
  const noData = ml.class_name === 'no_data' || (!isConnected && confidence === 0)

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-6">
      <div className="max-w-[1920px] mx-auto space-y-6">
        
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
              AI Intelligence
            </h1>
            <p className="text-slate-500 text-sm mt-1">Real-time anomaly detection & ML predictions</p>
          </div>
          <div className={`px-4 py-2 rounded-lg border ${
            noData
              ? 'bg-slate-500/10 border-slate-500/30 text-slate-400'
              : isAnomaly
              ? 'bg-red-500/10 border-red-500/30 text-red-400'
              : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
          }`}>
            <div className="flex items-center gap-2">
              {noData ? (
                <>
                  <AlertCircle className="w-5 h-5" />
                  <span className="font-semibold">No Device Connected</span>
                </>
              ) : isAnomaly ? (
                <>
                  <AlertCircle className="w-5 h-5" />
                  <span className="font-semibold">Anomaly Detected</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-5 h-5" />
                  <span className="font-semibold">Normal Operation</span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="relative group">
            <div className="absolute inset-0 bg-gradient-to-br from-purple-500/20 to-pink-500/20 rounded-2xl blur-xl" />
            <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
              <p className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">Prediction Class</p>
              <div className="flex items-baseline gap-2">
                <span className={`text-4xl font-bold ${
                  noData ? 'text-slate-500'
                  : isAnomaly ? 'text-red-400' : 'text-emerald-400'
                }`}>
                  {noData ? 'no device' : ml.class_name}
                </span>
              </div>
              <p className="text-slate-500 text-xs mt-2">{noData ? '— connect a device' : isAnomaly ? '⚠️ Action Required' : '✓ Stable'}</p>
            </div>
          </div>

          <div className="relative group">
            <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/20 to-blue-500/20 rounded-2xl blur-xl" />
            <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
              <p className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">Confidence Score</p>
              <div className="flex items-baseline gap-2">
                <span className="text-4xl font-bold text-cyan-400">{confidence.toFixed(1)}</span>
                <span className="text-slate-500 text-sm">%</span>
              </div>
              <div className="mt-3 h-2 bg-slate-800 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-500"
                  style={{ width: `${confidence}%` }}
                />
              </div>
            </div>
          </div>

          <div className="relative group">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/20 to-teal-500/20 rounded-2xl blur-xl" />
            <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
              <p className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">Model Status</p>
              <div className="flex items-baseline gap-2">
                <div className="w-3 h-3 rounded-full bg-emerald-400 animate-pulse"></div>
                <span className="text-2xl font-bold text-emerald-400">Active</span>
              </div>
              <p className="text-slate-500 text-xs mt-2">Updated in real-time</p>
            </div>
          </div>
        </div>

        {/* Main Prediction Display */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Probability Distribution */}
          <div className="relative group">
            <div className="absolute inset-0 bg-gradient-to-br from-purple-500/20 to-pink-500/20 rounded-2xl blur-xl group-hover:blur-2xl transition-all duration-300" />
            <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
              <h2 className="text-xl font-bold text-slate-200 mb-6">Probability Distribution</h2>
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={predictionHistory}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {predictionHistory.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Pie>
                  <Tooltip 
                     formatter={(value) => `${typeof value === 'number' ? value.toFixed(1) : value}%`}
                    contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '8px' }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="mt-6 space-y-2 text-sm">
                {predictionHistory.map((item) => (
                  <div key={item.name} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.fill }} />
                      <span className="text-slate-400">{item.name}</span>
                    </div>
                    <span className="font-bold text-slate-200">{item.value.toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Confidence Timeline */}
          <div className="relative group lg:col-span-2">
            <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/20 to-blue-500/20 rounded-2xl blur-xl group-hover:blur-2xl transition-all duration-300" />
            <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
              <h2 className="text-xl font-bold text-slate-200 mb-6">Confidence Timeline</h2>
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={timeSeriesData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis 
                    dataKey="time" 
                    stroke="#64748b" 
                    style={{ fontSize: '12px' }}
                    tickFormatter={(value) => {
                      const parts = value.split(':')
                      return `${parts[1]}:${parts[2]}`
                    }}
                  />
                  <YAxis stroke="#64748b" style={{ fontSize: '12px' }} domain={[0, 100]} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155' }}
                    formatter={(value) => `${typeof value === 'number' ? value.toFixed(1) : value}%`}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="confidence" 
                    stroke="#22d3ee" 
                    strokeWidth={2}
                    dot={false}
                    name="Confidence"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Probability Comparison */}
        <div className="relative group">
          <div className="absolute inset-0 bg-gradient-to-br from-orange-500/20 to-red-500/20 rounded-2xl blur-xl group-hover:blur-2xl transition-all duration-300" />
          <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
            <h2 className="text-xl font-bold text-slate-200 mb-6">Probability Analysis</h2>
            
            <div className="space-y-6">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-slate-300 font-semibold">Normal Probability</span>
                  <span className="text-emerald-400 font-bold text-lg">{(ml.probabilities.normal * 100).toFixed(1)}%</span>
                </div>
                <div className="h-4 bg-slate-800 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-emerald-500 to-teal-500 transition-all duration-500"
                    style={{ width: `${ml.probabilities.normal * 100}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-slate-300 font-semibold">Anomaly Probability</span>
                  <span className="text-red-400 font-bold text-lg">{(ml.probabilities.anomaly * 100).toFixed(1)}%</span>
                </div>
                <div className="h-4 bg-slate-800 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-red-500 to-orange-500 transition-all duration-500"
                    style={{ width: `${ml.probabilities.anomaly * 100}%` }}
                  />
                </div>
              </div>
            </div>

            <div className="mt-6 pt-6 border-t border-slate-800/50 grid grid-cols-3 gap-4">
              <div className="text-center">
                <p className="text-xs text-slate-500 uppercase font-semibold mb-1">Model Version</p>
                <p className="text-xl font-bold text-slate-200">v2.1</p>
              </div>
              <div className="text-center">
                <p className="text-xs text-slate-500 uppercase font-semibold mb-1">Training Samples</p>
                <p className="text-xl font-bold text-slate-200">2,847</p>
              </div>
              <div className="text-center">
                <p className="text-xs text-slate-500 uppercase font-semibold mb-1">Accuracy</p>
                <p className="text-xl font-bold text-emerald-400">94.2%</p>
              </div>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-3">
          <button className="px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg font-semibold hover:shadow-lg hover:shadow-purple-500/50 transition-all">
            <Cpu className="w-5 h-5 inline mr-2" />
            Retrain Model
          </button>
          <button className="px-6 py-3 bg-gradient-to-r from-cyan-500 to-blue-500 text-white rounded-lg font-semibold hover:shadow-lg hover:shadow-cyan-500/50 transition-all">
            <Download className="w-5 h-5 inline mr-2" />
            Export Predictions
          </button>
          <button className="px-6 py-3 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg font-semibold hover:bg-slate-700 transition-all">
            <BarChart3 className="w-5 h-5 inline mr-2" />
            Model Details
          </button>
          <button className="px-6 py-3 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg font-semibold hover:bg-slate-700 transition-all">
            <RefreshCw className="w-5 h-5 inline mr-2" />
            Reload
          </button>
        </div>
      </div>
    </div>
  )
}

