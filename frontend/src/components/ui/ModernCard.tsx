
import { ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';

interface ModernCardProps {
    children: ReactNode;
    className?: string;
    title?: string;
    glowColor?: 'cyan' | 'green' | 'amber' | 'red' | 'white';
}

export function ModernCard({ children, className, title, glowColor = 'cyan' }: ModernCardProps) {
    const glowStyles = {
        cyan: 'shadow-[0_0_15px_rgba(6,182,212,0.15)] border-cyan-500/20 hover:border-cyan-400/50 hover:shadow-[0_0_25px_rgba(6,182,212,0.3)]',
        green: 'shadow-[0_0_15px_rgba(16,185,129,0.15)] border-emerald-500/20 hover:border-emerald-400/50 hover:shadow-[0_0_25px_rgba(16,185,129,0.3)]',
        amber: 'shadow-[0_0_15px_rgba(245,158,11,0.15)] border-amber-500/20 hover:border-amber-400/50 hover:shadow-[0_0_25px_rgba(245,158,11,0.3)]',
        red: 'shadow-[0_0_15px_rgba(239,68,68,0.15)] border-red-500/20 hover:border-red-400/50 hover:shadow-[0_0_25px_rgba(239,68,68,0.3)]',
        white: 'shadow-[0_0_15px_rgba(255,255,255,0.10)] border-white/20 hover:border-white/50 hover:shadow-[0_0_25px_rgba(255,255,255,0.2)]',
    };

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className={cn(
                "relative backdrop-blur-xl bg-slate-900/60 rounded-xl border transition-all duration-500",
                glowStyles[glowColor],
                className
            )}
        >
            <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent opacity-0 hover:opacity-100 transition-opacity duration-500 rounded-xl" />

            {/* Corner Accents */}
            <div className={cn("absolute top-0 left-0 w-8 h-[1px]",
                glowColor === 'cyan' ? 'bg-cyan-500' :
                    glowColor === 'green' ? 'bg-emerald-500' :
                        glowColor === 'amber' ? 'bg-amber-500' :
                            glowColor === 'white' ? 'bg-white' : 'bg-red-500'
            )} />
            <div className={cn("absolute top-0 left-0 w-[1px] h-8",
                glowColor === 'cyan' ? 'bg-cyan-500' :
                    glowColor === 'green' ? 'bg-emerald-500' :
                        glowColor === 'amber' ? 'bg-amber-500' :
                            glowColor === 'white' ? 'bg-white' : 'bg-red-500'
            )} />

            {title && (
                <div className="px-6 py-4 border-b border-white/5 flex items-center justify-between">
                    <h3 className="text-sm font-bold tracking-widest uppercase text-white/90 font-mono">
                        {title}
                    </h3>
                    <div className={cn("w-2 h-2 rounded-full animate-pulse",
                        glowColor === 'cyan' ? 'bg-cyan-400' :
                            glowColor === 'green' ? 'bg-emerald-400' :
                                glowColor === 'amber' ? 'bg-amber-400' :
                                    glowColor === 'white' ? 'bg-white' : 'bg-red-400'
                    )} />
                </div>
            )}

            <div className="p-6 relative z-10">
                {children}
            </div>
        </motion.div>
    );
}
