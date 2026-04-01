with open('src/dashboard/OverviewTab.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

import re

new_handleData = """
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
          
          setTrendData(prev => {
            const newItem = {
              time: new Date().toLocaleTimeString('en-US', { hour12: false }),
              rms: newData.sensor_data?.z_rms || 0,
              temp: newData.sensor_data?.temperature || 0
            }
            return [...prev, newItem].slice(-60)
          })
          
          const baseAmp = newData.sensor_data?.z_rms || 1.0
          setWaveformData(Array.from({length: 100}, (_, i) => ({
            time: i,
            amplitude: (Math.sin(i * 0.1) * baseAmp) + (Math.random() * (baseAmp * 0.5))
          })))
          
          setFFTData(Array.from({length: 100}, (_, i) => {
            let amp = (Math.random() * baseAmp * 2)
            if(i===20 && baseAmp > 5.0) amp += 40 
            return {
              frequency: i * 5,
              amplitude: amp,
              band: i <= 16 ? 'wheel' : i <= 60 ? 'bearing' : 'noise',
              abnormal: i === 20 && baseAmp > 5.0
            }
          }))
        }
"""

text = re.sub(r'if \(newData\.sensor_data\) \{.*?(?=\n\s*if \(newData\.ml_prediction\))', new_handleData, text, flags=re.DOTALL)
text = re.sub(r'useEffect\(\(\) => \{\n\s*// Simulate data.*?\n\s*setFFTData\(fft\)\n\s*setWaveformData\(waveform\)\n\s*\}\n\s*const timer = setInterval.*?\n\s*return \(\) => clearInterval.*?\n\s*\}, \[\]\)', '', text, flags=re.DOTALL)

with open('src/dashboard/OverviewTab.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
