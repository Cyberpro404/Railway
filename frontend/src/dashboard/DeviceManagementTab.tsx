import React, { useState, useEffect } from 'react';
import { Activity, Wifi, Server, Search, RefreshCw, LogOut } from 'lucide-react';
import { wsClient, WebSocketData } from '../lib/websocket';

const COLORS = {
  bg: '#0a0f1a',
  bgPanel: '#1e293b',
  border: '#334155',
  text: '#e2e8f0',
  textMuted: '#94a3b8',
  primary: '#3b82f6',
  success: '#10b981',
  warning: '#f59e0b',
  critical: '#ef4444'
}

export default function DeviceManagementTab() {
  const [connectionType, setConnectionType] = useState<'serial' | 'tcp'>('tcp');
  
  // TCP State
  const [subnet, setSubnet] = useState('192.168.0');
  const [ipAddress, setIpAddress] = useState('192.168.0.1');
  const [useVpn, setUseVpn] = useState(false);
  const [tcpDevices, setTcpDevices] = useState<any[]>([]);
  
  // Serial State
  const [comPort, setComPort] = useState('');
  const [baudRate, setBaudRate] = useState('19200');
  const [serialDevices, setSerialDevices] = useState<any[]>([]);

  // Global State
  const [isScanning, setIsScanning] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectedState, setConnectedState] = useState(false);
  const [statusMsg, setStatusMsg] = useState('Not Connected');
  
  // Fetch initial connection status from WS
  useEffect(() => {
    const handleData = (newData: WebSocketData) => {
      if (newData.connection_status) {
        const isConn = newData.connection_status.connected;
        setConnectedState(isConn);
        const sensorStatus = newData.sensor_data?.sensor_status;
        if (isConn && sensorStatus === 'live') {
          setStatusMsg(`Connected to ${newData.connection_status.port || 'device'} — live polling active`);
        } else if (isConn && sensorStatus === 'connecting') {
          setStatusMsg(`Connecting to ${newData.connection_status.port || 'device'} — awaiting first poll…`);
        } else if (!isConn && sensorStatus === 'stale') {
          setStatusMsg(`Reconnecting to ${newData.connection_status.port || 'device'} — showing last known data`);
        } else if (!isConn) {
          setStatusMsg('Not Connected — enter device IP and click Connect');
        }
      }
    };
    const unsubscribe = wsClient.subscribe(handleData);
    
    // Also do a manual fetch from backend API
    fetch('/api/v1/connection/status')
      .then(res => res.json())
      .then(data => {
        setConnectedState(data.connected);
        if(data.connected) setStatusMsg(`Connected via ${data.type}`);
      })
      .catch(err => console.error("Error fetching status", err));
      
    return () => unsubscribe();
  }, []);

  const handleScanTcp = async () => {
    setIsScanning(true);
    setStatusMsg(`Scanning subnet ${subnet}.x...`);
    setTcpDevices([]);
    try {
      const response = await fetch(`/api/v1/connection/scan-network?subnet=${encodeURIComponent(subnet)}`, {
        method: 'POST'
      });
      if (response.ok) {
        const data = await response.json();
        const formattedDevices = (data.devices || []).map((ip: string) => ({
          ip,
          mac: 'Unknown',
          model: 'DXM',
          serial: 'Unknown',
          fw: 'Unknown'
        }));
        setTcpDevices(formattedDevices);
        setStatusMsg(`Found ${formattedDevices.length} devices on network.`);
      } else {
        setStatusMsg('Network scan failed (Server Error).');
      }
    } catch (err) {
      console.error(err);
      setStatusMsg('Network scan failed.');
    }
    setIsScanning(false);
  };
  
  const handleScanSerial = async () => {
    setIsScanning(true);
    setStatusMsg(`Scanning COM Ports...`);
    setSerialDevices([]);
    try {
      const response = await fetch('/api/v1/connection/scan', { method: 'POST' });
      if (response.ok) {
        const data = await response.json();
        setSerialDevices(data.ports || []);
        setStatusMsg(`Found ${(data.ports || []).length} serial ports.`);
        if (data.ports && data.ports.length > 0) {
          setComPort(data.ports[0].device);
        }
      } else {
        setStatusMsg('Serial scan failed (Server error).');
      }
    } catch (err) {
      console.error(err);
      setStatusMsg('Serial scan failed.');
    }
    setIsScanning(false);
  };

  const handleConnectTcp = async () => {
    setIsConnecting(true);
    setStatusMsg(`Connecting to TCP/IP ${ipAddress}:502...`);
    try {
      const response = await fetch('/api/v1/connection/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          protocol: 'TCP',
          host: ipAddress,
          port: 502,
          slave_id: 1,
          timeout: 5.0
        })
      });
      const data = await response.json();
      if (response.ok && data.success) {
        setConnectedState(true);
        setStatusMsg(`Connected to ${ipAddress} — live polling active`);
      } else {
        setStatusMsg(data.message || 'TCP Connection Failed — check IP address and device power');
      }
    } catch (error) {
      setStatusMsg('TCP Connection Error — backend unreachable');
    }
    setIsConnecting(false);
  };

  const handleConnectSerial = async () => {
    setIsConnecting(true);
    setStatusMsg(`Connecting to Serial ${comPort} @ ${baudRate} baud...`);
    try {
      const response = await fetch('/api/v1/connection/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          protocol: 'RTU',
          port: comPort,
          baudrate: parseInt(baudRate),
          baud: parseInt(baudRate),
          slave_id: 1,
          timeout: 5.0
        })
      });
      const data = await response.json();
      if (response.ok && data.success) {
        setConnectedState(true);
        setStatusMsg(`Connected to ${comPort} — live polling active`);
      } else {
        setStatusMsg(data.message || 'Serial Connection Failed — check port and baud rate');
      }
    } catch (error) {
      setStatusMsg('Serial Connection Error — backend unreachable');
    }
    setIsConnecting(false);
  };

  const handleDisconnect = async () => {
    try {
      await fetch('/api/v1/connection/disconnect', { method: 'POST' });
      setConnectedState(false);
      setStatusMsg('Not Connected');
    } catch(err) {
      console.error(err);
    }
  };

  return (
    <div className="p-6 h-full flex flex-col gap-6" style={{ backgroundColor: COLORS.bg, color: COLORS.text }}>
      <h1 className="text-2xl font-bold mb-4 flex items-center gap-2">
        <Server className="w-6 h-6" style={{ color: COLORS.primary }} />
        Connection Management
      </h1>

      <div className="p-6 rounded-lg border flex flex-col gap-6 w-full max-w-4xl shadow-lg" style={{ backgroundColor: COLORS.bgPanel, borderColor: COLORS.border, color: COLORS.text }}>
        
        {/* Radio Selection */}
        <div className="flex items-center gap-6 text-lg font-semibold border-b pb-4" style={{ borderColor: COLORS.border }}>
          <span style={{ color: COLORS.textMuted }}>Connect to DXM using:</span>
          <label className="flex items-center gap-2 cursor-pointer font-normal hover:text-white transition-colors">
            <input 
              type="radio" 
              name="connType" 
              value="serial" 
              checked={connectionType === 'serial'} 
              onChange={() => setConnectionType('serial')}
              className="w-4 h-4 cursor-pointer accent-blue-500"
            />
            Serial
          </label>
          <label className="flex items-center gap-2 cursor-pointer font-normal hover:text-white transition-colors">
            <input 
              type="radio" 
              name="connType" 
              value="tcp" 
              checked={connectionType === 'tcp'} 
              onChange={() => setConnectionType('tcp')}
              className="w-4 h-4 cursor-pointer accent-blue-500"
            />
            TCP/IP
          </label>
        </div>

        {connectionType === 'tcp' ? (
          <>
            {/* TCP SCANNING CONTROLS */}
            <div className="flex items-center gap-4 mt-2">
              <span className="w-32 text-right" style={{ color: COLORS.textMuted }}>Subnet to Scan:</span>
              <div className="flex items-center">
                <input 
                  type="text" 
                  value={subnet} 
                  onChange={(e) => setSubnet(e.target.value)}
                  className="border rounded px-3 py-1.5 flex-1 outline-none w-48 text-white focus:border-blue-500 transition-colors"
                  style={{ backgroundColor: COLORS.bg, borderColor: COLORS.border }}
                />
              </div>
              <button 
                onClick={handleScanTcp}
                disabled={isScanning}
                className="border rounded p-1.5 transition-colors disabled:opacity-50 shadow-sm hover:bg-slate-700"
                style={{ backgroundColor: COLORS.bg, borderColor: COLORS.border }}
                title="Refresh"
              >
                <RefreshCw className={`w-5 h-5 ${isScanning ? 'animate-spin' : ''}`} style={{ color: COLORS.primary }} />
              </button>
              <button 
                onClick={handleScanTcp}
                disabled={isScanning}
                className="border rounded px-4 py-1.5 focus:outline-none transition-colors disabled:opacity-50 shadow-sm hover:bg-slate-700"
                style={{ backgroundColor: COLORS.bg, borderColor: COLORS.border, color: COLORS.text }}
              >
                Scan Network for DXMs
              </button>
            </div>

            {/* TCP DEVICES TABLE */}
            <div className="border rounded-md min-h-[160px] overflow-hidden shadow-inner mt-4" style={{ borderColor: COLORS.border, backgroundColor: COLORS.bg }}>
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b" style={{ backgroundColor: COLORS.bgPanel, borderColor: COLORS.border }}>
                    <th className="p-3 border-r font-medium" style={{ borderColor: COLORS.border, color: COLORS.textMuted }}>IP</th>
                    <th className="p-3 border-r font-medium" style={{ borderColor: COLORS.border, color: COLORS.textMuted }}>MAC</th>
                    <th className="p-3 border-r font-medium" style={{ borderColor: COLORS.border, color: COLORS.textMuted }}>Model</th>
                    <th className="p-3 border-r font-medium" style={{ borderColor: COLORS.border, color: COLORS.textMuted }}>Serial Number</th>
                    <th className="p-3 font-medium" style={{ color: COLORS.textMuted }}>FW Version</th>
                  </tr>
                </thead>
                <tbody>
                  {tcpDevices.map((dev, i) => (
                    <tr key={i} className="hover:bg-slate-800 cursor-pointer border-b transition-colors" style={{ borderColor: COLORS.border }} onClick={() => setIpAddress(dev.ip)}>
                      <td className="p-3 border-r" style={{ borderColor: COLORS.border }}>{dev.ip}</td>
                      <td className="p-3 border-r" style={{ borderColor: COLORS.border }}>{dev.mac}</td>
                      <td className="p-3 border-r" style={{ borderColor: COLORS.border }}>{dev.model}</td>
                      <td className="p-3 border-r" style={{ borderColor: COLORS.border }}>{dev.serial}</td>
                      <td className="p-3">{dev.fw}</td>
                    </tr>
                  ))}
                  {tcpDevices.length === 0 && !isScanning && (
                    <tr>
                      <td colSpan={5} className="p-6 text-center italic" style={{ color: COLORS.textMuted }}>
                        No devices found or scanning not started.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* TCP CONNECTION ACTIONS */}
            <div className="flex items-center justify-center gap-4 mt-8">
              <span className="w-24 text-right" style={{ color: COLORS.textMuted }}>IP Address</span>
              <input 
                type="text" 
                value={ipAddress} 
                onChange={(e) => setIpAddress(e.target.value)}
                className="border rounded px-3 py-1.5 w-48 outline-none shadow-inner text-white focus:border-blue-500 transition-colors"
                style={{ backgroundColor: COLORS.bg, borderColor: COLORS.border }}
              />
              <label className="flex items-center gap-2 cursor-pointer ml-4">
                <input 
                  type="checkbox" 
                  checked={useVpn} 
                  onChange={(e) => setUseVpn(e.target.checked)}
                  className="w-4 h-4 cursor-pointer accent-blue-500"
                />
                VPN
              </label>
              
              {!connectedState ? (
                <button 
                  onClick={handleConnectTcp}
                  disabled={isConnecting}
                  className="ml-4 border rounded px-8 py-1.5 shadow-sm focus:outline-none transition-colors disabled:opacity-50 hover:bg-blue-600 font-medium"
                  style={{ backgroundColor: COLORS.primary, borderColor: COLORS.primary, color: 'white' }}
                >
                  {isConnecting ? 'Connecting...' : 'Connect'}
                </button>
              ) : (
                <button 
                  onClick={handleDisconnect}
                  className="ml-4 border rounded px-6 py-1.5 shadow-sm focus:outline-none transition-colors hover:bg-red-600 font-medium"
                  style={{ backgroundColor: COLORS.critical, borderColor: COLORS.critical, color: 'white' }}
                >
                  Disconnect
                </button>
              )}
            </div>
          </>
        ) : (
          <>
            {/* SERIAL SCANNING CONTROLS */}
            <div className="flex items-center gap-4 mt-2">
              <button 
                onClick={handleScanSerial}
                disabled={isScanning}
                className="border rounded px-4 py-1.5 focus:outline-none transition-colors disabled:opacity-50 shadow-sm hover:bg-slate-700 flex items-center gap-2"
                style={{ backgroundColor: COLORS.bg, borderColor: COLORS.border, color: COLORS.text }}
              >
                <RefreshCw className={`w-4 h-4 ${isScanning ? 'animate-spin' : ''}`} style={{ color: COLORS.primary }} />
                Scan Ports for DXMs
              </button>
            </div>

            {/* SERIAL DEVICES TABLE */}
            <div className="border rounded-md min-h-[160px] overflow-hidden shadow-inner mt-4" style={{ borderColor: COLORS.border, backgroundColor: COLORS.bg }}>
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b" style={{ backgroundColor: COLORS.bgPanel, borderColor: COLORS.border }}>
                    <th className="p-3 border-r font-medium" style={{ borderColor: COLORS.border, color: COLORS.textMuted }}>Port</th>
                    <th className="p-3 border-r font-medium" style={{ borderColor: COLORS.border, color: COLORS.textMuted }}>Description</th>
                    <th className="p-3 font-medium" style={{ color: COLORS.textMuted }}>HWID</th>
                  </tr>
                </thead>
                <tbody>
                  {serialDevices.map((dev, i) => (
                    <tr key={i} className="hover:bg-slate-800 cursor-pointer border-b transition-colors" style={{ borderColor: COLORS.border }} onClick={() => setComPort(dev.device)}>
                      <td className="p-3 border-r" style={{ borderColor: COLORS.border }}>{dev.device}</td>
                      <td className="p-3 border-r" style={{ borderColor: COLORS.border }}>{dev.description}</td>
                      <td className="p-3">{dev.hwid}</td>
                    </tr>
                  ))}
                  {serialDevices.length === 0 && !isScanning && (
                    <tr>
                      <td colSpan={3} className="p-6 text-center italic" style={{ color: COLORS.textMuted }}>
                        No COM ports found or scanning not started.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* SERIAL CONNECTION ACTIONS */}
            <div className="flex items-center justify-center gap-4 mt-8">
              <span className="text-right" style={{ color: COLORS.textMuted }}>COM Port</span>
              <input 
                type="text" 
                value={comPort} 
                onChange={(e) => setComPort(e.target.value)}
                className="border rounded px-3 py-1.5 w-32 outline-none shadow-inner text-white focus:border-blue-500 transition-colors"
                style={{ backgroundColor: COLORS.bg, borderColor: COLORS.border }}
              />
              
              <span className="text-right ml-4" style={{ color: COLORS.textMuted }}>Baud</span>
              <select 
                value={baudRate} 
                onChange={(e) => setBaudRate(e.target.value)}
                className="border rounded px-3 py-1.5 w-32 outline-none shadow-inner text-white focus:border-blue-500 transition-colors"
                style={{ backgroundColor: COLORS.bg, borderColor: COLORS.border }}
              >
                <option value="9600">9600</option>
                <option value="19200">19200</option>
                <option value="38400">38400</option>
                <option value="115200">115200</option>
              </select>
              
              {!connectedState ? (
                <button 
                  onClick={handleConnectSerial}
                  disabled={isConnecting}
                  className="ml-4 border rounded px-8 py-1.5 shadow-sm focus:outline-none transition-colors disabled:opacity-50 hover:bg-blue-600 font-medium"
                  style={{ backgroundColor: COLORS.primary, borderColor: COLORS.primary, color: 'white' }}
                >
                  {isConnecting ? 'Connecting...' : 'Connect'}
                </button>
              ) : (
                <button 
                  onClick={handleDisconnect}
                  className="ml-4 border rounded px-6 py-1.5 shadow-sm focus:outline-none transition-colors hover:bg-red-600 font-medium"
                  style={{ backgroundColor: COLORS.critical, borderColor: COLORS.critical, color: 'white' }}
                >
                  Disconnect
                </button>
              )}
            </div>
          </>
        )}

        {/* BOTTOM STATUS */}
        <div className="mt-8 text-center pt-6 border-t" style={{ borderColor: COLORS.border }}>
          <p className="font-medium text-lg" style={{ color: connectedState ? COLORS.success : COLORS.textMuted }}>
            Status: {statusMsg}
          </p>
        </div>

      </div>
    </div>
  );
}
