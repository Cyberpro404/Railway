import asyncio, json, websockets

async def test():
    async with websockets.connect("ws://127.0.0.1:8000/ws") as ws:
        msg = await asyncio.wait_for(ws.recv(), timeout=5)
        d = json.loads(msg)
        sd = d.get("sensor_data", {})
        print(f"source: {d.get('source')}")
        print(f"connected: {d.get('connection_status',{}).get('connected')}")
        print(f"register_source: {sd.get('register_source')}")
        print(f"non_zero_registers: {sd.get('non_zero_registers')}")
        print(f"float32_reg20_21: {sd.get('float32_reg20_21')}")
        print(f"raw_registers: {sd.get('raw_registers')}")

asyncio.run(test())
