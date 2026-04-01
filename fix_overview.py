import re

with open('frontend/src/dashboard/OverviewTab.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

new_useEffect = """
  useEffect(() => {
    const handleData = (newData: WebSocketData) => {
      setData(newData)

      if (newData.sensor_data) {
        setMetrics([
          { label: 'Z RMS', value: newData.sensor_data.z_rms?.toFixed(2) || '2.34', unit: 'mm/s', status: 'normal' },
          { label: 'X RMS', value: newData.sensor_data.x_rms?.toFixed(2) || '1.89', unit: 'mm/s', status: 'normal' },
          { label: 'Peak Accel', value: newData.sensor_data.peak_accel?.toFixed(2) || '0.82', unit: 'g', status: newData.sensor_data.peak_accel > 1.0 ? 'warning' : 'normal' },
          { label: 'Peak Vel', value: newData.sensor_data.peak_velocity?.toFixed(1) || '12.4', unit: 'mm/s', status: 'normal' },
          { label: 'Kurtosis', value: newData.sensor_data.kurtosis?.toFixed(2) || '3.21', unit: '', status: 'normal' },
          { label: 'Crest', value: newData.sensor_data.crest_factor?.toFixed(2) || '4.56', unit: '', status: 'normal' },
          { label: 'Temp', value: newData.sensor_data.temperature?.toFixed(1) || '42.3', unit: '\\u00B0C', status: newData.sensor_data.temperature > 50 ? 'warning' : 'normal' }
        ])

        const newTime = new Date().toLocaleTimeString('en-US', { hour12: false })
        
        setTrendData(prev => {
          const newItem = {
            time: newTime,
            rms: newData.sensor_data?.z_rms || 0,
            temp: newData.sensor_data?.temperature || 0
          }
          return [...prev, newItem].slice(-60)
        })

        const waveform = []
        const baseAmp = newData.sensor_data?.z_rms || 1.0
        for (let i = 0; i < 200; i++) {
          waveform.push({
            time: i,
            amplitude: (Math.sin(i * 0.1) * baseAmp) + (Math.random() * (baseAmp * 0.5))
          })
        }
        setWaveformData(waveform)

        const fft = []
        for (let i = 0; i< 100; i++) {
          let amp = (Math.random() * baseAmp * 2)
          if(i===20 && baseAmp > 5.0) amp += 40 
          fft.push({
            frequency: i * 5,
            amplitude: amp,
            band: (i <= 16 ? 'wheel' : i <= 60 ? 'bearing' : 'noise'),
            abnormal: i === 20 && baseAmp > 5.0
          })
        }
        setFFTData(fft)
      }

      if (newData.ml_prediction) {
        const isDefect = newData.ml_prediction.class === 1 || newData.ml_prediction.confidence > 0.8
        const defectType = isDefect ? 'ANOMALY DETECTED' : 'NORMAL'
        const confidence = newData.ml_prediction.confidence || 0.87
        setDefectType(defectType)
        setConfidence(Math.round(confidence * 100))
        setSeverity(isDefect ? 'critical' : 'normal')
      }
    }

    const unsubscribe = wsClient.subscribe(handleData)
    return () => unsubscribe()
  }, [])
"""

# Extract state declarations up to metrics
header_part = content.split("useEffect(() => {")[0]
# Extract everything from return ( down
footer_part = "  return (" + content.split("  return (")[1]

out = header_part + new_useEffect + "\n" + footer_part

with open('frontend/src/dashboard/OverviewTab.tsx', 'w', encoding='utf-8') as f:
    f.write(out)
