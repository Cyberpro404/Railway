import { ReactNode } from 'react'
import { ArrowUp, ArrowDown, Minus } from 'lucide-react'
import { cn } from '@/lib/utils'

interface StatCardProps {
  title: string
  value: string | number
  unit?: string
  change?: number
  changeLabel?: string
  icon?: ReactNode
  color?: 'primary' | 'success' | 'warning' | 'critical'
  className?: string
}

export default function StatCard({
  title,
  value,
  unit,
  change,
  changeLabel,
  icon,
  color = 'primary',
  className
}: StatCardProps) {
  const colorClasses = {
    primary: 'border-primary/30 bg-gradient-to-br from-primary/10 to-primary/5',
    success: 'border-success/30 bg-gradient-to-br from-success/10 to-success/5',
    warning: 'border-warning/30 bg-gradient-to-br from-warning/10 to-warning/5',
    critical: 'border-critical/30 bg-gradient-to-br from-critical/10 to-critical/5',
  }

  const getTrendIcon = () => {
    if (!change) return null
    if (change > 0) return <ArrowUp className="w-4 h-4 text-success" />
    if (change < 0) return <ArrowDown className="w-4 h-4 text-critical" />
    return <Minus className="w-4 h-4 text-text-muted" />
  }

  return (
    <div className={cn(
      "bg-card border rounded-xl p-6 card-hover",
      "backdrop-blur-sm transition-all duration-300",
      colorClasses[color],
      className
    )}>
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <p className="text-sm text-text-muted font-medium uppercase tracking-wide mb-2">
            {title}
          </p>
          <div className="flex items-baseline gap-2">
            <p className="text-3xl font-bold text-text font-mono">{value}</p>
            {unit && <span className="text-sm text-text-muted font-semibold">{unit}</span>}
          </div>
        </div>
        {icon && (
          <div className={cn(
            "p-3 rounded-lg",
            color === 'primary' && 'bg-primary/20 text-primary',
            color === 'success' && 'bg-success/20 text-success',
            color === 'warning' && 'bg-warning/20 text-warning',
            color === 'critical' && 'bg-critical/20 text-critical',
          )}>
            {icon}
          </div>
        )}
      </div>

      {change !== undefined && (
        <div className="flex items-center gap-2">
          {getTrendIcon()}
          <span className={cn(
            "text-sm font-medium",
            change > 0 ? 'text-success' : change < 0 ? 'text-critical' : 'text-text-muted'
          )}>
            {Math.abs(change)}% {changeLabel || 'vs last period'}
          </span>
        </div>
      )}
    </div>
  )
}
