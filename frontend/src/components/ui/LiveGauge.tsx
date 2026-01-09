import { useEffect, useRef } from 'react'
import { cn } from '@/lib/utils'

interface LiveGaugeProps {
  value: number
  min: number
  max: number
  label: string
  unit?: string
  thresholds?: { warn: number; alarm: number }
  size?: 'sm' | 'md' | 'lg'
}

export default function LiveGauge({
  value,
  min,
  max,
  label,
  unit,
  thresholds,
  size = 'md'
}: LiveGaugeProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const sizeMap = { sm: 120, md: 180, lg: 240 }
    const canvasSize = sizeMap[size]
    canvas.width = canvasSize
    canvas.height = canvasSize
    const centerX = canvasSize / 2
    const centerY = canvasSize / 2
    const radius = canvasSize / 2 - 20

    // Clear canvas
    ctx.clearRect(0, 0, canvasSize, canvasSize)

    // Draw arc background
    ctx.strokeStyle = '#1A2332'
    ctx.lineWidth = 20
    ctx.beginPath()
    ctx.arc(centerX, centerY, radius, Math.PI, 0, false)
    ctx.stroke()

    // Draw threshold zones
    if (thresholds) {
      const warnAngle = Math.PI - ((thresholds.warn - min) / (max - min)) * Math.PI
      const alarmAngle = Math.PI - ((thresholds.alarm - min) / (max - min)) * Math.PI

      // Warning zone (from warn to alarm)
      if (thresholds.warn < thresholds.alarm) {
        ctx.strokeStyle = '#F59E0B'
        ctx.lineWidth = 20
        ctx.beginPath()
        ctx.arc(centerX, centerY, radius, warnAngle, alarmAngle, false)
        ctx.stroke()
      }

      // Alarm zone (from alarm to max)
      ctx.strokeStyle = '#EF4444'
      ctx.lineWidth = 20
      ctx.beginPath()
      ctx.arc(centerX, centerY, radius, alarmAngle, 0, false)
      ctx.stroke()
    }

    // Draw value arc
    const normalizedValue = Math.max(0, Math.min(1, (value - min) / (max - min)))
    const valueAngle = Math.PI - normalizedValue * Math.PI

    ctx.strokeStyle = value > (thresholds?.alarm || max) ? '#EF4444' :
                     value > (thresholds?.warn || max) ? '#F59E0B' : '#00D4FF'
    ctx.lineWidth = 20
    ctx.beginPath()
    ctx.arc(centerX, centerY, radius, Math.PI, valueAngle, false)
    ctx.stroke()

    // Draw value text
    ctx.fillStyle = '#E5E7EB'
    ctx.font = 'bold 24px JetBrains Mono'
    ctx.textAlign = 'center'
    ctx.fillText(value.toFixed(2), centerX, centerY - 10)
    
    if (unit) {
      ctx.font = '14px Inter'
      ctx.fillStyle = '#9CA3AF'
      ctx.fillText(unit, centerX, centerY + 15)
    }

    // Draw label
    ctx.font = '12px Inter'
    ctx.fillStyle = '#9CA3AF'
    ctx.fillText(label, centerX, canvasSize - 10)
  }, [value, min, max, label, unit, thresholds, size])

  return (
    <div className="flex flex-col items-center">
      <canvas ref={canvasRef} className="block" />
    </div>
  )
}

