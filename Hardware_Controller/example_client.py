#!/usr/bin/env python3
"""
Example client for Hardware Controller Backend.
Demonstrates how to use the API from Python.
"""

import requests
import time
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000"
TIMEOUT = 5


class HardwareClient:
    """Client for communicating with Hardware Controller Backend."""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
    
    def health_check(self) -> bool:
        """Check if backend is running."""
        try:
            response = requests.get(f"{self.base_url}/", timeout=TIMEOUT)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Backend not responding: {e}")
            return False
    
    def list_ports(self) -> list:
        """Get list of available COM ports."""
        try:
            response = requests.get(f"{self.base_url}/ports", timeout=TIMEOUT)
            data = response.json()
            return data.get("available_ports", [])
        except Exception as e:
            print(f"❌ Error listing ports: {e}")
            return []
    
    def connect(self, port: str, baud: int = 9600) -> bool:
        """Connect to a COM port."""
        try:
            response = requests.post(
                f"{self.base_url}/connect",
                params={"port": port, "baud": baud},
                timeout=TIMEOUT
            )
            if response.status_code == 200:
                print(f"✅ Connected to {port}")
                return True
            else:
                print(f"❌ Failed to connect: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
    
    def disconnect(self) -> bool:
        """Disconnect from device."""
        try:
            response = requests.post(
                f"{self.base_url}/disconnect",
                timeout=TIMEOUT
            )
            print("✅ Disconnected")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Disconnection error: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current device status."""
        try:
            response = requests.get(
                f"{self.base_url}/status",
                timeout=TIMEOUT
            )
            return response.json()
        except Exception as e:
            print(f"❌ Error getting status: {e}")
            return {}
    
    def send_command(self, value: float, threshold: float) -> bool:
        """
        Send control command.
        Sends "1\n" if value > threshold, else "0\n"
        """
        try:
            response = requests.post(
                f"{self.base_url}/send",
                json={"value": value, "threshold": threshold},
                timeout=TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                result = "ON" if data["command_sent"] == "ON" else "OFF"
                print(f"✅ Command sent: {result} (value={value}, threshold={threshold})")
                return True
            else:
                print(f"❌ Failed to send command: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error sending command: {e}")
            return False
    
    def send_raw(self, command: str) -> bool:
        """Send raw command string (e.g., "1\n" or "0\n")."""
        try:
            response = requests.post(
                f"{self.base_url}/send-raw",
                params={"command": command},
                timeout=TIMEOUT
            )
            
            if response.status_code == 200:
                print(f"✅ Raw command sent: {repr(command)}")
                return True
            else:
                print(f"❌ Failed to send raw command: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error sending raw command: {e}")
            return False


def example_basic_usage():
    """Basic usage example."""
    print("\n" + "="*60)
    print("EXAMPLE: Basic Usage")
    print("="*60)
    
    client = HardwareClient()
    
    # Check if backend is running
    if not client.health_check():
        print("❌ Backend not running. Start it with: python main.py")
        return
    
    print("✅ Backend is running")
    
    # List available ports
    ports = client.list_ports()
    print(f"Available COM ports: {ports}")
    
    # Get current status
    status = client.get_status()
    print(f"Device connected: {status.get('connected')}")
    print(f"Last command: {status.get('last_command')}")
    
    # Send some commands
    print("\nSending test commands...")
    client.send_command(value=100, threshold=50)  # Should turn ON (100 > 50)
    time.sleep(1)
    
    client.send_command(value=25, threshold=50)   # Should turn OFF (25 < 50)
    time.sleep(1)
    
    client.send_command(value=75, threshold=50)   # Should turn ON (75 > 50)


def example_threshold_logic():
    """Example showing threshold logic."""
    print("\n" + "="*60)
    print("EXAMPLE: Threshold Logic")
    print("="*60)
    
    client = HardwareClient()
    
    if not client.health_check():
        print("❌ Backend not running")
        return
    
    # Simulate sensor reading with changing thresholds
    sensor_value = 60
    threshold = 50
    
    print(f"Sensor value: {sensor_value}")
    print(f"Threshold: {threshold}")
    print(f"Comparison: {sensor_value} > {threshold} = {sensor_value > threshold}")
    
    client.send_command(sensor_value, threshold)


def example_loop_with_updates():
    """Example of continuous monitoring."""
    print("\n" + "="*60)
    print("EXAMPLE: Continuous Monitoring (5 iterations)")
    print("="*60)
    
    client = HardwareClient()
    
    if not client.health_check():
        print("❌ Backend not running")
        return
    
    # Simulate changing sensor values
    values = [30, 55, 45, 75, 40]
    threshold = 50
    
    for i, value in enumerate(values, 1):
        print(f"\n[{i}/5] Reading sensor value: {value}")
        client.send_command(value, threshold)
        print("Waiting 2 seconds before next...")
        time.sleep(2)
    
    # Show final status
    status = client.get_status()
    print(f"\nFinal status:")
    print(f"  Last value: {status.get('last_value')}")
    print(f"  Last command: {status.get('last_command')}")


def example_manual_commands():
    """Example of sending raw commands."""
    print("\n" + "="*60)
    print("EXAMPLE: Raw Command Control")
    print("="*60)
    
    client = HardwareClient()
    
    if not client.health_check():
        print("❌ Backend not running")
        return
    
    print("Sending raw '1\\n' (ON)...")
    client.send_raw("1\n")
    time.sleep(1)
    
    print("Sending raw '0\\n' (OFF)...")
    client.send_raw("0\n")
    time.sleep(1)
    
    print("Sending raw '1\\n' (ON)...")
    client.send_raw("1\n")


if __name__ == "__main__":
    print("Hardware Controller Backend - Client Examples")
    print("Make sure backend is running: python main.py")
    
    try:
        # Run examples
        example_basic_usage()
        example_threshold_logic()
        example_loop_with_updates()
        example_manual_commands()
        
        print("\n" + "="*60)
        print("✅ Examples completed successfully!")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
