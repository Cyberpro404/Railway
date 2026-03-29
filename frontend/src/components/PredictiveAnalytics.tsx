import { useState, useEffect } from 'react'
import Card from '@/components/ui/Card'
import { AnimatedCard, FadeIn, AnimatedProgress } from '@/components/ui/AnimatedComponents'
import { TrendingUp, Activity, Zap, Thermometer, AlertTriangle, CheckCircle } from 'lucide-react'
import { wsClient, WebSocketData } from '@/lib/websocket'

interface HistoricalData {
  timestamp: string
  z_rms: number
  x_rms: number
  temperature: number
  frequency: number
  bearing_health: number
}

interface PredictionResult {
  parameter: string
  current: number
  predicted: number
  trend: 'increasing' | 'decreasing' | 'stable'
  confidence: number
  timeHorizon: string
  riskLevel: 'low' | 'medium' | 'high'
}

export default function PredictiveAnalytics() {
  const [data, setData] = useState<WebSocketData | null>(null)
  const [historicalData, setHistoricalData] = useState<HistoricalData[]>([])
  const [predictions, setPredictions] = useState<PredictionResult[]>([])
  const [isAnalyzing, setIsAnalyzing] = useState(false)

  useEffect(() => {
    const unsubscribe = wsClient.subscribe((newData: WebSocketData) => {
      setData(newData)
      
      // Store historical data (keep last 100 points)
      if (newData.sensor_data) {
        const historicalPoint: HistoricalData = {
          timestamp: newData.timestamp,
          z_rms: newData.sensor_data.z_rms,
          x_rms: newData.sensor_data.x_rms,
          temperature: newData.sensor_data.temperature,
          frequency: newData.sensor_data.frequency,
          bearing_health: newData.sensor_data.bearing_health
        }
        
        setHistoricalData(prev => {
          const updated = [...prev, historicalPoint]
          return updated.slice(-100) // Keep last 100 data points
        })
      }
    })

    return unsubscribe
  }, [])

  useEffect(() => {
    if (historicalData.length >= 10) {
      generatePredictions()
    }
  }, [historicalData])

  const generatePredictions = () => {
    setIsAnalyzing(true)
    
    const newPredictions: PredictionResult[] = []
    
    // Simple linear regression for prediction
    const predictLinear = (data: number[], horizon: number) => {
      if (data.length < 2) return data[data.length - 1] || 0
      
      const n = data.length
      const sumX = (n * (n - 1)) / 2
      const sumY = data.reduce((sum, val) => sum + val, 0)
      const sumXY = data.reduce((sum, val, idx) => sum + val * idx, 0)
      const sumX2 = (n * (n - 1) * (2 * n - 1)) / 6
      
      const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX)
      const intercept = (sumY - slope * sumX) / n
      
      return intercept + slope * (n + horizon)
    }
    
    const calculateTrend = (data: number[]): 'increasing' | 'decreasing' | 'stable' => {
      if (data.length < 2) return 'stable'
      
      const recent = data.slice(-5)
      const older = data.slice(-10, -5)
      
      if (recent.length === 0 || older.length === 0) return 'stable'
      
      const recentAvg = recent.reduce((sum, val) => sum + val, 0) / recent.length
      const olderAvg = older.reduce((sum, val) => sum + val, 0) / older.length
      
      const change = (recentAvg - olderAvg) / olderAvg
      
      if (Math.abs(change) < 0.05) return 'stable'
      return change > 0 ? 'increasing' : 'decreasing'
    }
    
    const calculateRiskLevel = (current: number, predicted: number, trend: string): 'low' | 'medium' | 'high' => {
      const change = Math.abs((predicted - current) / current)
      
      if (trend === 'increasing' && change > 0.2) return 'high'
      if (trend === 'increasing' && change > 0.1) return 'medium'
      if (change > 0.3) return 'high'
      if (change > 0.15) return 'medium'
      return 'low'
    }
    
    // Z-RMS Prediction (30 min ahead)
    const zRmsData = historicalData.map(d => d.z_rms)
    const zRmsPredicted = predictLinear(zRmsData, 30)
    const zRmsTrend = calculateTrend(zRmsData)
    
    newPredictions.push({
      parameter: 'Z-Axis Vibration',
      current: data?.sensor_data?.z_rms || 0,
      predicted: zRmsPredicted,
      trend: zRmsTrend,
      confidence: Math.max(60, 95 - historicalData.length * 0.5),
      timeHorizon: '30 min',
      riskLevel: calculateRiskLevel(data?.sensor_data?.z_rms || 0, zRmsPredicted, zRmsTrend)
    })
    
    // Temperature Prediction (1 hour ahead)
    const tempData = historicalData.map(d => d.temperature)
    const tempPredicted = predictLinear(tempData, 60)
    const tempTrend = calculateTrend(tempData)
    
    newPredictions.push({
      parameter: 'Temperature',
      current: data?.sensor_data?.temperature || 0,
      predicted: tempPredicted,
      trend: tempTrend,
      confidence: Math.max(65, 90 - historicalData.length * 0.3),
      timeHorizon: '1 hour',
      riskLevel: calculateRiskLevel(data?.sensor_data?.temperature || 0, tempPredicted, tempTrend)
    })
    
    // Bearing Health Prediction (2 hours ahead)
    const bearingData = historicalData.map(d => d.bearing_health)
    const bearingPredicted = predictLinear(bearingData, 120)
    const bearingTrend = calculateTrend(bearingData)
    
    newPredictions.push({
      parameter: 'Bearing Health',
      current: data?.sensor_data?.bearing_health || 100,
      predicted: Math.max(0, Math.min(100, bearingPredicted)),
      trend: bearingTrend,
      confidence: Math.max(70, 85 - historicalData.length * 0.2),
      timeHorizon: '2 hours',
      riskLevel: calculateRiskLevel(data?.sensor_data?.bearing_health || 100, bearingPredicted, bearingTrend)
    })
    
    // Frequency Prediction (15 min ahead)
    const freqData = historicalData.map(d => d.frequency)
    const freqPredicted = predictLinear(freqData, 15)
    const freqTrend = calculateTrend(freqData)
    
    newPredictions.push({
      parameter: 'Peak Frequency',
      current: data?.sensor_data?.frequency || 0,
      predicted: freqPredicted,
      trend: freqTrend,
      confidence: Math.max(55, 80 - historicalData.length * 0.4),
      timeHorizon: '15 min',
      riskLevel: calculateRiskLevel(data?.sensor_data?.frequency || 0, freqPredicted, freqTrend)
    })
    
    setPredictions(newPredictions)
    setIsAnalyzing(false)
  }

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'high':
        return 'text-error border-error/30 bg-error/5'
      case 'medium':
        return 'text-warning border-warning/30 bg-warning/5'
      default:
        return 'text-success border-success/30 bg-success/5'
    }
  }

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'increasing':
        return <TrendingUp className="w-4 h-4 text-error" />
      case 'decreasing':
        return <TrendingUp className="w-4 h-4 text-success rotate-180" />
      default:
        return <Activity className="w-4 h-4 text-primary" />
    }
  }

  const getParameterIcon = (parameter: string) => {
    if (parameter.includes('Vibration')) return <Activity className="w-5 h-5" />
    if (parameter.includes('Temperature')) return <Thermometer className="w-5 h-5" />
    if (parameter.includes('Frequency')) return <Zap className="w-5 h-5" />
    return <CheckCircle className="w-5 h-5" />
  }

  return (
    <div className="space-y-6">
      {/* Analysis Status */}
      <AnimatedCard delay={0.1}>
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-3 h-3 rounded-full ${isAnalyzing ? 'bg-warning animate-pulse' : 'bg-success'}`} />
              <div>
                <h3 className="text-lg font-semibold text-text">Predictive Analytics</h3>
                <p className="text-sm text-text-muted">
                  {isAnalyzing ? 'Analyzing trends...' : `Analysis complete (${historicalData.length} data points)`}
                </p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-xs text-text-muted">Model Confidence</p>
              <p className="text-sm font-mono font-bold text-primary">
                {predictions.length > 0 ? (predictions.reduce((sum, p) => sum + p.confidence, 0) / predictions.length).toFixed(1) : 0}%
              </p>
            </div>
          </div>
        </Card>
      </AnimatedCard>

      {/* Predictions Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {predictions.map((prediction, index) => (
          <AnimatedCard key={prediction.parameter} delay={0.2 + (index * 0.1)}>
            <Card className={`p-6 border ${getRiskColor(prediction.riskLevel)}`}>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-background/50">
                    {getParameterIcon(prediction.parameter)}
                  </div>
                  <div>
                    <h4 className="font-semibold text-text">{prediction.parameter}</h4>
                    <p className="text-xs text-text-muted">{prediction.timeHorizon} forecast</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {getTrendIcon(prediction.trend)}
                  <span className="text-xs capitalize text-text-muted">{prediction.trend}</span>
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex justify-between items-end">
                  <div>
                    <p className="text-xs text-text-muted mb-1">Current</p>
                    <p className="text-xl font-mono font-bold text-text">
                      {prediction.current.toFixed(2)}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-text-muted mb-1">Predicted</p>
                    <p className="text-xl font-mono font-bold text-primary">
                      {prediction.predicted.toFixed(2)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-text-muted mb-1">Change</p>
                    <p className={`text-lg font-mono font-bold ${
                      prediction.predicted > prediction.current ? 'text-error' : 
                      prediction.predicted < prediction.current ? 'text-success' : 'text-primary'
                    }`}>
                      {prediction.predicted > prediction.current ? '+' : ''}
                      {((prediction.predicted - prediction.current) / prediction.current * 100).toFixed(1)}%
                    </p>
                  </div>
                </div>

                <div className="space-y-2">
                  <AnimatedProgress 
                    value={prediction.confidence} 
                    color="primary"
                    size="sm"
                    showValue={true}
                    delay={0.3 + (index * 0.1)}
                  />
                  <div className="flex justify-between text-xs text-text-muted">
                    <span>Confidence: {prediction.confidence.toFixed(1)}%</span>
                    <span className={`capitalize font-medium ${getRiskColor(prediction.riskLevel)}`}>
                      {prediction.riskLevel} risk
                    </span>
                  </div>
                </div>
              </div>
            </Card>
          </AnimatedCard>
        ))}
      </div>

      {/* Model Information */}
      <FadeIn delay={0.8}>
        <Card className="p-6">
          <h3 className="text-lg font-semibold text-text mb-4">Model Information</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center p-4 bg-background/50 rounded-lg">
              <Activity className="w-8 h-8 text-primary mx-auto mb-2" />
              <p className="font-semibold text-text mb-1">Linear Regression</p>
              <p className="text-xs text-text-muted">Time-series analysis</p>
            </div>
            <div className="text-center p-4 bg-background/50 rounded-lg">
              <TrendingUp className="w-8 h-8 text-success mx-auto mb-2" />
              <p className="font-semibold text-text mb-1">Trend Analysis</p>
              <p className="text-xs text-text-muted">Direction & velocity</p>
            </div>
            <div className="text-center p-4 bg-background/50 rounded-lg">
              <AlertTriangle className="w-8 h-8 text-warning mx-auto mb-2" />
              <p className="font-semibold text-text mb-1">Risk Assessment</p>
              <p className="text-xs text-text-muted">Anomaly detection</p>
            </div>
          </div>
        </Card>
      </FadeIn>
    </div>
  )
}
