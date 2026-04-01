import re

with open('src/dashboard/OverviewTab.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('newData.sensor_data.waveform', '(newData.sensor_data as any).waveform')
text = text.replace('newData.sensor_data.fft', '(newData.sensor_data as any).fft')

with open('src/dashboard/OverviewTab.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
