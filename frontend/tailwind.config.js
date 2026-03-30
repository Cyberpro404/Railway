/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        // Project Gandhiva SCADA Theme
        background: "#1a1a1a",
        card: "#2d2d2d",
        primary: "#0078d4",
        "primary-foreground": "#ffffff",
        success: "#4caf50",
        warning: "#ff9800",
        critical: "#f44336",
        text: "#e0e0e0",
        "text-muted": "#a0a0a0",
        border: "#404040",
        input: "#404040",
        ring: "#0078d4",
      },
      borderRadius: {
        lg: "8px",
        md: "6px",
        sm: "4px",
      },
      fontFamily: {
        sans: ['Sora', 'Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
        display: ['Sora', 'Inter', 'sans-serif'],
      },
      fontSize: {
        h1: ['40px', { lineHeight: '1.2', fontWeight: '800', letterSpacing: '-0.02em' }],
        h2: ['28px', { lineHeight: '1.3', fontWeight: '700', letterSpacing: '-0.01em' }],
        h3: ['20px', { lineHeight: '1.4', fontWeight: '600' }],
        body: ['16px', { lineHeight: '1.6', fontWeight: '400' }],
        metric: ['24px', { lineHeight: '1.2', fontWeight: '600', fontFamily: 'JetBrains Mono' }],
        sm: ['14px', { lineHeight: '1.5', fontWeight: '400' }],
        xs: ['12px', { lineHeight: '1.4', fontWeight: '500' }],
      },
      keyframes: {
        "accordion-down": {
          from: { height: 0 },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: 0 },
        },
        pulse: {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.5 },
        },
        "pulse-cyan": {
          '0%, 100%': { opacity: 1, boxShadow: '0 0 10px rgba(0, 212, 255, 0.5)' },
          '50%': { opacity: 0.7, boxShadow: '0 0 20px rgba(0, 212, 255, 0.8)' },
        },
        "fade-in": {
          from: { opacity: 0 },
          to: { opacity: 1 },
        },
        "fade-in-up": {
          from: { opacity: 0, transform: 'translateY(20px)' },
          to: { opacity: 1, transform: 'translateY(0)' },
        },
        "slide-in-from-top": {
          from: { transform: 'translateY(-100%)', opacity: 0 },
          to: { transform: 'translateY(0)', opacity: 1 },
        },
        "shimmer": {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        "bounce-in": {
          '0%': { opacity: 0, transform: 'scale(0.9)' },
          '50%': { opacity: 1, transform: 'scale(1.05)' },
          '100%': { opacity: 1, transform: 'scale(1)' },
        },
        "glow": {
          '0%, 100%': { opacity: 1, boxShadow: '0 0 10px rgba(0, 212, 255, 0.3)' },
          '50%': { opacity: 0.8, boxShadow: '0 0 30px rgba(0, 212, 255, 0.6)' },
        },
        "float": {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        "slideInX": {
          from: { opacity: 0, transform: 'translateX(-20px)' },
          to: { opacity: 1, transform: 'translateX(0)' },
        },
        "scale-in": {
          from: { opacity: 0, transform: 'scale(0.9)' },
          to: { opacity: 1, transform: 'scale(1)' },
        },
        "rotate-in": {
          from: { opacity: 0, transform: 'rotate(-5deg) scale(0.95)' },
          to: { opacity: 1, transform: 'rotate(0deg) scale(1)' },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "pulse-cyan": "pulse-cyan 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "fade-in": "fade-in 0.5s ease-in",
        "fade-in-up": "fade-in-up 0.6s cubic-bezier(0.4, 0, 0.2, 1)",
        "slide-in-from-top": "slide-in-from-top 0.3s ease-out",
        "shimmer": "shimmer 2s infinite",
        "bounce-in": "bounce-in 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)",
        "glow": "glow 2s ease-in-out infinite",
        "float": "float 4s ease-in-out infinite",
        "slideInX": "slideInX 0.5s cubic-bezier(0.4, 0, 0.2, 1)",
        "scale-in": "scale-in 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
        "rotate-in": "rotate-in 0.5s cubic-bezier(0.4, 0, 0.2, 1)",
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}

