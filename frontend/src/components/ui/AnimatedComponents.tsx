import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'

interface AnimatedCardProps {
  children: React.ReactNode
  className?: string
  delay?: number
  duration?: number
  hover?: boolean
}

export function AnimatedCard({ 
  children, 
  className, 
  delay = 0, 
  duration = 0.5,
  hover = true 
}: AnimatedCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ 
        duration, 
        delay,
        ease: "easeOut"
      }}
      whileHover={hover ? { 
        scale: 1.02,
        boxShadow: "0 10px 30px rgba(0, 0, 0, 0.2)"
      } : undefined}
      className={cn(
        "bg-card border border-border rounded-lg transition-all duration-300",
        className
      )}
    >
      {children}
    </motion.div>
  )
}

interface AnimatedStatCardProps {
  title: string
  value: string | number
  unit?: string
  icon?: React.ReactNode
  color?: 'primary' | 'success' | 'warning' | 'error'
  trend?: {
    value: number
    direction: 'up' | 'down'
  }
  delay?: number
}

export function AnimatedStatCard({
  title,
  value,
  unit,
  icon,
  color = 'primary',
  trend,
  delay = 0
}: AnimatedStatCardProps) {
  const colorClasses = {
    primary: 'text-primary border-primary/30 bg-primary/5',
    success: 'text-success border-success/30 bg-success/5',
    warning: 'text-warning border-warning/30 bg-warning/5',
    error: 'text-error border-error/30 bg-error/5'
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, delay }}
      whileHover={{ 
        scale: 1.05,
        boxShadow: "0 8px 25px rgba(0, 0, 0, 0.15)"
      }}
      className={cn(
        "p-6 rounded-lg border transition-all duration-300",
        colorClasses[color]
      )}
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          {icon && (
            <motion.div
              initial={{ rotate: 0 }}
              animate={{ rotate: 360 }}
              transition={{ duration: 2, delay: delay + 0.5, repeat: Infinity, repeatDelay: 3 }}
              className="opacity-80"
            >
              {icon}
            </motion.div>
          )}
          <div>
            <p className="text-sm text-text-muted uppercase tracking-wide font-semibold">
              {title}
            </p>
          </div>
        </div>
        {trend && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: delay + 0.3 }}
            className={cn(
              "flex items-center gap-1 text-xs font-medium",
              trend.direction === 'up' ? 'text-success' : 'text-error'
            )}
          >
            <span>{trend.direction === 'up' ? '↑' : '↓'}</span>
            <span>{Math.abs(trend.value)}%</span>
          </motion.div>
        )}
      </div>
      
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: delay + 0.2 }}
        className="flex items-baseline gap-2"
      >
        <span className="text-3xl font-mono font-bold">
          {value}
        </span>
        {unit && (
          <span className="text-sm text-text-muted opacity-70">
            {unit}
          </span>
        )}
      </motion.div>
    </motion.div>
  )
}

interface AnimatedProgressProps {
  value: number
  max?: number
  color?: 'primary' | 'success' | 'warning' | 'error'
  size?: 'sm' | 'md' | 'lg'
  showValue?: boolean
  animated?: boolean
  delay?: number
}

export function AnimatedProgress({
  value,
  max = 100,
  color = 'primary',
  size = 'md',
  showValue = true,
  animated = true,
  delay = 0
}: AnimatedProgressProps) {
  const percentage = Math.min((value / max) * 100, 100)
  
  const sizeClasses = {
    sm: 'h-1',
    md: 'h-2',
    lg: 'h-3'
  }

  const colorClasses = {
    primary: 'bg-primary',
    success: 'bg-success',
    warning: 'bg-warning',
    error: 'bg-error'
  }

  return (
    <div className="w-full">
      {showValue && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay }}
          className="flex justify-between mb-2 text-sm"
        >
          <span className="text-text-muted">Progress</span>
          <span className="font-medium">{percentage.toFixed(1)}%</span>
        </motion.div>
      )}
      <div className={cn("bg-border rounded-full overflow-hidden", sizeClasses[size])}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ 
            duration: animated ? 1 : 0, 
            delay: animated ? delay + 0.3 : 0,
            ease: "easeOut"
          }}
          className={cn("h-full rounded-full", colorClasses[color])}
        />
      </div>
    </div>
  )
}

interface PulseIndicatorProps {
  active: boolean
  color?: 'primary' | 'success' | 'warning' | 'error'
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export function PulseIndicator({
  active,
  color = 'primary',
  size = 'md',
  className
}: PulseIndicatorProps) {
  const sizeClasses = {
    sm: 'w-2 h-2',
    md: 'w-3 h-3',
    lg: 'w-4 h-4'
  }

  const colorClasses = {
    primary: 'bg-primary',
    success: 'bg-success',
    warning: 'bg-warning',
    error: 'bg-error'
  }

  return (
    <div className={cn("relative", sizeClasses[size], className)}>
      {active && (
        <>
          <motion.div
            animate={{
              scale: [1, 1.5, 1.5, 1],
              opacity: [1, 0.5, 0.5, 1],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: "easeInOut"
            }}
            className={cn(
              "absolute inset-0 rounded-full",
              colorClasses[color]
            )}
          />
          <motion.div
            animate={{
              scale: [1, 2, 2, 1],
              opacity: [0.8, 0, 0, 0.8],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: "easeInOut"
            }}
            className={cn(
              "absolute inset-0 rounded-full",
              colorClasses[color]
            )}
          />
        </>
      )}
      <div className={cn(
        "relative rounded-full",
        colorClasses[color],
        !active && "opacity-30"
      )} />
    </div>
  )
}

interface SlideInProps {
  children: React.ReactNode
  direction?: 'left' | 'right' | 'up' | 'down'
  delay?: number
  duration?: number
  className?: string
}

export function SlideIn({
  children,
  direction = 'up',
  delay = 0,
  duration = 0.5,
  className
}: SlideInProps) {
  const initialOffset = {
    left: { x: -50, y: 0 },
    right: { x: 50, y: 0 },
    up: { x: 0, y: 50 },
    down: { x: 0, y: -50 }
  }

  return (
    <motion.div
      initial={{ opacity: 0, ...initialOffset[direction] }}
      animate={{ opacity: 1, x: 0, y: 0 }}
      transition={{ duration, delay, ease: "easeOut" }}
      className={className}
    >
      {children}
    </motion.div>
  )
}

interface FadeInProps {
  children: React.ReactNode
  delay?: number
  duration?: number
  className?: string
}

export function FadeIn({
  children,
  delay = 0,
  duration = 0.5,
  className
}: FadeInProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration, delay }}
      className={className}
    >
      {children}
    </motion.div>
  )
}
