import { useState } from 'react'
import { Database, RefreshCw, Download, Settings } from 'lucide-react'

export default function ControlTab() {
  const [pollingRate, setPollingRate] = useState('1Hz')
  const [theme, setTheme] = useState('Dark')
  const [soundVolume, setSoundVolume] = useState(50)

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div>
        <h1 className="text-h1 text-text mb-2 font-bold tracking-tight">SYSTEM CONTROL</h1>
        <p className="text-text-muted font-medium">Sensor Config • ML Controls • Display Options</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sensor Configuration */}
        <div className="bg-card border border-border rounded-lg p-6 card-hover shadow-xl">
          <h3 className="text-h2 text-text mb-4 font-bold">Sensor Configuration</h3>
          <div className="space-y-4">
            <div>
              <label className="text-sm text-text-muted block mb-2">Polling Rate</label>
              <select
                value={pollingRate}
                onChange={(e) => setPollingRate(e.target.value)}
                className="w-full px-3 py-2 bg-background border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-primary/50"
              >
                <option>0.5Hz</option>
                <option>1Hz</option>
                <option>2Hz</option>
                <option>5Hz</option>
              </select>
            </div>
            <div>
              <label className="text-sm text-text-muted block mb-2">Baud Rate</label>
              <select className="w-full px-3 py-2 bg-background border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-primary/50">
                <option>9600</option>
                <option>19200</option>
                <option>38400</option>
                <option>115200</option>
              </select>
            </div>
            <div>
              <label className="text-sm text-text-muted block mb-2">Slave ID</label>
              <input
                type="number"
                defaultValue={1}
                className="w-full px-3 py-2 bg-background border border-border rounded-lg text-text font-mono focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
            </div>
          </div>
        </div>

        {/* Display Options */}
        <div className="bg-card border border-border rounded-lg p-6 card-hover shadow-xl">
          <h3 className="text-h2 text-text mb-4 font-bold">Display Options</h3>
          <div className="space-y-4">
            <div>
              <label className="text-sm text-text-muted block mb-2">Theme</label>
              <select
                value={theme}
                onChange={(e) => setTheme(e.target.value)}
                className="w-full px-3 py-2 bg-background border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-primary/50"
              >
                <option>Dark</option>
                <option>Light</option>
                <option>Auto</option>
              </select>
            </div>
            <div>
              <label className="text-sm text-text-muted block mb-2">Sound Volume</label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={soundVolume}
                  onChange={(e) => setSoundVolume(parseInt(e.target.value))}
                  className="flex-1"
                />
                <span className="text-text font-mono min-w-[50px] text-right">{soundVolume}%</span>
              </div>
            </div>
            <div>
              <label className="text-sm text-text-muted block mb-2">Chart Update Rate</label>
              <select className="w-full px-3 py-2 bg-background border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-primary/50">
                <option>Real-time (1Hz)</option>
                <option>Fast (5Hz)</option>
                <option>Slow (0.5Hz)</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* ML Controls */}
      <div className="bg-card border border-border rounded-lg p-6 card-hover shadow-xl">
        <h3 className="text-h2 text-text mb-4 font-bold">ML Controls</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button className="px-4 py-2 bg-card border border-border rounded-lg text-text hover:bg-primary/10 hover:border-primary/30 transition-colors">
            Reload Model
          </button>
          <button className="px-4 py-2 bg-card border border-border rounded-lg text-text hover:bg-primary/10 hover:border-primary/30 transition-colors">
            Train New Model
          </button>
          <button className="px-4 py-2 bg-card border border-border rounded-lg text-text hover:bg-primary/10 hover:border-primary/30 transition-colors">
            Model Statistics
          </button>
        </div>
      </div>

      {/* System Actions */}
      <div className="bg-card border border-border rounded-lg p-6 card-hover shadow-xl">
        <h3 className="text-h2 text-text mb-4 font-bold">System Actions</h3>
        <div className="flex flex-wrap gap-3">
          <button className="px-5 py-2.5 bg-primary/10 border border-primary/30 rounded-lg text-primary hover:bg-primary/20 hover:shadow-lg hover:scale-105 transition-all duration-200 flex items-center gap-2 font-semibold">
            <Database className="w-4 h-4" />
            DATABASE BACKUP
          </button>
          <button className="px-5 py-2.5 bg-card border border-border rounded-lg text-text hover:bg-primary/10 hover:border-primary/30 hover:shadow-lg hover:scale-105 transition-all duration-200 flex items-center gap-2 font-semibold">
            <RefreshCw className="w-4 h-4" />
            RESTART SERVICES
          </button>
          <button className="px-5 py-2.5 bg-card border border-border rounded-lg text-text hover:bg-primary/10 hover:border-primary/30 hover:shadow-lg hover:scale-105 transition-all duration-200 flex items-center gap-2 font-semibold">
            <Download className="w-4 h-4" />
            EXPORT CONFIG
          </button>
          <button className="px-5 py-2.5 bg-card border border-border rounded-lg text-text hover:bg-primary/10 hover:border-primary/30 hover:shadow-lg hover:scale-105 transition-all duration-200 flex items-center gap-2 font-semibold">
            <Settings className="w-4 h-4" />
            ADVANCED SETTINGS
          </button>
        </div>
      </div>
    </div>
  )
}

