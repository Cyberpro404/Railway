import { ReactNode, useEffect, useState } from 'react'
import { cn } from '@/lib/utils'

interface MetricCardProps {
  title: string
  value: string | number
  unit?: string
  trend?: 'up' | 'down' | 'neutral'
  status?: 'good' | 'warning' | 'critical'
  icon?: ReactNode
  sparkline?: number[]
  animated?: boolean
}

export default function MetricCard({
  title,
  value,
  unit,
  trend,
  status,
  icon,
  sparkline,
  animated = true
}: MetricCardProps) {
  // Convert string values back to numbers if needed
  const numericValue = typeof value === 'string' ? parseFloat(value) : value
  const stringValue = typeof value === 'string' ? value : (typeof value === 'number' ? value.toString() : String(value))
  
  const [displayValue, setDisplayValue] = useState(animated && typeof numericValue === 'number' ? 0 : numericValue)
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    setIsVisible(true)
    if (animated && typeof numericValue === 'number' && numericValue > 0) {
      const duration = 1000
      const steps = 60
      const increment = numericValue / steps
      const stepDuration = duration / steps
      let current = 0
      
      const timer = setInterval(() => {
        current += increment
        if (current >= numericValue) {
          setDisplayValue(numericValue)
          clearInterval(timer)
        } else {
          setDisplayValue(Math.round(current * 1000) / 1000)
        }
      }, stepDuration)
      
      return () => clearInterval(timer)
    } else {
      setDisplayValue(numericValue)
    }
  }, [numericValue, animated])

  const statusConfig = {
    good: {
      border: 'border-success/50',
      bg: 'bg-success/10',
      glow: 'card-glow-success',
      shadow: 'shadow-[0_0_20px_rgba(16,185,129,0.15)]',
      dot: 'bg-success'
    },
    warning: {
      border: 'border-warning/50',
      bg: 'bg-warning/10',
      glow: 'card-glow-warning',
      shadow: 'shadow-[0_0_20px_rgba(245,158,11,0.15)]',
      dot: 'bg-warning'
    },
    critical: {
      border: 'border-critical/60',
      bg: 'bg-critical/15',
      glow: 'card-glow-critical',
      shadow: 'shadow-[0_0_25px_rgba(239,68,68,0.25)]',
      dot: 'bg-critical'
    }
  }

  const config = status ? statusConfig[status] : null

  return (
    <div className={cn(
      "bg-card border rounded-xl p-5 card-hover relative overflow-hidden",
      "transition-all duration-500 group",
      "backdrop-blur-sm",
      isVisible && "fade-in-up",
      config?.border,
      config?.bg,
      config?.glow
    )}>
      {/* Animated background gradient */}
      <div className={cn(
        "absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500",
        status === 'good' && "bg-gradient-to-br from-success/10 to-transparent",
        status === 'warning' && "bg-gradient-to-br from-warning/10 to-transparent",
        status === 'critical' && "bg-gradient-to-br from-critical/15 to-transparent"
      )} />
      
      {/* Shimmer effect for critical status */}
      {status === 'critical' && (
        <div className="absolute inset-0 shimmer pointer-events-none opacity-30" />
      )}
      
      {/* Animated border glow */}
      {status && (
        <div className={cn(
          "absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500",
          status === 'good' && "bg-gradient-to-r from-success/20 via-success/10 to-transparent",
          status === 'warning' && "bg-gradient-to-r from-warning/20 via-warning/10 to-transparent",
          status === 'critical' && "bg-gradient-to-r from-critical/30 via-critical/15 to-transparent"
        )} />
      )}
      
      <div className="relative z-10">
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            <p className="text-xs text-text-muted uppercase tracking-wider font-bold mb-2 opacity-80">
              {title}
            </p>
            <div className="flex items-baseline gap-2">
              <span className={cn(
                "text-3xl font-mono font-bold tracking-tight transition-all duration-300",
                "metric-font",
                status === 'critical' && "text-critical",
                status === 'warning' && "text-warning",
                status === 'good' && "text-success"
              )}>
                {typeof displayValue === 'number' ? displayValue.toFixed(3) : displayValue}
              </span>
              {unit && (
                <span className="text-sm text-text-muted font-semibold opacity-70">
                  {unit}
                </span>
              )}
            </div>
          </div>
          {icon && (
            <div className={cn(
              "text-primary transition-all duration-500 group-hover:scale-110",
              status === 'critical' && "animate-pulse-cyan text-critical",
              status === 'warning' && "text-warning",
              status === 'good' && "text-success"
            )}>
              {icon}
            </div>
          )}
        </div>
        
        {sparkline && sparkline.length > 0 && (
          <div className="h-12 mt-4 flex items-end gap-0.5 relative">
            {sparkline.map((val, i) => {
              const maxVal = Math.max(...sparkline, 0.001)
              const height = (val / maxVal) * 100
              return (
                <div
                  key={i}
                  className={cn(
                    "flex-1 rounded-t transition-all duration-500 hover:opacity-80",
                    "relative overflow-hidden group/bar",
                    status === 'critical' ? 'bg-gradient-to-t from-critical to-critical/60' :
                    status === 'warning' ? 'bg-gradient-to-t from-warning to-warning/60' :
                    'bg-gradient-to-t from-primary to-primary/60'
                  )}
                  style={{ 
                    height: `${height}%`,
                    minHeight: height > 0 ? '3px' : '0',
                    animationDelay: `${i * 0.05}s`
                  }}
                >
                  <div className={cn(
                    "absolute inset-0 opacity-0 group-hover/bar:opacity-100 transition-opacity",
                    "bg-gradient-to-t from-white/20 to-transparent"
                  )} />
                </div>
              )
            })}
          </div>
        )}
      </div>
      
      {/* Status indicator with pulse */}
      {status && (
        <div className={cn(
          "absolute top-3 right-3 w-3 h-3 rounded-full",
          config?.dot,
          status === 'critical' && "pulse-ring",
          status !== 'critical' && "pulse-subtle"
        )}>
          <div className={cn(
            "absolute inset-0 rounded-full animate-ping",
            config?.dot,
            "opacity-75"
          )} />
        </div>
      )}
      
      {/* Trend indicator */}
      {trend && trend !== 'neutral' && (
        <div className={cn(
          "absolute bottom-3 right-3 text-xs font-bold",
          trend === 'up' && "text-success",
          trend === 'down' && "text-critical"
        )}>
          {trend === 'up' ? '↑' : '↓'}
        </div>
      )}
    </div>
  )
}
