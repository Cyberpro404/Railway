import asyncio, websockets, json

async def t():
    async with websockets.connect("ws://127.0.0.1:8000/ws") as ws:
        for i in range(3):
            d = json.loads(await ws.recv())
            s = d.get("sensor_data", {})
            print(f"tick {i+1}: z_rms={s.get('z_rms')} x_rms={s.get('x_rms')} temp={s.get('temperature')} freq={s.get('frequency')} nz={s.get('non_zero_registers')}")

asyncio.run(t())
