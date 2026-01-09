import { InputHTMLAttributes, forwardRef } from 'react'
import { cn } from '@/lib/utils'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          'w-full px-3 py-2 bg-background border border-border rounded-lg',
          'text-text placeholder-text-muted',
          'focus:outline-none focus:ring-2 focus:ring-primary/50',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)

Input.displayName = 'Input'

export default Input

