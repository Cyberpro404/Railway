"""
Collect real vibration sensor readings from the rail controller and save to CSV.

Runs continuously (or for a fixed count / duration) and appends rows to
models/dataset.csv.  That CSV is then used automatically by train_model.py to
ground the ML model on observed hardware behaviour instead of purely synthetic data.

Usage
-----
  # Collect indefinitely (Ctrl+C to stop):
  python models/collect_dataset.py

  # Collect exactly 600 samples (~5 min at default 0.5 s / sample):
  python models/collect_dataset.py --count 600

  # Collect for 1 hour:
  python models/collect_dataset.py --duration 3600

  # Faster polling — 1 sample/sec, 1000 samples:
  python models/collect_dataset.py --interval 1.0 --count 1000

  # Different device:
  python models/collect_dataset.py --host 192.168.0.5 --count 200

After collecting, re-train the model:
  python models/train_model.py
"""

import argparse
import csv
import logging
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
MODBUS_HOST      = "192.168.0.1"
MODBUS_PORT      = 502
MODBUS_SLAVE_ID  = 1
DEFAULT_INTERVAL = 0.5          # seconds between samples
DEFAULT_OUTPUT   = Path("models/dataset.csv")

# Column order must stay in sync with FEATURE_NAMES in train_model.py
CSV_COLUMNS = [
    "timestamp",
    "z_axis_rms", "z_rms", "iso_peak_peak", "temperature", "z_true_peak",
    "x_rms", "z_accel", "x_accel", "frequency", "x_frequency",
    "z_band_rms", "x_band_rms", "kurtosis", "x_kurtosis",
    "crest_factor", "x_crest_factor", "z_hf_rms_accel", "z_peak",
    "x_hf_rms_accel", "x_peak", "z_x_ratio",
]

# ---------------------------------------------------------------------------
# Register decoding (duplicated here so this script runs standalone)
# ---------------------------------------------------------------------------

def _get(regs: list[int], idx: int, div: float = 1.0) -> float:
    return regs[idx] / div if idx < len(regs) else 0.0


def _signed(v: float) -> float:
    return v - 655.36 if v > 327.67 else v


def decode(regs: list[int]) -> dict | None:
    """Decode raw register list → physical quantities dict."""
    if len(regs) < 20:
        return None
    z_rms = _get(regs, 1, 1000.0)
    x_rms = _get(regs, 5, 1000.0)
    return {
        "z_axis_rms":     round(_get(regs, 0,  100.0),  4),
        "z_rms":          round(z_rms,               3),
        "iso_peak_peak":  round(_get(regs, 2, 1000.0),  3),
        "temperature":    round(_signed(_get(regs, 3, 100.0)), 1),
        "z_true_peak":    round(_get(regs, 4, 1000.0),  3),
        "x_rms":          round(x_rms,               3),
        "z_accel":        round(_get(regs, 6, 1000.0),  3),
        "x_accel":        round(_get(regs, 7, 1000.0),  3),
        "frequency":      round(_get(regs, 8,   10.0),  1),
        "x_frequency":    round(_get(regs, 9,   10.0),  1),
        "z_band_rms":     round(_get(regs, 10, 1000.0), 3),
        "x_band_rms":     round(_get(regs, 11, 1000.0), 3),
        "kurtosis":       round(_get(regs, 12, 1000.0), 3),
        "x_kurtosis":     round(_get(regs, 13, 1000.0), 3),
        "crest_factor":   round(_get(regs, 14, 1000.0), 3),
        "x_crest_factor": round(_get(regs, 15, 1000.0), 3),
        "z_hf_rms_accel": round(_get(regs, 16, 1000.0), 4),
        "z_peak":         round(_get(regs, 17, 1000.0), 3),
        "x_hf_rms_accel": round(_get(regs, 18, 1000.0), 4),
        "x_peak":         round(_get(regs, 19, 1000.0), 3),
        "z_x_ratio":      round(z_rms / x_rms, 4) if x_rms > 0 else 0.0,
    }


# ---------------------------------------------------------------------------
# Collection loop
# ---------------------------------------------------------------------------

def collect(
    host: str,
    port: int,
    slave: int,
    count: int | None,
    duration: float | None,
    interval: float,
    output: Path,
) -> None:
    try:
        from pymodbus.client import ModbusTcpClient
    except ImportError:
        log.error("pymodbus not installed.  Run:  pip install pymodbus")
        sys.exit(1)

    log.info("Connecting to Modbus %s:%d slave=%d …", host, port, slave)
    client = ModbusTcpClient(host=host, port=port, timeout=3)
    if not client.connect():
        log.error(
            "Cannot connect to %s:%d\n"
            "  • Check that the device is powered and the network cable is connected.\n"
            "  • Verify IP with: ping %s",
            host, port, host,
        )
        sys.exit(1)
    log.info("Connected.")

    output.parent.mkdir(parents=True, exist_ok=True)
    file_exists = output.exists() and output.stat().st_size > 0

    n_collected = 0
    n_errors    = 0
    start_time  = time.monotonic()
    stop        = False

    def _on_sigint(sig, frame):            # allow clean Ctrl+C
        nonlocal stop
        stop = True
        print()
        log.info("Interrupted.")

    signal.signal(signal.SIGINT, _on_sigint)

    mode = (
        f"{count} samples"        if count    is not None else
        f"{duration:.0f} seconds" if duration is not None else
        "indefinitely (Ctrl+C to stop)"
    )
    log.info("Collecting %s at %.1f s intervals → %s", mode, interval, output)

    with open(output, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        if not file_exists:
            writer.writeheader()
            log.info("Created %s", output)
        else:
            existing = sum(1 for _ in open(output, encoding="utf-8")) - 1
            log.info("Appending to existing file (%d rows already present)", existing)

        while not stop:
            # Check stop conditions
            if count    is not None and n_collected >= count:
                break
            if duration is not None and (time.monotonic() - start_time) >= duration:
                break

            # Read registers — try primary address range first, fallback to 0
            raw = None
            for addr in (5200, 0):
                try:
                    result = client.read_holding_registers(
                        address=addr, count=22, slave=slave
                    )
                    if not result.isError() and result.registers:
                        regs = list(result.registers)
                        if any(r != 0 for r in regs):
                            raw = regs
                            break
                except Exception:
                    pass

            if raw:
                data = decode(raw)
                if data:
                    row = {"timestamp": datetime.now(timezone.utc).isoformat()}
                    row.update({k: data[k] for k in CSV_COLUMNS if k != "timestamp"})
                    writer.writerow(row)
                    fh.flush()
                    n_collected += 1
                    n_errors = 0

                    if n_collected % 50 == 0:
                        elapsed = time.monotonic() - start_time
                        rate    = n_collected / elapsed * 60 if elapsed > 0 else 0
                        remain  = f"  ({count - n_collected} remaining)" if count else ""
                        log.info(
                            "%d samples  (%.1f / min)%s  z_rms=%.3f  temp=%.1f°C",
                            n_collected, rate, remain,
                            data["z_rms"], data["temperature"],
                        )
            else:
                n_errors += 1
                if n_errors == 1 or n_errors % 20 == 0:
                    log.warning("Read error #%d — retrying …", n_errors)

            time.sleep(interval)

    client.close()
    log.info(
        "Collection complete: %d samples saved to %s",
        n_collected, output.resolve(),
    )
    if n_collected > 0:
        log.info("Re-train the model now with:  python models/train_model.py")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect real Modbus sensor data for ML training.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python models/collect_dataset.py --count 600\n"
            "  python models/collect_dataset.py --duration 3600\n"
            "  python models/collect_dataset.py --interval 1.0 --count 1000\n"
        ),
    )
    parser.add_argument("--host",     default=MODBUS_HOST,     help="Modbus device IP")
    parser.add_argument("--port",     type=int, default=MODBUS_PORT)
    parser.add_argument("--slave",    type=int, default=MODBUS_SLAVE_ID)
    parser.add_argument("--count",    type=int, default=None,
                        help="Stop after N samples (default: run until Ctrl+C)")
    parser.add_argument("--duration", type=float, default=None,
                        help="Stop after N seconds")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL,
                        help=f"Seconds between readings (default: {DEFAULT_INTERVAL})")
    parser.add_argument("--output",   default=str(DEFAULT_OUTPUT),
                        help=f"CSV output path (default: {DEFAULT_OUTPUT})")
    args = parser.parse_args()

    collect(
        host     = args.host,
        port     = args.port,
        slave    = args.slave,
        count    = args.count,
        duration = args.duration,
        interval = args.interval,
        output   = Path(args.output),
    )


if __name__ == "__main__":
    main()
