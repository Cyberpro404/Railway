import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { wsClient } from './lib/websocket'
import Layout from './components/Layout'
import OverviewTab from './dashboard/OverviewTab'
import AnalyticsTab from './dashboard/AnalyticsSimple'
import MLTab from './dashboard/ML'
import AlertsEnhanced from './dashboard/AlertsEnhanced'
import ConnectionTab from './dashboard/Connection'
import ThresholdsSimple from './dashboard/ThresholdsSimple'
import LogsDiagnostics from './dashboard/LogsDiagnostics'
import DeviceManagementTab from './dashboard/DeviceManagementTab'
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
          <Route path="/" element={<OverviewTab />} />
          <Route path="/live" element={<AnalyticsTab />} />
          <Route path="/fleet" element={<MLTab />} />
          <Route path="/defects" element={<AlertsEnhanced />} />
          <Route path="/history" element={<ThresholdsSimple />} />
          <Route path="/alerts" element={<AlertsEnhanced />} />
          <Route path="/reports" element={<LogsDiagnostics />} />

          <Route path="/settings" element={<ThresholdsSimple />} />
          <Route path="/devices" element={<DeviceManagementTab />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </Router>
  )
}

export default App


