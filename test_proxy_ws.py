import asyncio, websockets, json

async def t():
    # Test via Vite proxy port 3000 — same URL the browser now uses
    async with websockets.connect("ws://localhost:3000/ws") as ws:
        d = json.loads(await ws.recv())
        s = d.get("sensor_data", {})
        print(f"VIA VITE PROXY: z_rms={s.get('z_rms')} temp={s.get('temperature')} alarm={s.get('alarm_status')} iso={s.get('iso_class')} nz={s.get('non_zero_registers')}")

asyncio.run(t())
