import { useState, useEffect } from 'react'
import Card from '@/components/ui/Card'
import { AnimatedCard, FadeIn, PulseIndicator } from '@/components/ui/AnimatedComponents'
import { Power, Settings, Activity, AlertTriangle, CheckCircle } from 'lucide-react'

interface DemoStatus {
  demo_mode: boolean
  modbus_connected: boolean
  active_connections: number
  message: string
}

export default function DemoModeControl() {
  const [demoStatus, setDemoStatus] = useState<DemoStatus | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchDemoStatus()
    const interval = setInterval(fetchDemoStatus, 5000) // Update every 5 seconds
    return () => clearInterval(interval)
  }, [])

  const fetchDemoStatus = async () => {
    try {
      const response = await fetch('/api/v1/demo/status')
      const data = await response.json()
      setDemoStatus(data)
    } catch (error) {
      console.error('Failed to fetch demo status:', error)
    }
  }

  const toggleDemoMode = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/v1/demo/toggle', { method: 'POST' })
      const data = await response.json()
      setDemoStatus({
        demo_mode: data.demo_mode,
        modbus_connected: false,
        active_connections: 0,
        message: data.message
      })
    } catch (error) {
      console.error('Failed to toggle demo mode:', error)
    } finally {
      setLoading(false)
    }
  }

  if (!demoStatus) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="w-8 h-8 border-4 border-primary/20 border-t-primary rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <AnimatedCard delay={0.1}>
      <Card className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Settings className="w-6 h-6 text-primary" />
            <h3 className="text-lg font-semibold text-text">Demo Mode Control</h3>
          </div>
          <div className="flex items-center gap-2">
            <PulseIndicator 
              active={demoStatus.demo_mode} 
              color={demoStatus.demo_mode ? 'warning' : 'success'} 
            />
            <span className={`text-sm font-medium ${
              demoStatus.demo_mode ? 'text-warning' : 'text-success'
            }`}>
              {demoStatus.demo_mode ? 'DEMO ACTIVE' : 'LIVE MODE'}
            </span>
          </div>
        </div>

        <div className="space-y-4">
          {/* Status Information */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center p-4 bg-background/50 rounded-lg">
              <Activity className="w-6 h-6 text-primary mx-auto mb-2" />
              <p className="text-sm text-text-muted mb-1">Mode</p>
              <p className="font-semibold text-text">
                {demoStatus.demo_mode ? 'Demo' : 'Live'}
              </p>
            </div>
            <div className="text-center p-4 bg-background/50 rounded-lg">
              <div className={`w-6 h-6 mx-auto mb-2 rounded-full ${
                demoStatus.modbus_connected ? 'bg-success' : 'bg-error'
              }`} />
              <p className="text-sm text-text-muted mb-1">Modbus</p>
              <p className="font-semibold text-text">
                {demoStatus.modbus_connected ? 'Connected' : 'Disconnected'}
              </p>
            </div>
            <div className="text-center p-4 bg-background/50 rounded-lg">
              <div className="w-6 h-6 bg-primary rounded mx-auto mb-2 flex items-center justify-center">
                <span className="text-xs text-white font-bold">
                  {demoStatus.active_connections}
                </span>
              </div>
              <p className="text-sm text-text-muted mb-1">Connections</p>
              <p className="font-semibold text-text">Active</p>
            </div>
          </div>

          {/* Control Button */}
          <div className="flex justify-center">
            <button
              onClick={toggleDemoMode}
              disabled={loading}
              className={`px-6 py-3 rounded-lg font-semibold transition-all flex items-center gap-2 ${
                demoStatus.demo_mode
                  ? 'bg-success/10 border border-success/30 text-success hover:bg-success/20'
                  : 'bg-warning/10 border border-warning/30 text-warning hover:bg-warning/20'
              } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                  Switching...
                </>
              ) : (
                <>
                  <Power className="w-4 h-4" />
                  {demoStatus.demo_mode ? 'Enable Live Mode' : 'Enable Demo Mode'}
                </>
              )}
            </button>
          </div>

          {/* Status Message */}
          <div className={`p-4 rounded-lg border ${
            demoStatus.demo_mode 
              ? 'bg-warning/5 border-warning/30' 
              : 'bg-success/5 border-success/30'
          }`}>
            <div className="flex items-center gap-2">
              {demoStatus.demo_mode ? (
                <AlertTriangle className="w-5 h-5 text-warning" />
              ) : (
                <CheckCircle className="w-5 h-5 text-success" />
              )}
              <p className="text-sm text-text">
                {demoStatus.message}
              </p>
            </div>
          </div>

          {/* Information */}
          <div className="text-xs text-text-muted space-y-1">
            <p>• <strong>Demo Mode:</strong> Generates realistic synthetic data for all 21 Modbus registers</p>
            <p>• <strong>Live Mode:</strong> Reads actual data from connected Modbus device</p>
            <p>• <strong>Auto-Switch:</strong> System automatically falls back to demo mode after 3 consecutive connection failures</p>
          </div>
        </div>
      </Card>
    </AnimatedCard>
  )
}
