import re

with open('frontend/src/dashboard/DeviceManagementTab.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace /api/v1/devices/... with the correct endpoints
content = content.replace("fetch('/api/v1/devices/interfaces')", "fetch('/api/v1/connection/status')") 
content = content.replace("fetch('/api/v1/devices/network/ranges')", "fetch('/api/v1/connection/status')")
content = content.replace("fetch('/api/v1/devices/connected')", "fetch('/api/v1/connection/status')")
content = content.replace("fetch('/api/v1/devices/scan/network'", "fetch('/api/v1/connection/scan-network'")
content = content.replace("fetch(/api/v1/devices/scan/)", "fetch('/api/v1/connection/status')")
content = content.replace("fetch('/api/v1/devices/connect'", "fetch('/api/v1/connection/connect'")
content = content.replace("fetch(/api/v1/devices/disconnect/", "fetch('/api/v1/connection/disconnect'")
content = content.replace("fetch(/api/v1/devices/test/", "fetch('/api/v1/connection/status'")

with open('frontend/src/dashboard/DeviceManagementTab.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
