import { ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface AdvancedChartProps {
  title: string
  children: ReactNode
  subtitle?: string
  action?: ReactNode
  className?: string
  headerAction?: ReactNode
  animated?: boolean
}

export default function AdvancedChart({
  title,
  children,
  subtitle,
  action,
  className,
  headerAction,
  animated = true
}: AdvancedChartProps) {
  return (
    <div className={cn(
      "bg-card border border-border/50 rounded-xl p-6",
      "backdrop-blur-sm transition-all duration-300",
      animated && 'card-hover card-glow',
      className
    )}>
      <div className="flex items-start justify-between mb-6">
        <div className="flex-1">
          <h3 className="text-lg font-bold text-text mb-1">{title}</h3>
          {subtitle && (
            <p className="text-sm text-text-muted">{subtitle}</p>
          )}
        </div>
        {headerAction && (
          <div className="flex items-center gap-2">
            {headerAction}
          </div>
        )}
      </div>

      <div className="relative">
        {children}
      </div>

      {action && (
        <div className="mt-4 pt-4 border-t border-border/30">
          {action}
        </div>
      )}
    </div>
  )
}
