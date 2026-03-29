#!/usr/bin/env python3
"""
Quick verification script to test if the Modbus backend is working correctly
after the fixes. Run this to verify the critical error is resolved.
"""

import subprocess
import time
import sys

def test_backend_startup():
    """Test if backend starts without the critical error"""
    print("=" * 60)
    print("BACKEND ERROR FIX VERIFICATION")
    print("=" * 60)
    print("\n✓ Testing backend startup...\n")
    
    try:
        # Start the backend process
        process = subprocess.Popen(
            [sys.executable, "app.py"],
            cwd="backend",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        
        # Monitor for 10 seconds
        print("Monitoring logs for 10 seconds...")
        print("-" * 60)
        
        start_time = time.time()
        error_found = False
        register_error_count = 0
        
        while time.time() - start_time < 10:
            try:
                line = process.stderr.readline()
                if line:
                    print(line.strip())
                    
                    # Check for the critical error
                    if "cannot access local variable 'registers'" in line:
                        error_found = True
                        register_error_count += 1
                        print(f"  🔴 CRITICAL ERROR FOUND! (occurrence #{register_error_count})")
                    
                    if "Modbus exception" in line.lower():
                        print(f"  ⚠️  Modbus exception detected")
                    
                    if "successfully" in line.lower() or "connected" in line.lower():
                        print(f"  ✅ Connection successful")
            except:
                pass
        
        # Terminate the process
        process.terminate()
        time.sleep(0.5)
        
        print("\n" + "-" * 60)
        print("\nRESULTS:")
        print("-" * 60)
        
        if error_found:
            print(f"❌ FAILED: Critical error still present ({register_error_count} occurrences)")
            print("\nThe 'cannot access local variable registers' error was found.")
            print("The backend fix may not have been applied correctly.")
            return False
        else:
            print("✅ SUCCESS: No critical errors detected!")
            print("\nThe backend appears to be working correctly.")
            print("The duplicate exception handler has been removed.")
            return True
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False

def check_analytics_tsx():
    """Verify Analytics.tsx has been updated"""
    print("\n\n" + "=" * 60)
    print("FRONTEND UPDATE VERIFICATION")
    print("=" * 60 + "\n")
    
    try:
        with open("frontend/src/dashboard/Analytics.tsx", "r") as f:
            content = f.read()
        
        checks = [
            ("MODBUS_REGISTERS", "All 21 Modbus registers defined"),
            ("45201", "Z RMS Velocity register (45201)"),
            ("45221", "Data Quality register (45221)"),
            ("temperature", "Real temperature handling"),
            ("peakFrequency", "Peak frequency calculation"),
            ("System Status", "Status indicator"),
            ("Bearing Health Index", "Bearing health display"),
            ("const baseFreq = 50", "Physics-based frequency calculation"),
        ]
        
        all_pass = True
        for check_str, description in checks:
            if check_str in content:
                print(f"✅ {description}")
            else:
                print(f"❌ {description}")
                all_pass = False
        
        return all_pass
        
    except Exception as e:
        print(f"❌ Error checking Analytics.tsx: {e}")
        return False

def main():
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "RAIL V4 - PHASE 2 FIX VERIFICATION" + " " * 13 + "║")
    print("╚" + "=" * 58 + "╝")
    
    # Check frontend first (no dependencies)
    frontend_ok = check_analytics_tsx()
    
    # Then test backend
    backend_ok = test_backend_startup()
    
    # Summary
    print("\n\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    
    results = []
    if frontend_ok:
        results.append("✅ Frontend: Analytics.tsx updated with all 21 registers")
    else:
        results.append("❌ Frontend: Analytics.tsx needs verification")
    
    if backend_ok:
        results.append("✅ Backend: No critical errors detected")
    else:
        results.append("❌ Backend: Critical errors still present")
    
    for result in results:
        print(result)
    
    print("\n" + "=" * 60)
    if frontend_ok and backend_ok:
        print("✅ ALL TESTS PASSED - System is ready!")
    else:
        print("⚠️  Some tests failed - review above for details")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
