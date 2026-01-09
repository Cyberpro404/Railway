import { useState } from 'react'
import { Database, Upload, Download, Trash2, Eye } from 'lucide-react'

export default function DataTab() {
  const [totalSamples] = useState(1247)
  const [normalSamples] = useState(885)
  const [faultySamples] = useState(362)

  const normalPercent = (normalSamples / totalSamples * 100).toFixed(1)
  const faultyPercent = (faultySamples / totalSamples * 100).toFixed(1)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-h1 text-text mb-2">DATA MANAGEMENT</h1>
        <p className="text-text-muted">Training Dataset Browser & Management</p>
      </div>

      <div className="bg-card border border-border rounded-lg p-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <div>
            <div className="text-sm text-text-muted mb-2">Total Samples</div>
            <div className="text-3xl font-mono font-bold text-text">{totalSamples.toLocaleString()}</div>
          </div>
          <div>
            <div className="text-sm text-text-muted mb-2">Normal</div>
            <div className="text-3xl font-mono font-bold text-success">{normalSamples.toLocaleString()}</div>
            <div className="text-sm text-text-muted mt-1">{normalPercent}%</div>
          </div>
          <div>
            <div className="text-sm text-text-muted mb-2">Faulty</div>
            <div className="text-3xl font-mono font-bold text-critical">{faultySamples.toLocaleString()}</div>
            <div className="text-sm text-text-muted mt-1">{faultyPercent}%</div>
          </div>
        </div>

        <div className="flex flex-wrap gap-3">
          <button className="px-4 py-2 bg-primary/10 border border-primary/30 rounded-lg text-primary hover:bg-primary/20 transition-colors flex items-center gap-2">
            <Upload className="w-4 h-4" />
            IMPORT CSV
          </button>
          <button className="px-4 py-2 bg-card border border-border rounded-lg text-text hover:bg-primary/10 hover:border-primary/30 transition-colors flex items-center gap-2">
            <Download className="w-4 h-4" />
            EXPORT ALL
          </button>
          <button className="px-4 py-2 bg-card border border-border rounded-lg text-text hover:bg-primary/10 hover:border-primary/30 transition-colors flex items-center gap-2">
            <Trash2 className="w-4 h-4" />
            DATA CLEANUP
          </button>
          <button className="px-4 py-2 bg-card border border-border rounded-lg text-text hover:bg-primary/10 hover:border-primary/30 transition-colors flex items-center gap-2">
            <Eye className="w-4 h-4" />
            PREVIEW
          </button>
        </div>
      </div>

      <div className="bg-card border border-border rounded-lg p-6">
        <h3 className="text-h2 text-text mb-4">Dataset Statistics</h3>
        <div className="space-y-4">
          <div>
            <div className="text-sm text-text-muted mb-2">Data Quality</div>
            <div className="flex items-center gap-2">
              <div className="flex-1 bg-border rounded-full h-2">
                <div className="bg-success h-2 rounded-full" style={{ width: '94%' }} />
              </div>
              <span className="text-sm text-text-muted">94%</span>
            </div>
          </div>
          <div>
            <div className="text-sm text-text-muted mb-2">Last Updated</div>
            <div className="text-text font-mono">{new Date().toLocaleString()}</div>
          </div>
        </div>
      </div>
    </div>
  )
}

