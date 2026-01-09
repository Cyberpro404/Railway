
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { useEffect } from 'react'
import Layout from './components/Layout'
import ConnectionTab from './dashboard/Connection'
import ExecutiveTab from './dashboard/Executive'
import AnalyticsTab from './dashboard/Analytics'
import MLTab from './dashboard/ML'
import DataTab from './dashboard/Data'
import LogsTab from './dashboard/Logs'
import AlertsTab from './dashboard/Alerts'
import ThresholdsTab from './dashboard/Thresholds'
import ControlTab from './dashboard/Control'
import { wsClient } from './lib/websocket'

function App() {
  useEffect(() => {
    // Connect WebSocket on app start
    wsClient.connect()
    
    return () => {
      wsClient.disconnect()
    }
  }, [])

  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<ConnectionTab />} />
          <Route path="/connection" element={<ConnectionTab />} />
          <Route path="/executive" element={<ExecutiveTab />} />
          <Route path="/analytics" element={<AnalyticsTab />} />
          <Route path="/ml" element={<MLTab />} />
          <Route path="/data" element={<DataTab />} />
          <Route path="/logs" element={<LogsTab />} />
          <Route path="/alerts" element={<AlertsTab />} />
          <Route path="/thresholds" element={<ThresholdsTab />} />
          <Route path="/control" element={<ControlTab />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App

