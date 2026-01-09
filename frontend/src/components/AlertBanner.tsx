import { useEffect, useState } from 'react'
import { AlertTriangle, X, Zap } from 'lucide-react'
import { wsClient, WebSocketData } from '@/lib/websocket'

export default function AlertBanner() {
  const [mlAlert, setMlAlert] = useState<{ message: string; confidence: number } | null>(null)
  const [dismissed, setDismissed] = useState(false)
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const unsubscribe = wsClient.subscribe((data: WebSocketData) => {
      if (data.ml_prediction && data.ml_prediction.class === 1 && data.ml_prediction.confidence > 0.3) {
        setMlAlert({
          message: data.ml_prediction.class_name,
          confidence: data.ml_prediction.confidence * 100
        })
        setDismissed(false)
        setIsVisible(true)
      } else {
        setIsVisible(false)
      }
    })

    return unsubscribe
  }, [])

  if (!mlAlert || dismissed || !isVisible) return null

  return (
    <div className="relative overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0 bg-gradient-to-r from-warning/20 via-warning/15 to-warning/20 animate-shimmer" />
      
      {/* Main banner */}
      <div className="relative bg-warning/20 border-b border-warning/50 px-6 py-4 flex items-center justify-between backdrop-blur-sm">
        {/* Left side with icon and text */}
        <div className="flex items-center gap-4">
          <div className="relative">
            <AlertTriangle className="w-6 h-6 text-warning animate-pulse-cyan" />
            <div className="absolute inset-0 w-6 h-6 text-warning animate-ping opacity-50" />
          </div>
          
          <div className="flex items-center gap-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-warning text-lg tracking-tight">
                  {mlAlert.message} DETECTED
                </span>
                <Zap className="w-4 h-4 text-warning animate-pulse" />
              </div>
              <div className="text-text-muted text-sm font-semibold mt-0.5">
                Confidence: <span className="text-warning font-bold">{mlAlert.confidence.toFixed(1)}%</span>
              </div>
            </div>
          </div>
        </div>
        
        {/* Dismiss button */}
        <button
          onClick={() => {
            setDismissed(true)
            setIsVisible(false)
          }}
          className="text-text-muted hover:text-text hover:bg-warning/10 rounded-lg p-2 transition-all duration-200 hover:scale-110 group"
        >
          <X className="w-5 h-5 group-hover:rotate-90 transition-transform duration-300" />
        </button>
        
        {/* Animated border glow */}
        <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-warning to-transparent animate-shimmer" />
      </div>
    </div>
  )
}
