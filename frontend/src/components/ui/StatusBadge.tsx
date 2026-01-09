import { cn } from '@/lib/utils'

interface StatusBadgeProps {
  status: 'active' | 'inactive' | 'warning' | 'critical' | 'pending'
  label: string
  animated?: boolean
  size?: 'sm' | 'md' | 'lg'
}

export default function StatusBadge({
  status,
  label,
  animated = true,
  size = 'md'
}: StatusBadgeProps) {
  const statusClasses = {
    active: 'bg-success/20 text-success border-success/40',
    inactive: 'bg-text-muted/20 text-text-muted border-text-muted/40',
    warning: 'bg-warning/20 text-warning border-warning/40',
    critical: 'bg-critical/20 text-critical border-critical/40',
    pending: 'bg-primary/20 text-primary border-primary/40',
  }

  const sizeClasses = {
    sm: 'px-2.5 py-1 text-xs',
    md: 'px-3 py-1.5 text-sm',
    lg: 'px-4 py-2 text-base',
  }

  return (
    <div className={cn(
      'inline-flex items-center gap-1.5 rounded-full border font-medium',
      'backdrop-blur-sm transition-all duration-200',
      statusClasses[status],
      sizeClasses[size]
    )}>
      <div className={cn(
        'w-2 h-2 rounded-full',
        status === 'active' && 'bg-success',
        status === 'inactive' && 'bg-text-muted',
        status === 'warning' && 'bg-warning',
        status === 'critical' && 'bg-critical',
        status === 'pending' && 'bg-primary',
        animated && (status === 'active' || status === 'critical' || status === 'warning') && 'animate-pulse'
      )} />
      {label}
    </div>
  )
}
