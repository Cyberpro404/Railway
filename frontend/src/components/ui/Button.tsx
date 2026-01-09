import { ButtonHTMLAttributes, forwardRef } from 'react'
import { cn } from '@/lib/utils'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'critical' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'md', ...props }, ref) => {
    const variants = {
      default: 'bg-card border border-border text-text hover:bg-primary/10 hover:border-primary/30',
      primary: 'bg-primary/10 border border-primary/30 text-primary hover:bg-primary/20',
      success: 'bg-success/10 border border-success/30 text-success hover:bg-success/20',
      warning: 'bg-warning/10 border border-warning/30 text-warning hover:bg-warning/20',
      critical: 'bg-critical/10 border border-critical/30 text-critical hover:bg-critical/20',
      ghost: 'bg-transparent border-transparent text-text hover:bg-card',
    }

    const sizes = {
      sm: 'px-3 py-1.5 text-sm',
      md: 'px-4 py-2 text-base',
      lg: 'px-6 py-3 text-lg',
    }

    return (
      <button
        className={cn(
          'rounded-lg transition-colors font-medium',
          variants[variant],
          sizes[size],
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)

Button.displayName = 'Button'

export default Button

