import asyncio
from pymodbus.client import AsyncModbusTcpClient

async def scan_host(ip, port=502):
    try:
        client = AsyncModbusTcpClient(ip, port=port, timeout=2)
        connected = await client.connect()
        if not connected:
            return
        result = await client.read_holding_registers(address=0, count=30, slave=1)
        if not result.isError():
            regs = list(result.registers)
            non_zero = sum(1 for r in regs if r != 0)
            print(f"  {ip}:{port} => {non_zero} non-zero: {regs[:30]}")
        client.close()
    except:
        pass

async def main():
    # 1. Deep scan 192.168.0.1 - wider register range
    print("=== Deep scan 192.168.0.1 (HR 0-1000, step 50) ===")
    client = AsyncModbusTcpClient("192.168.0.1", port=502, timeout=3)
    await client.connect()
    for start in range(0, 1001, 50):
        try:
            result = await client.read_holding_registers(address=start, count=50, slave=1)
            if not result.isError():
                regs = list(result.registers)
                non_zero_idx = [(start+i, r) for i, r in enumerate(regs) if r != 0]
                if non_zero_idx:
                    print(f"  HR {start:5d}-{start+49}: {non_zero_idx}")
        except: pass
    client.close()

    # 2. Also try ports 502 and 8899 on 192.168.0.x
    print("\n=== Network scan 192.168.0.1-20 on port 502 ===")
    tasks = [scan_host(f"192.168.0.{i}") for i in range(1, 21)]
    await asyncio.gather(*tasks)
    
    print("\n=== Network scan 192.168.0.1-20 on port 8899 ===")
    tasks = [scan_host(f"192.168.0.{i}", 8899) for i in range(1, 21)]
    await asyncio.gather(*tasks)

asyncio.run(main())
