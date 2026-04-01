"""
Modbus Data Test Script
Tests register reads from the DXM controller at 192.168.0.1:502, slave_id=1.
Scans holding registers, input registers, and coils to find all non-zero data.
"""

import asyncio
import struct
import sys
from datetime import datetime

HOST = "192.168.0.1"
PORT = 502
SLAVE_ID = 1

try:
    from pymodbus.client import AsyncModbusTcpClient
except ImportError:
    print("ERROR: pymodbus not installed. Run: pip install pymodbus")
    sys.exit(1)


def decode_float32_be(high: int, low: int) -> float:
    """Decode two 16-bit registers as a big-endian IEEE 754 float32."""
    try:
        return struct.unpack('>f', struct.pack('>HH', high, low))[0]
    except Exception:
        return 0.0


def decode_float32_le(low: int, high: int) -> float:
    """Decode two 16-bit registers as a little-endian word-swap float32."""
    try:
        return struct.unpack('>f', struct.pack('>HH', high, low))[0]
    except Exception:
        return 0.0


async def main():
    print("=" * 70)
    print(f"  MODBUS DATA TEST — {HOST}:{PORT}  slave_id={SLAVE_ID}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    client = AsyncModbusTcpClient(HOST, port=PORT, timeout=5)
    connected = await client.connect()
    if not connected:
        print(f"\n  FAILED to connect to {HOST}:{PORT}")
        return

    print(f"\n  Connected to {HOST}:{PORT}\n")

    # ──────────────────────────────────────────────
    # 1. SCAN HOLDING REGISTERS (Function 03)
    # ──────────────────────────────────────────────
    print("-" * 70)
    print("  [1] HOLDING REGISTERS (Function 03)")
    print("-" * 70)

    all_nonzero_hr = []
    scan_ranges = (
        list(range(0, 500, 50))
        + list(range(500, 1100, 100))
        + [5200, 5250, 5300]
    )

    for start in scan_ranges:
        try:
            result = await client.read_holding_registers(
                address=start, count=50, slave=SLAVE_ID
            )
            if not result.isError():
                regs = list(result.registers)
                for i, val in enumerate(regs):
                    if val != 0:
                        all_nonzero_hr.append((start + i, val))
        except Exception:
            pass

    if all_nonzero_hr:
        print(f"\n  Found {len(all_nonzero_hr)} non-zero holding registers:\n")
        print(f"  {'Addr':>6}  {'Raw':>7}  {'Signed':>8}  {'/ 10':>8}  {'/ 100':>8}  {'/ 1000':>8}")
        print(f"  {'─' * 6}  {'─' * 7}  {'─' * 8}  {'─' * 8}  {'─' * 8}  {'─' * 8}")
        for addr, val in all_nonzero_hr:
            signed = val - 65536 if val > 32767 else val
            print(
                f"  {addr:>6}  {val:>7}  {signed:>8}  "
                f"{val / 10:>8.1f}  {val / 100:>8.2f}  {val / 1000:>8.3f}"
            )

        # Try float32 decoding on consecutive pairs
        print(f"\n  Float32 pair decoding:")
        for i in range(len(all_nonzero_hr) - 1):
            a1, v1 = all_nonzero_hr[i]
            a2, v2 = all_nonzero_hr[i + 1]
            if a2 == a1 + 1:
                f_be = decode_float32_be(v1, v2)
                f_le = decode_float32_le(v1, v2)
                print(f"    R[{a1}:{a2}] = BE: {f_be:.4f}  |  LE(word-swap): {f_le:.4f}")
    else:
        print("\n  No non-zero holding registers found in scanned range.")

    # ──────────────────────────────────────────────
    # 2. SCAN INPUT REGISTERS (Function 04)
    # ──────────────────────────────────────────────
    print(f"\n{'-' * 70}")
    print("  [2] INPUT REGISTERS (Function 04)")
    print("-" * 70)

    all_nonzero_ir = []
    for start in range(0, 500, 50):
        try:
            result = await client.read_input_registers(
                address=start, count=50, slave=SLAVE_ID
            )
            if not result.isError():
                regs = list(result.registers)
                for i, val in enumerate(regs):
                    if val != 0:
                        all_nonzero_ir.append((start + i, val))
        except Exception:
            pass

    if all_nonzero_ir:
        print(f"\n  Found {len(all_nonzero_ir)} non-zero input registers:\n")
        print(f"  {'Addr':>6}  {'Raw':>7}  {'/ 10':>8}  {'/ 100':>8}  {'/ 1000':>8}")
        print(f"  {'─' * 6}  {'─' * 7}  {'─' * 8}  {'─' * 8}  {'─' * 8}")
        for addr, val in all_nonzero_ir:
            print(
                f"  {addr:>6}  {val:>7}  "
                f"{val / 10:>8.1f}  {val / 100:>8.2f}  {val / 1000:>8.3f}"
            )
    else:
        print("\n  No non-zero input registers found in scanned range.")

    # ──────────────────────────────────────────────
    # 3. DETAILED READ — Registers 0-21
    # ──────────────────────────────────────────────
    print(f"\n{'-' * 70}")
    print("  [3] DETAILED: Holding Registers 0-21 (current data_receiver mapping)")
    print("-" * 70)

    try:
        result = await client.read_holding_registers(address=0, count=22, slave=SLAVE_ID)
        if not result.isError():
            regs = list(result.registers)
            labels = [
                "R0  (unused)",
                "R1  z_rms       /1000",
                "R2  (unused)",
                "R3  temperature /100 signed",
                "R4  (unused)",
                "R5  x_rms       /1000",
                "R6  z_peak_accel /1000",
                "R7  x_peak_accel /1000",
                "R8  z_peak_freq  /10",
                "R9  (unused)",
                "R10 (unused)",
                "R11 (unused)",
                "R12 z_kurtosis   /1000",
                "R13 (unused)",
                "R14 z_crest      /1000",
                "R15 (unused)",
                "R16 (unused)",
                "R17 z_peak_vel   /1000",
                "R18 (unused)",
                "R19 x_peak_vel   /1000",
                "R20 (float32 high)",
                "R21 (float32 low)",
            ]
            print()
            for i, val in enumerate(regs):
                marker = " <<<" if val != 0 else ""
                lbl = labels[i] if i < len(labels) else f"R{i}"
                print(f"  [{i:2d}] {val:>6}  {lbl}{marker}")

            f32 = decode_float32_be(regs[20], regs[21]) if len(regs) >= 22 else 0
            if f32 != 0:
                print(f"\n  Float32 from R[20:21] = {f32:.4f}")
    except Exception as e:
        print(f"  Error: {e}")

    # ──────────────────────────────────────────────
    # 4. LIVE STREAM TEST — 5 consecutive reads
    # ──────────────────────────────────────────────
    print(f"\n{'-' * 70}")
    print("  [4] LIVE STREAM TEST — 5 reads at 1s interval")
    print("-" * 70)
    print()

    for tick in range(5):
        try:
            result = await client.read_holding_registers(address=0, count=22, slave=SLAVE_ID)
            if not result.isError():
                regs = list(result.registers)
                nz = [(i, v) for i, v in enumerate(regs) if v != 0]
                ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                if nz:
                    pairs = " | ".join(f"R{i}={v}" for i, v in nz)
                    print(f"  [{ts}] tick {tick + 1}: {pairs}")
                else:
                    print(f"  [{ts}] tick {tick + 1}: all zeros")
            else:
                print(f"  tick {tick + 1}: read error")
        except Exception as e:
            print(f"  tick {tick + 1}: {e}")
        if tick < 4:
            await asyncio.sleep(1)

    # ──────────────────────────────────────────────
    # 5. SUMMARY
    # ──────────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print("  SUMMARY")
    print("=" * 70)

    total_nz = len(all_nonzero_hr) + len(all_nonzero_ir)
    print(f"\n  Device:           {HOST}:{PORT}")
    print(f"  Slave ID:         {SLAVE_ID}")
    print(f"  Holding non-zero: {len(all_nonzero_hr)}")
    print(f"  Input non-zero:   {len(all_nonzero_ir)}")
    print(f"  Total non-zero:   {total_nz}")

    if total_nz > 0:
        print(f"\n  ✓ DATA IS BEING RECEIVED from the device.")
        if all_nonzero_hr:
            addrs = [a for a, _ in all_nonzero_hr]
            print(f"  ✓ Active holding register addresses: {addrs}")
        if all_nonzero_ir:
            addrs = [a for a, _ in all_nonzero_ir]
            print(f"  ✓ Active input register addresses:   {addrs}")
    else:
        print(f"\n  ✗ NO DATA received — all registers are zero.")
        print(f"    Check: sensor power, DXM register mapping, wiring.")

    print()
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
