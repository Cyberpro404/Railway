$base = "http://localhost:8000"; $p = 0; $f = 0

function ep($m, $u, $b = $null) {
    try {
        $h = @{ Uri = "$base$u"; Method = $m; ContentType = "application/json"; TimeoutSec = 12 }
        if ($b) { $h.Body = ($b | ConvertTo-Json -Compress -Depth 5) }
        $null = Invoke-RestMethod @h
        Write-Host "PASS  $m $u" -ForegroundColor Green
        $script:p++
    } catch {
        $c = $_.Exception.Response.StatusCode.value__
        if (-not $c) { $c = "ERR" }
        Write-Host "FAIL  $m $u  [$c]" -ForegroundColor Red
        $script:f++
    }
}

ep GET "/"
ep GET "/health"
ep GET "/api/v1/health"
ep GET "/api/v1/demo/status"
ep POST "/api/v1/demo/toggle"
ep POST "/api/v1/demo/toggle"
ep GET "/api/v1/connection/status"
ep POST "/api/v1/connection/scan"
ep POST "/api/v1/connection/connect" @{ port = "COM3"; baud = 19200; slave_id = 1 }
ep POST "/api/v1/connection/connect" @{ protocol = "TCP"; host = "192.168.0.1"; port = 502; slave_id = 1 }
ep POST "/api/v1/connection/connect" @{ protocol = "RTU"; port = "COM3"; baudrate = 19200; slave_id = 1 }
ep POST "/api/v1/connection/disconnect"
ep POST "/api/v1/connection/scan-network"
ep GET "/api/v1/interfaces"
ep GET "/api/v1/network/ranges"
ep GET "/api/v1/connected"
ep POST "/api/v1/scan/network" @{ network_range = "192.168.0.0/30"; scan_type = "quick"; timeout = 0.3 }

try {
    $sc = Invoke-RestMethod -Uri "$base/api/v1/scan/network" -Method POST -ContentType "application/json" -Body '{"network_range":"192.168.0.0/30","timeout":0.3}'
    Write-Host "PASS  POST /api/v1/scan/network (inline)" -ForegroundColor Green
    $script:p++
    ep GET "/api/v1/scan/$($sc.scan_id)"
} catch {
    Write-Host "FAIL  POST /api/v1/scan/network (inline) [ERR]" -ForegroundColor Red
    $script:f++
}

ep POST "/api/v1/connect" @{ ip = "192.168.0.1"; port = 502; slave_id = 1; connection_type = "tcp" }
ep DELETE "/api/v1/disconnect/device_192.168.0.1_1"
ep GET "/api/v1/thresholds/get"
ep POST "/api/v1/thresholds/save" @(@{ id = "t1"; parameter = "z_rms"; parameterLabel = "Z RMS"; unit = "mm/s"; minLimit = 1.5; maxLimit = 4.0 })
ep GET "/api/v1/controller-thresholds/get"
ep POST "/api/v1/controller-thresholds/save" @(@{ id = "c1"; parameter = "z_rms"; warningLimit = 2.0; alertLimit = 4.0 })
ep GET "/api/v1/alerts"
ep GET "/api/v1/alerts/active"

try {
    $al = Invoke-RestMethod -Uri "$base/api/v1/alerts" -Method POST -ContentType "application/json" -Body '{"alert_type":"test","severity":"warning","message":"Test"}'
    Write-Host "PASS  POST /api/v1/alerts" -ForegroundColor Green
    $script:p++
    ep POST "/api/v1/alerts/$($al.id)/acknowledge"
    ep DELETE "/api/v1/alerts/$($al.id)"
} catch {
    Write-Host "FAIL  alert CRUD [ERR]" -ForegroundColor Red
    $script:f++
}

ep POST "/api/v1/alerts/clear"
ep GET "/api/v1/data/chart"
ep GET "/api/v1/data/batch?limit=50"
ep GET "/api/v1/metrics"
ep GET "/api/v1/logs/offline?file=app&limit=20"
ep GET "/api/v1/logs/offline/stats?file=app"
ep GET "/api/v1/logs/offline?file=errors"
ep GET "/api/v1/logs/offline/stats?file=modbus"

Write-Host ""
Write-Host "=== WebSocket Test ===" -ForegroundColor Cyan
$py = "c:\Users\athar\Desktop\VS Code\Rail V4\.venv\Scripts\python.exe"
$wsCode = @"
import asyncio, json, websockets

async def t():
    async with websockets.connect('ws://localhost:8000/api/v2/ws/realtime') as ws:
        msg = await asyncio.wait_for(ws.recv(), timeout=4)
        d = json.loads(msg)
        assert 'sensor_data' in d and 'z_rms' in d['sensor_data'], 'bad shape'
        print('OK')

asyncio.run(t())
"@
$wsResult = & $py -c $wsCode 2>&1
if ($wsResult -match "OK") {
    Write-Host "PASS  WS /api/v2/ws/realtime" -ForegroundColor Green
    $script:p++
} else {
    Write-Host "FAIL  WS: $wsResult" -ForegroundColor Red
    $script:f++
}

Write-Host ""
Write-Host "=========================================="
$color = if ($f -eq 0) { "Green" } else { "Yellow" }
Write-Host "  FINAL  Passed=$p  Failed=$f" -ForegroundColor $color
Write-Host "=========================================="
