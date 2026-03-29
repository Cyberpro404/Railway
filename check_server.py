
import asyncio
import socket
import sys

async def check_port(host, port, name):
    try:
        reader, writer = await asyncio.open_connection(host, port)
        print(f"✅ {name} is listening on {host}:{port}")
        writer.close()
        await writer.wait_closed()
        return True
    except ConnectionRefusedError:
        print(f"❌ {name} is NOT listening on {host}:{port}")
        return False
    except Exception as e:
        print(f"❌ {name} check error: {e}")
        return False

async def main():
    backend = await check_port("localhost", 8000, "Backend")
    frontend = await check_port("localhost", 3000, "Frontend")
    
    if not backend:
        print("\nDIAGNOSIS: Backend is DOWN.")
        print("Please restart START_ALL.bat.")
    elif not frontend:
        print("\nDIAGNOSIS: Frontend is DOWN.")
        print("Please restart START_ALL.bat. The frontend might take a moment to start.")
    else:
        print("\nDIAGNOSIS: Both servers are UP.")
        print("If web is not loading, try:")
        print("1. Refreshing the browser")
        print("2. Checking browser console (F12) for errors")

if __name__ == "__main__":
    asyncio.run(main())






























































