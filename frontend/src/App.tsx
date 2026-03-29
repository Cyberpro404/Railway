import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { wsClient } from './lib/websocket'
import Layout from './components/Layout'
import NewDashboard from './dashboard/NewDashboard'
import AnalyticsTab from './dashboard/AnalyticsSimple'
import MLTab from './dashboard/ML'
import AlertsEnhanced from './dashboard/AlertsEnhanced'
import ConnectionTab from './dashboard/Connection'
import ThresholdsSimple from './dashboard/ThresholdsSimple'
import LogsDiagnostics from './dashboard/LogsDiagnostics'
import NotFound from './pages/NotFound'

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
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<NewDashboard />} />
          <Route path="/analytics" element={<AnalyticsTab />} />
          <Route path="/ml" element={<MLTab />} />
          <Route path="/alerts" element={<AlertsEnhanced />} />
          <Route path="/connection" element={<ConnectionTab />} />
          <Route path="/settings" element={<ThresholdsSimple />} />
          <Route path="/logs" element={<LogsDiagnostics />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </Router>
  )
}

export default App

