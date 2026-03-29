
import subprocess
import sys
import time
import requests
import socket
import os
import signal

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def test_backend():
    print("🧪 STARTING SYSTEM TEST")
    print("-" * 30)
    
    # 1. Check if backend is already running
    if is_port_in_use(8000):
        print("⚠️  Port 8000 is BUSY. Backend might already be running.")
        try:
            r = requests.get("http://localhost:8000/api/v1/connection/status", timeout=2)
            if r.status_code == 200:
                print("✅ Existing Backend is responding! Status:", r.json())
                return True
            else:
                print("❌ Existing Backend responded with error:", r.status_code)
                return False
        except Exception as e:
            print(f"❌ Existing Backend on port 8000 is NOT responding: {e}")
            return False

    # 2. Try to start backend
    print("🚀 Attempting to start Backend from test script...")
    backend_dir = os.path.join(os.getcwd(), "backend")
    
    # Command to run uvicorn
    cmd = [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8000"]
    
    try:
        proc = subprocess.Popen(
            cmd, 
            cwd=backend_dir, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        
        print("⏳ Waiting for backend to initialize (5s)...")
        time.sleep(5)
        
        # Check if process is still alive
        if proc.poll() is not None:
             stdout, stderr = proc.communicate()
             print("❌ Backend CRASHED immediately!")
             print("STDOUT:", stdout)
             print("STDERR:", stderr)
             return False
             
        # 3. Test API
        try:
            print("📡 Testing API connection...")
            r = requests.get("http://127.0.0.1:8000/api/v1/connection/status", timeout=5)
            if r.status_code == 200:
                print("✅ API CONNECTED SUCCESSFULLY!")
                print("Data:", r.json())
                print("✅ Backend is working correctly.")
            else:
                print(f"❌ API Error: {r.status_code}")
                
        except requests.exceptions.ConnectionError:
            print("❌ Could not connect to API (Connection Refused)")
            stdout, stderr = proc.communicate()
            print("Backend Logs:\n", stderr)
            
        finally:
            print("🛑 Stopping Test Backend...")
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                
    except Exception as e:
        print(f"❌ Test Failed with Exception: {e}")

if __name__ == "__main__":
    test_backend()
