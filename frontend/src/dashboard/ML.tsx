import { useEffect, useState } from 'react'
import { Brain, RefreshCw, BarChart3, Download } from 'lucide-react'
import { wsClient, WebSocketData } from '@/lib/websocket'
import LiveGauge from '@/components/ui/LiveGauge'
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts'

export default function MLTab() {
  const [data, setData] = useState<WebSocketData | null>(null)
  const [predictionHistory, setPredictionHistory] = useState<{ name: string; value: number }[]>([])

  useEffect(() => {
    const unsubscribe = wsClient.subscribe((newData: WebSocketData) => {
      setData(newData)
      
      if (newData.ml_prediction) {
        // Update prediction history (last 24 hours simulation)
        const normal = newData.ml_prediction.probabilities.normal * 100
        const anomaly = newData.ml_prediction.probabilities.anomaly * 100
        
        setPredictionHistory([
          { name: 'Normal', value: normal },
          { name: 'Anomaly', value: anomaly }
        ])
      }
    })

    return unsubscribe
  }, [])

  const handleReloadModel = async () => {
    // TODO: Implement model reload API call
    console.log('Reloading model...')
  }

  const handleCaptureTraining = async () => {
    // TODO: Implement training data capture
    console.log('Capturing training data...')
  }

  if (!data || !data.ml_prediction) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto mb-4" />
          <div className="text-text-muted font-medium">Waiting for ML predictions...</div>
        </div>
      </div>
    )
  }

  const ml = data.ml_prediction
  const confidence = ml.confidence * 100

  const COLORS = ['#10B981', '#EF4444']

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div>
        <h1 className="text-h1 text-text mb-2 font-bold tracking-tight">ML INTELLIGENCE</h1>
        <p className="text-text-muted font-medium">Live Anomaly Detection & Predictions</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Live Prediction Display */}
        <div className="bg-card border border-border rounded-lg p-6 card-hover shadow-xl">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-h2 text-text font-bold">Live Prediction</h3>
            <div className={`px-4 py-2 rounded-lg font-semibold ${
              ml.class === 1 
                ? 'bg-critical/20 text-critical border border-critical/30' 
                : 'bg-success/20 text-success border border-success/30'
            }`}>
              {ml.class_name}
            </div>
          </div>

          <div className="flex flex-col items-center mb-6">
            <LiveGauge
              value={confidence}
              min={0}
              max={100}
              label="Confidence"
              unit="%"
              size="lg"
            />
            <div className="mt-4 text-center">
              <div className="text-sm text-text-muted mb-2">Prediction Confidence</div>
              <div className="text-3xl font-mono font-bold text-primary">{confidence.toFixed(1)}%</div>
            </div>
          </div>

          <div className="space-y-3">
            <div>
              <div className="text-sm text-text-muted mb-1">Normal Probability</div>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-border rounded-full h-2">
                  <div 
                    className="bg-success h-2 rounded-full"
                    style={{ width: `${ml.probabilities.normal * 100}%` }}
                  />
                </div>
                <span className="text-sm font-mono text-text">{(ml.probabilities.normal * 100).toFixed(1)}%</span>
              </div>
            </div>
            <div>
              <div className="text-sm text-text-muted mb-1">Anomaly Probability</div>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-border rounded-full h-2">
                  <div 
                    className="bg-critical h-2 rounded-full"
                    style={{ width: `${ml.probabilities.anomaly * 100}%` }}
                  />
                </div>
                <span className="text-sm font-mono text-text">{(ml.probabilities.anomaly * 100).toFixed(1)}%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Prediction History */}
        <div className="bg-card border border-border rounded-lg p-6 card-hover shadow-xl">
          <h3 className="text-h2 text-text mb-6 font-bold">Prediction History (24hr)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={predictionHistory}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {predictionHistory.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ backgroundColor: '#1A2332', border: '1px solid #2D3748', color: '#E5E7EB' }} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Feature Importance */}
      {ml.feature_importance && (
        <div className="bg-card border border-border rounded-lg p-6 card-hover shadow-xl">
          <h3 className="text-h2 text-text mb-4 font-bold">Feature Importance Matrix</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(ml.feature_importance)
              .sort(([, a], [, b]) => b - a)
              .map(([feature, importance]) => (
                <div key={feature} className="space-y-2">
                  <div className="text-sm text-text-muted">{feature}</div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 bg-border rounded-full h-2">
                      <div 
                        className="bg-primary h-2 rounded-full"
                        style={{ width: `${importance * 100}%` }}
                      />
                    </div>
                    <span className="text-xs font-mono text-text">{(importance * 100).toFixed(1)}%</span>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3">
        <button
          onClick={handleCaptureTraining}
          className="px-5 py-2.5 bg-primary/10 border border-primary/30 rounded-lg text-primary hover:bg-primary/20 hover:shadow-lg hover:scale-105 transition-all duration-200 flex items-center gap-2 font-semibold"
        >
          <Download className="w-4 h-4" />
          CAPTURE TRAINING
        </button>
        <button
          onClick={handleReloadModel}
          className="px-5 py-2.5 bg-card border border-border rounded-lg text-text hover:bg-primary/10 hover:border-primary/30 hover:shadow-lg hover:scale-105 transition-all duration-200 flex items-center gap-2 font-semibold"
        >
          <RefreshCw className="w-4 h-4" />
          RELOAD MODEL
        </button>
        <button className="px-5 py-2.5 bg-card border border-border rounded-lg text-text hover:bg-primary/10 hover:border-primary/30 hover:shadow-lg hover:scale-105 transition-all duration-200 flex items-center gap-2 font-semibold">
          <BarChart3 className="w-4 h-4" />
          MODEL STATS
        </button>
      </div>
    </div>
  )
}

