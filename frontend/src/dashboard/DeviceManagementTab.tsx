import React, { useState, useEffect } from 'react';
import { 
  Wifi, WifiOff, Search, Play, Pause, Plus, Trash2, 
  Settings, Activity, CheckCircle, XCircle, AlertTriangle,
  Network, HardDrive, Cpu, Clock, Zap
} from 'lucide-react';

interface NetworkDevice {
  ip: string;
  mac: string;
  hostname?: string;
  vendor?: string;
  open_ports: number[];
  device_type: string;
  confidence: number;
  response_time_ms: number;
  last_seen: string;
}

interface ModbusDevice {
  ip: string;
  port: number;
  slave_id: number;
  device_id?: string;
  firmware_version?: string;
  serial_number?: string;
  model?: string;
  vendor?: string;
  is_dxm: boolean;
  confidence: number;
  response_time_ms: number;
  registers: Record<number, any>;
}

interface ConnectedDevice {
  device_id: string;
  status: any;
  registers: Record<number, any>;
  last_updated: string;
}

interface NetworkInterface {
  name: string;
  addresses: Array<{
    family: string;
    address: string;
    netmask?: string;
    broadcast?: string;
  }>;
  stats?: {
    isup: boolean;
    duplex: number;
    speed: number;
    mtu: number;
  };
}

const DeviceManagementTab: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'scan' | 'connected' | 'interfaces'>('scan');
  const [scanning, setScanning] = useState(false);
  const [scanResults, setScanResults] = useState<{
    network_devices: NetworkDevice[];
    modbus_devices: ModbusDevice[];
  }>({ network_devices: [], modbus_devices: [] });
  const [connectedDevices, setConnectedDevices] = useState<ConnectedDevice[]>([]);
  const [networkInterfaces, setNetworkInterfaces] = useState<NetworkInterface[]>([]);
  const [networkRanges, setNetworkRanges] = useState<string[]>([]);
  const [selectedRange, setSelectedRange] = useState('192.168.1.0/24');
  const [scanType, setScanType] = useState<'quick' | 'full' | 'modbus_only'>('quick');
  const [activeScanId, setActiveScanId] = useState<string | null>(null);
  const [scanProgress, setScanProgress] = useState(0);

  useEffect(() => {
    fetchNetworkInterfaces();
    fetchNetworkRanges();
    fetchConnectedDevices();
    
    // Auto-refresh connected devices
    const interval = setInterval(fetchConnectedDevices, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchNetworkInterfaces = async () => {
    try {
      const response = await fetch('/api/v1/devices/interfaces');
      const data = await response.json();
      setNetworkInterfaces(data.interfaces || []);
    } catch (error) {
      console.error('Error fetching network interfaces:', error);
    }
  };

  const fetchNetworkRanges = async () => {
    try {
      const response = await fetch('/api/v1/devices/network/ranges');
      const data = await response.json();
      setNetworkRanges(data.network_ranges || []);
      if (data.network_ranges?.length > 0) {
        setSelectedRange(data.network_ranges[0]);
      }
    } catch (error) {
      console.error('Error fetching network ranges:', error);
    }
  };

  const fetchConnectedDevices = async () => {
    try {
      const response = await fetch('/api/v1/devices/connected');
      const data = await response.json();
      setConnectedDevices(data.connected_devices || []);
    } catch (error) {
      console.error('Error fetching connected devices:', error);
    }
  };

  const startScan = async () => {
    setScanning(true);
    setScanProgress(0);
    
    try {
      const response = await fetch('/api/v1/devices/scan/network', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          network_range: selectedRange,
          scan_type: scanType,
          timeout: 2.0
        })
      });
      
      const data = await response.json();
      setActiveScanId(data.scan_id);
      
      // Poll for scan results
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await fetch(`/api/v1/devices/scan/${data.scan_id}`);
          const statusData = await statusResponse.json();
          
          setScanProgress(statusData.status === 'completed' ? 100 : 50);
          
          if (statusData.status === 'completed' || statusData.status === 'failed') {
            clearInterval(pollInterval);
            setScanning(false);
            setActiveScanId(null);
            
            if (statusData.status === 'completed') {
              setScanResults({
                network_devices: statusData.network_devices || [],
                modbus_devices: statusData.modbus_devices || []
              });
            }
          }
        } catch (error) {
          console.error('Error polling scan status:', error);
          clearInterval(pollInterval);
          setScanning(false);
        }
      }, 2000);
      
    } catch (error) {
      console.error('Error starting scan:', error);
      setScanning(false);
    }
  };

  const connectToDevice = async (device: ModbusDevice) => {
    try {
      const response = await fetch('/api/v1/devices/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ip: device.ip,
          port: device.port,
          slave_id: device.slave_id,
          connection_type: 'tcp'
        })
      });
      
      const result = await response.json();
      
      if (result.status === 'connected') {
        await fetchConnectedDevices();
        alert(`Successfully connected to ${result.device_id}`);
      } else {
        alert(`Failed to connect: ${result.error_message}`);
      }
    } catch (error) {
      console.error('Error connecting to device:', error);
      alert('Error connecting to device');
    }
  };

  const disconnectDevice = async (deviceId: string) => {
    try {
      const response = await fetch(`/api/v1/devices/disconnect/${deviceId}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        await fetchConnectedDevices();
        alert(`Device ${deviceId} disconnected`);
      } else {
        alert('Failed to disconnect device');
      }
    } catch (error) {
      console.error('Error disconnecting device:', error);
      alert('Error disconnecting device');
    }
  };

  const testDevice = async (deviceId: string, testType: string = 'connectivity') => {
    try {
      const response = await fetch(`/api/v1/devices/test/${deviceId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ test_type: testType })
      });
      
      const result = await response.json();
      
      if (result.status === 'completed') {
        alert(`Test completed: ${JSON.stringify(result.results, null, 2)}`);
      } else {
        alert(`Test failed: ${result.error_message}`);
      }
    } catch (error) {
      console.error('Error testing device:', error);
      alert('Error testing device');
    }
  };

  const getDeviceIcon = (deviceType: string) => {
    switch (deviceType) {
      case 'DXM Controller':
      case 'Modbus Device':
        return <Settings className="w-5 h-5" />;
      case 'Network Infrastructure':
        return <Network className="w-5 h-5" />;
      case 'Server':
        return <HardDrive className="w-5 h-5" />;
      default:
        return <Cpu className="w-5 h-5" />;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'disconnected':
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />;
      case 'connecting':
        return <Activity className="w-5 h-5 text-yellow-500" />;
      default:
        return <AlertTriangle className="w-5 h-5 text-gray-500" />;
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-500';
    if (confidence >= 0.6) return 'text-yellow-500';
    return 'text-red-500';
  };

  return (
    <div className="space-y-6">
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <h2 className="text-xl font-semibold text-white mb-4">Device Management</h2>
        
        {/* Tab Navigation */}
        <div className="flex space-x-1 mb-6 bg-gray-900 rounded-lg p-1">
          <button
            onClick={() => setActiveTab('scan')}
            className={`flex items-center space-x-2 px-4 py-2 rounded-md transition-colors ${
              activeTab === 'scan' 
                ? 'bg-blue-600 text-white' 
                : 'text-gray-400 hover:text-white'
            }`}
          >
            <Search className="w-4 h-4" />
            <span>Network Scan</span>
          </button>
          <button
            onClick={() => setActiveTab('connected')}
            className={`flex items-center space-x-2 px-4 py-2 rounded-md transition-colors ${
              activeTab === 'connected' 
                ? 'bg-blue-600 text-white' 
                : 'text-gray-400 hover:text-white'
            }`}
          >
            <Wifi className="w-4 h-4" />
            <span>Connected Devices</span>
          </button>
          <button
            onClick={() => setActiveTab('interfaces')}
            className={`flex items-center space-x-2 px-4 py-2 rounded-md transition-colors ${
              activeTab === 'interfaces' 
                ? 'bg-blue-600 text-white' 
                : 'text-gray-400 hover:text-white'
            }`}
          >
            <Network className="w-4 h-4" />
            <span>Network Interfaces</span>
          </button>
        </div>

        {/* Network Scan Tab */}
        {activeTab === 'scan' && (
          <div className="space-y-6">
            {/* Scan Configuration */}
            <div className="bg-gray-900 rounded-lg p-4">
              <h3 className="text-lg font-medium text-white mb-4">Scan Configuration</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-gray-400 text-sm mb-1">Network Range</label>
                  <select
                    value={selectedRange}
                    onChange={(e) => setSelectedRange(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                  >
                    {networkRanges.map(range => (
                      <option key={range} value={range}>{range}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-gray-400 text-sm mb-1">Scan Type</label>
                  <select
                    value={scanType}
                    onChange={(e) => setScanType(e.target.value as any)}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                  >
                    <option value="quick">Quick Scan</option>
                    <option value="full">Full Scan</option>
                    <option value="modbus_only">Modbus Only</option>
                  </select>
                </div>
                <div className="flex items-end">
                  <button
                    onClick={startScan}
                    disabled={scanning}
                    className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                  >
                    {scanning ? (
                      <>
                        <Activity className="w-4 h-4 animate-spin" />
                        <span>Scanning...</span>
                      </>
                    ) : (
                      <>
                        <Search className="w-4 h-4" />
                        <span>Start Scan</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
              
              {scanning && (
                <div className="mt-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-gray-400">Scan Progress</span>
                    <span className="text-sm text-gray-400">{scanProgress}%</span>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-2">
                    <div 
                      className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${scanProgress}%` }}
                    ></div>
                  </div>
                </div>
              )}
            </div>

            {/* Scan Results */}
            {(scanResults.network_devices.length > 0 || scanResults.modbus_devices.length > 0) && (
              <div className="space-y-6">
                {/* Modbus Devices */}
                {scanResults.modbus_devices.length > 0 && (
                  <div className="bg-gray-900 rounded-lg p-4">
                    <h3 className="text-lg font-medium text-white mb-4">
                      Modbus Devices ({scanResults.modbus_devices.length})
                    </h3>
                    <div className="space-y-3">
                      {scanResults.modbus_devices.map((device, index) => (
                        <div key={index} className="bg-gray-800 rounded-lg p-4 border border-gray-700">
                          <div className="flex items-start justify-between">
                            <div className="flex items-center space-x-3">
                              <div className="mt-1 text-blue-500">
                                {getDeviceIcon(device.is_dxm ? 'DXM Controller' : 'Modbus Device')}
                              </div>
                              <div className="flex-1">
                                <div className="flex items-center space-x-2 mb-1">
                                  <h4 className="text-white font-medium">
                                    {device.device_id || `Device ${device.slave_id}`}
                                  </h4>
                                  {device.is_dxm && (
                                    <span className="px-2 py-1 bg-green-900 text-green-300 text-xs rounded">
                                      DXM
                                    </span>
                                  )}
                                  <span className={`text-sm ${getConfidenceColor(device.confidence)}`}>
                                    {(device.confidence * 100).toFixed(0)}% confidence
                                  </span>
                                </div>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm text-gray-400">
                                  <div>IP: {device.ip}:{device.port}</div>
                                  <div>Slave ID: {device.slave_id}</div>
                                  <div>Response: {device.response_time_ms.toFixed(1)}ms</div>
                                  {device.firmware_version && (
                                    <div>Firmware: {device.firmware_version}</div>
                                  )}
                                </div>
                                {device.registers && Object.keys(device.registers).length > 0 && (
                                  <div className="mt-2">
                                    <span className="text-xs text-gray-400">Registers: </span>
                                    <span className="text-xs text-white">
                                      {Object.keys(device.registers).slice(0, 5).join(', ')}
                                      {Object.keys(device.registers).length > 5 && '...'}
                                    </span>
                                  </div>
                                )}
                              </div>
                            </div>
                            <div className="flex space-x-2">
                              <button
                                onClick={() => connectToDevice(device)}
                                className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 transition-colors text-sm"
                              >
                                Connect
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Other Network Devices */}
                {scanResults.network_devices.length > 0 && (
                  <div className="bg-gray-900 rounded-lg p-4">
                    <h3 className="text-lg font-medium text-white mb-4">
                      Other Network Devices ({scanResults.network_devices.length})
                    </h3>
                    <div className="space-y-2">
                      {scanResults.network_devices.map((device, index) => (
                        <div key={index} className="bg-gray-800 rounded-lg p-3 border border-gray-700">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-3">
                              <div className="text-gray-500">
                                {getDeviceIcon(device.device_type)}
                              </div>
                              <div>
                                <div className="text-white font-medium">{device.hostname || device.ip}</div>
                                <div className="text-sm text-gray-400">
                                  {device.ip} • {device.device_type} • {device.open_ports.length} ports
                                </div>
                              </div>
                            </div>
                            <div className={`text-sm ${getConfidenceColor(device.confidence)}`}>
                              {(device.confidence * 100).toFixed(0)}%
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Connected Devices Tab */}
        {activeTab === 'connected' && (
          <div className="space-y-4">
            {connectedDevices.length > 0 ? (
              connectedDevices.map((device, index) => (
                <div key={index} className="bg-gray-900 rounded-lg p-4 border border-gray-700">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start space-x-3">
                      <div className="mt-1">
                        {getStatusIcon(device.status?.state || 'unknown')}
                      </div>
                      <div className="flex-1">
                        <h4 className="text-white font-medium mb-1">{device.device_id}</h4>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-sm text-gray-400">
                          <div>Status: {device.status?.state || 'Unknown'}</div>
                          <div>Last Updated: {new Date(device.last_updated).toLocaleString()}</div>
                          <div>Registers: {Object.keys(device.registers).length}</div>
                        </div>
                        {device.registers && Object.keys(device.registers).length > 0 && (
                          <div className="mt-3 p-3 bg-gray-800 rounded">
                            <div className="text-xs text-gray-400 mb-2">Recent Register Values:</div>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                              {Object.entries(device.registers).slice(0, 8).map(([addr, value]) => (
                                <div key={addr} className="text-xs">
                                  <span className="text-gray-400">{addr}:</span>
                                  <span className="text-white ml-1">{value}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => testDevice(device.device_id, 'connectivity')}
                        className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors text-sm"
                      >
                        Test
                      </button>
                      <button
                        onClick={() => testDevice(device.device_id, 'registers')}
                        className="px-3 py-1 bg-yellow-600 text-white rounded hover:bg-yellow-700 transition-colors text-sm"
                      >
                        Registers
                      </button>
                      <button
                        onClick={() => disconnectDevice(device.device_id)}
                        className="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700 transition-colors text-sm"
                      >
                        Disconnect
                      </button>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="bg-gray-900 rounded-lg p-12 border border-gray-700 text-center">
                <WifiOff className="w-16 h-16 text-gray-500 mx-auto mb-4" />
                <p className="text-gray-400 text-lg">No connected devices</p>
                <p className="text-gray-500 text-sm mt-2">Scan for devices and connect to start monitoring</p>
              </div>
            )}
          </div>
        )}

        {/* Network Interfaces Tab */}
        {activeTab === 'interfaces' && (
          <div className="space-y-4">
            {networkInterfaces.map((iface, index) => (
              <div key={index} className="bg-gray-900 rounded-lg p-4 border border-gray-700">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-white font-medium">{iface.name}</h4>
                  {iface.stats?.isup ? (
                    <span className="px-2 py-1 bg-green-900 text-green-300 text-xs rounded">Active</span>
                  ) : (
                    <span className="px-2 py-1 bg-red-900 text-red-300 text-xs rounded">Inactive</span>
                  )}
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <h5 className="text-sm text-gray-400 mb-2">Addresses</h5>
                    <div className="space-y-1">
                      {iface.addresses.map((addr, addrIndex) => (
                        <div key={addrIndex} className="text-sm">
                          <span className="text-gray-400">{addr.family}:</span>
                          <span className="text-white ml-2">{addr.address}</span>
                          {addr.netmask && <span className="text-gray-500 ml-2">/{addr.netmask}</span>}
                        </div>
                      ))}
                    </div>
                  </div>
                  
                  {iface.stats && (
                    <div>
                      <h5 className="text-sm text-gray-400 mb-2">Statistics</h5>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div>
                          <span className="text-gray-400">Speed:</span>
                          <span className="text-white ml-2">{iface.stats.speed} Mbps</span>
                        </div>
                        <div>
                          <span className="text-gray-400">Duplex:</span>
                          <span className="text-white ml-2">{iface.stats.duplex}</span>
                        </div>
                        <div>
                          <span className="text-gray-400">MTU:</span>
                          <span className="text-white ml-2">{iface.stats.mtu}</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default DeviceManagementTab;
