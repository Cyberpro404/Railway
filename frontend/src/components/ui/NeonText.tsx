
import { cn } from '@/lib/utils';

interface NeonTextProps {
    children: React.ReactNode;
    color?: 'cyan' | 'green' | 'amber' | 'red' | 'white';
    className?: string;
    size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '4xl';
}

export function NeonText({ children, color = 'cyan', className, size = 'md' }: NeonTextProps) {
    const colorStyles = {
        cyan: 'text-cyan-400 drop-shadow-[0_0_8px_rgba(34,211,238,0.8)]',
        green: 'text-emerald-400 drop-shadow-[0_0_8px_rgba(52,211,153,0.8)]',
        amber: 'text-amber-400 drop-shadow-[0_0_8px_rgba(251,191,36,0.8)]',
        red: 'text-red-400 drop-shadow-[0_0_8px_rgba(248,113,113,0.8)]',
        white: 'text-white drop-shadow-[0_0_10px_rgba(255,255,255,0.5)]',
    };

    const sizeStyles = {
        xs: 'text-xs',
        sm: 'text-sm',
        md: 'text-base',
        lg: 'text-lg',
        xl: 'text-xl',
        '2xl': 'text-2xl',
        '4xl': 'text-4xl',
    }

    return (
        <span className={cn("font-mono font-bold tracking-wider", colorStyles[color], sizeStyles[size], className)}>
            {children}
        </span>
    );
}
