#!/usr/bin/env python3
"""
collect_good_bad_track.py - Terminal-based training data collection
====================================================================

Standalone script to collect labeled vibration samples for ML training.
Works independently of the web UI.

Usage:
    python scripts/collect_good_bad_track.py

Labels:
    good    -> Normal track, no issues
    gap     -> Expansion gap (intentional, not a defect)
    defect  -> Crack or other defect (needs inspection)
    idle    -> Train idle baseline (special collection)

Output:
    CSV file: gandiva_samples_YYYYMMDD_HHMMSS.csv
"""

import os
import sys
import time
import csv
from datetime import datetime
from typing import Optional, List, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import ConnectionConfig
from core import sensor_reader

# =============================================================================
# CONFIGURATION
# =============================================================================

# Modbus connection settings - adjust to match your sensor
DEFAULT_PORT = "COM5"
DEFAULT_SLAVE_ID = 1
DEFAULT_BAUDRATE = 19200
DEFAULT_PARITY = "N"

# Sampling settings
SAMPLE_INTERVAL_S = 0.5  # Time between samples

# Simple heuristic for train idle detection (mm/s)
# Adjusted for real sensor noise - sensors never reach true 0, always have baseline vibration
IDLE_RMS_THRESHOLD = 0.5  # 0.5 mm/s accounts for sensor noise and ambient vibrations

# CSV columns
CSV_COLUMNS = [
    "timestamp", "rms", "peak", "band_1x", "band_2x",
    "band_3x", "band_5x", "band_7x", "temperature",
    "train_state",  # 'idle' or 'moving' at capture time
    "label",
]

# Label mapping
LABELS = {
    "1": "good",
    "2": "gap", 
    "3": "defect",
    "4": "idle",
}


# =============================================================================
# MAIN COLLECTOR CLASS
# =============================================================================

class DataCollector:
    """Collects labeled sensor samples for training."""
    
    def __init__(self):
        self.samples: List[Dict[str, Any]] = []
        self.current_label: Optional[str] = None
        self.running = False
        self.paused = True
        
        # Counts per label
        self.counts = {"good": 0, "gap": 0, "defect": 0, "idle": 0}
        
        # Sample limits per label (None = no limit)
        self.label_limits = {
            "good": None,
            "gap": None,
            "defect": None,
            "idle": None,
        }
    
    def init_sensor(self, port: str, slave_id: int, baudrate: int, parity: str) -> bool:
        """Initialize the sensor connection."""
        try:
            config = ConnectionConfig(
                port=port,
                slave_id=slave_id,
                baudrate=baudrate,
                parity=parity,
                bytesize=8,
                stopbits=1,
                timeout_s=1.0
            )
            sensor_reader.init_reader(config)
            print(f"✓ Sensor initialized on {port} (slave {slave_id})")
            return True
        except Exception as e:
            print(f"✗ Failed to initialize sensor: {e}")
            return False
    
    def collect_one_sample(self) -> Optional[Dict[str, Any]]:
        """Collect a single sample from the sensor."""
        try:
            status, reading = sensor_reader.read_sensor_once()
            
            if reading is None:
                return None
            
            if not reading.get("ok", False):
                error = reading.get("error", "Unknown error")
                print(f"  [SKIP] Sensor error: {error}")
                return None
            
            return reading
        except Exception as e:
            print(f"  [SKIP] Exception: {e}")
            return None
    
    def add_sample(self, reading: Dict[str, Any], label: str):
        """Add a labeled sample to the collection.

        We also tag each sample with a simple train_state flag
        ("idle" or "moving") based on the same RMS threshold
        heuristic used in the main app.
        """
        # Get RMS and peak values
        rms = reading.get("z_rms_mm_s", 0.0)
        peak = reading.get("z_peak_mm_s", 0.0)
        
        # Get band values (may be 0 if not supported by sensor)
        band_1x = reading.get("band_1x", 0.0)
        band_2x = reading.get("band_2x", 0.0)
        band_3x = reading.get("band_3x", 0.0)
        band_5x = reading.get("band_5x", 0.0)
        band_7x = reading.get("band_7x", 0.0)
        
        # Track if using alternative features
        using_alt = False
        
        # If bands are all 0, use alternative scalar features
        if band_1x == 0 and band_2x == 0 and band_3x == 0:
            using_alt = True
            # Use kurtosis, crest factor, etc. as alternative features
            band_1x = reading.get("z_kurtosis", 0.0)
            band_2x = reading.get("z_crest_factor", 0.0)
            band_3x = reading.get("z_rms_g", 0.0)
            band_5x = reading.get("z_hf_rms_g", 0.0)
            band_7x = peak / (rms + 0.001)  # peak-to-RMS ratio

        # Derive simple train state (idle vs moving) based on RMS
        try:
            z_rms = float(reading.get("z_rms_mm_s", rms))
            x_rms = float(reading.get("x_rms_mm_s", 0.0))
        except Exception:
            z_rms = rms
            x_rms = 0.0

        if z_rms < IDLE_RMS_THRESHOLD and x_rms < IDLE_RMS_THRESHOLD:
            train_state = "idle"
        else:
            train_state = "moving"

        # If collecting idle baseline, only keep idle readings
        if label == "idle" and train_state != "idle":
            print("  [SKIP] Train not idle; waiting for idle to record idle sample")
            return
        
        sample = {
            "timestamp": reading.get("timestamp", datetime.now().isoformat()),
            "rms": rms,
            "peak": peak,
            "band_1x": band_1x,
            "band_2x": band_2x,
            "band_3x": band_3x,
            "band_5x": band_5x,
            "band_7x": band_7x,
            "temperature": reading.get("temp_c", 0.0),
            "train_state": train_state,
            "label": label,
        }
        self.samples.append(sample)
        self.counts[label] += 1
        # Debug output (first sample only per label)
        if self.counts[label] == 1:
            alt_note = " [using alt features]" if using_alt else ""
            print(f"    Features{alt_note}: rms={rms:.3f}, peak={peak:.3f}, kur={band_1x:.3f}, crest={band_2x:.3f}")
        # Check if sample limit reached for this label
        limit = self.label_limits.get(label)
        if limit is not None and self.counts[label] >= limit:
            print(f"\n  [INFO] Sample limit ({limit}) reached for label '{label}'. Pausing collection.")
            self.paused = True
            self.current_label = None
    
    def save_to_csv(self, filename: Optional[str] = None) -> str:
        """Save collected samples to CSV."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"gandiva_samples_{timestamp}.csv"
        
        # Save to data/ directory
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        os.makedirs(data_dir, exist_ok=True)
        filepath = os.path.join(data_dir, filename)
        
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(self.samples)
        
        return filepath
    
    def print_status(self):
        """Print current collection status."""
        total = sum(self.counts.values())
        mode = self.current_label.upper() if self.current_label else "PAUSED"
        print(f"\r  Mode: {mode} | good: {self.counts['good']} | gap: {self.counts['gap']} | defect: {self.counts['defect']} | idle: {self.counts['idle']} | total: {total}   ", end="", flush=True)
    
    def run_collection_loop(self):
        """Main collection loop - runs until stopped."""
        self.running = True
        
        while self.running:
            if not self.paused and self.current_label:
                reading = self.collect_one_sample()
                if reading:
                    self.add_sample(reading, self.current_label)
                    self.print_status()
            
            time.sleep(SAMPLE_INTERVAL_S)


def print_menu():
    print("\n" + "=" * 60)
    print("  GANDIVA - Training Data Collector")
    print("=" * 60)
    print("  1) Start collecting GOOD track samples")
    print("  2) Start collecting EXPANSION GAP samples")
    print("  3) Start collecting CRACK/DEFECT samples")
    print("  4) Start collecting IDLE baseline samples (only when train is idle)")
    print("  5) Start collecting OTHER samples")
    print("  6) Pause collection")
    print("  7) Save and exit")
    print("  8) Discard and exit")
    print("=" * 60)


def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("  GANDIVA - Manual Training Data Collection")
    print("=" * 60)
    
    # Get connection settings
    print("\nSensor Connection Settings:")
    port = input(f"  COM Port [{DEFAULT_PORT}]: ").strip() or DEFAULT_PORT
    slave_id = int(input(f"  Slave ID [{DEFAULT_SLAVE_ID}]: ").strip() or DEFAULT_SLAVE_ID)
    baudrate = int(input(f"  Baudrate [{DEFAULT_BAUDRATE}]: ").strip() or DEFAULT_BAUDRATE)
    parity = input(f"  Parity (N/E/O) [{DEFAULT_PARITY}]: ").strip().upper() or DEFAULT_PARITY
    
    # Initialize collector
    collector = DataCollector()
    
    # Initialize sensor
    if not collector.init_sensor(port, slave_id, baudrate, parity):
        print("\nFailed to connect. Check settings and try again.")
        return
    
    # Test read
    print("\nTesting sensor read...")
    status, reading = sensor_reader.read_sensor_once()
    if reading and reading.get("ok"):
        print(f"  ✓ Got reading: RMS={reading.get('z_rms_mm_s', 0):.3f} mm/s, Temp={reading.get('temp_c', 0):.1f}°C")
    else:
        error = reading.get("error", "No reading") if reading else "No response"
        print(f"  ✗ Test read failed: {error}")
        cont = input("\nContinue anyway? (y/n): ").strip().lower()
        if cont != "y":
            return
    
    # Start collection thread
    import threading
    collect_thread = threading.Thread(target=collector.run_collection_loop, daemon=True)
    collect_thread.start()
    
    # Interactive menu loop
    try:
        while True:
            print_menu()
            collector.print_status()
            print()
            choice = input("\n  Enter choice (1-8): ").strip()
            if choice in ["1", "2", "3", "4", "5"]:
                label = LABELS[choice]
                try:
                    limit = int(input(f"  Enter sample limit for '{label.upper()}' (or leave blank for unlimited): ").strip() or 0)
                except Exception:
                    limit = 0
                collector.label_limits[label] = limit if limit > 0 else None
                collector.current_label = label
                collector.paused = False
                print(f"\n  >> Collecting {label.upper()} samples... (limit: {limit if limit > 0 else 'unlimited'})")
                print("     (Press Enter to return to menu)")
                input()
            elif choice == "6":
                collector.paused = True
                collector.current_label = None
                print("\n  >> Collection PAUSED")
            elif choice == "7":
                collector.running = False
                collector.paused = True
                if len(collector.samples) == 0:
                    print("\n  No samples collected. Nothing to save.")
                else:
                    filepath = collector.save_to_csv()
                    print(f"\n  ✓ Saved {len(collector.samples)} samples to:")
                    print(f"    {filepath}")
                    print(f"\n  Summary:")
                    for k in collector.counts:
                        print(f"    {k}:   {collector.counts[k]}")
                break
            elif choice == "8":
                collector.running = False
                print("\n  Discarding samples and exiting...")
                break
            else:
                print("\n  Invalid choice. Try again.")
    
    except KeyboardInterrupt:
        collector.running = False
        print("\n\n  Interrupted. Samples not saved.")
    
    print("\n  Goodbye!\n")


if __name__ == "__main__":
    main()
