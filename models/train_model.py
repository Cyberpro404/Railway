"""
Train the vibration health monitoring ML model.

Workflow
--------
  1. Load REAL sensor readings from models/dataset.csv (if present)
     → Built by running: python models/collect_dataset.py --count 500
  2. Apply physics-based labels to real data
  3. Compute how many synthetic samples each class still needs to reach --synthetic
  4. Generate synthetic ONLY for underrepresented/missing classes
  5. (Optional) collect additional live samples via --samples N
  6. Train RandomForest, save model + artefacts

Classes
-------
  0  Normal       – healthy operation
  1  Warning      – elevated vibration, monitor closely
  2  Critical     – very high vibration or temperature, act now
  3  BearingFault – high kurtosis + high crest factor → bearing impacting
  4  Imbalance    – z_rms >> x_rms, low kurtosis → mechanical imbalance

Usage
-----
  # First collect real data (run while hardware is live):
  python models/collect_dataset.py --count 500

  # Then train with real data + synthetic fill for fault classes:
  python models/train_model.py

  # Skip real data, use pure synthetic (for offline testing):
  python models/train_model.py --no-real-data

  # Include extra live Modbus readings in addition to CSV:
  python models/train_model.py --samples 200
"""

import csv
import sys
import time
import json
import pickle
import logging
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MODBUS_HOST     = "192.168.0.1"
MODBUS_PORT     = 502
MODBUS_SLAVE_ID = 1
SAMPLE_INTERVAL = 0.5        # seconds between live reads
DEFAULT_SYNTH   = 400        # synthetic samples per class

CLASS_NAMES: dict[int, str] = {
    0: "Normal",
    1: "Warning",
    2: "Critical",
    3: "BearingFault",
    4: "Imbalance",
}

# 21 features (all 20 continuous registers + derived z_x_ratio)
FEATURE_NAMES: list[str] = [
    "z_axis_rms",      # R0  – Z-Axis RMS (g)
    "z_rms",           # R1  – Z-RMS velocity mm/s
    "iso_peak_peak",   # R2  – ISO Peak-Peak mm/s
    "temperature",     # R3  – Temperature °C
    "z_true_peak",     # R4  – Z True Peak mm/s
    "x_rms",           # R5  – X-RMS velocity mm/s
    "z_accel",         # R6  – Z-Peak Acceleration g
    "x_accel",         # R7  – X-Peak Acceleration g
    "frequency",       # R8  – Z-Peak Frequency Hz
    "x_frequency",     # R9  – X-Peak Frequency Hz
    "z_band_rms",      # R10 – Z-Band RMS mm/s
    "x_band_rms",      # R11 – X-Band RMS mm/s
    "kurtosis",        # R12 – Z-Kurtosis
    "x_kurtosis",      # R13 – X-Kurtosis
    "crest_factor",    # R14 – Z-Crest Factor
    "x_crest_factor",  # R15 – X-Crest Factor
    "z_hf_rms_accel",  # R16 – Z-Envelope / HF RMS g
    "z_peak",          # R17 – Z-Peak velocity mm/s
    "x_hf_rms_accel",  # R18 – X-Envelope / HF RMS g
    "x_peak",          # R19 – X-Peak velocity mm/s
    "z_x_ratio",       # derived – z_rms / x_rms
]

# ---------------------------------------------------------------------------
# Register decoding
# ---------------------------------------------------------------------------

def _get_reg(registers: list[int], idx: int, div: float = 1.0) -> float:
    if idx >= len(registers):
        return 0.0
    return registers[idx] / div


def _signed(v: float) -> float:
    return v - 655.36 if v > 327.67 else v


def decode_registers(registers: list[int]) -> dict | None:
    """Decode a list of 21+ raw Modbus register values into physical quantities."""
    if not registers or len(registers) < 20:
        return None

    g = lambda idx, div=1.0: _get_reg(registers, idx, div)

    z_rms = g(1, 1000.0)
    x_rms = g(5, 1000.0)

    return {
        "z_axis_rms":     round(g(0, 100.0),   4),
        "z_rms":          round(z_rms,          3),
        "iso_peak_peak":  round(g(2, 1000.0),   3),
        "temperature":    round(_signed(g(3, 100.0)), 1),
        "z_true_peak":    round(g(4, 1000.0),   3),
        "x_rms":          round(x_rms,          3),
        "z_accel":        round(g(6, 1000.0),   3),
        "x_accel":        round(g(7, 1000.0),   3),
        "frequency":      round(g(8, 10.0),     1),
        "x_frequency":    round(g(9, 10.0),     1),
        "z_band_rms":     round(g(10, 1000.0),  3),
        "x_band_rms":     round(g(11, 1000.0),  3),
        "kurtosis":       round(g(12, 1000.0),  3),
        "x_kurtosis":     round(g(13, 1000.0),  3),
        "crest_factor":   round(g(14, 1000.0),  3),
        "x_crest_factor": round(g(15, 1000.0),  3),
        "z_hf_rms_accel": round(g(16, 1000.0),  4),
        "z_peak":         round(g(17, 1000.0),  3),
        "x_hf_rms_accel": round(g(18, 1000.0),  4),
        "x_peak":         round(g(19, 1000.0),  3),
        "z_x_ratio":      round(z_rms / x_rms, 4) if x_rms > 0 else 0.0,
    }


# ---------------------------------------------------------------------------
# Physics-based label assignment
# ---------------------------------------------------------------------------

def label_sample(d: dict) -> int:
    """Assign a health class label using physics-based thresholds."""
    z_rms      = d["z_rms"]
    kurtosis   = d["kurtosis"]
    crest      = d["crest_factor"]
    temp       = d["temperature"]
    z_x_ratio  = d["z_x_ratio"]

    # BearingFault: high kurtosis AND high crest factor
    if kurtosis >= 5.0 and crest >= 4.0:
        return 3

    # Imbalance: z_rms >> x_rms, low kurtosis
    if z_x_ratio >= 2.5 and kurtosis < 4.0 and z_rms >= 2.0:
        return 4

    # Critical: severe vibration or overtemperature
    if z_rms >= 7.1 or temp >= 70.0:
        return 2

    # Warning: elevated but not critical
    if z_rms >= 2.8 or kurtosis >= 3.0:
        return 1

    return 0  # Normal


# ---------------------------------------------------------------------------
# Synthetic data generation
# ---------------------------------------------------------------------------

def generate_synthetic(
    n_per_class: "int | dict[int, int]" = DEFAULT_SYNTH,
    seed: int = 42,
) -> list[dict]:
    """
    Generate physics-informed synthetic samples.

    n_per_class: int  → generate that many per class for ALL 5 classes
                 dict → {label: count} – only generate for listed classes,
                        skipped if count is 0 (used for gap-filling)
    """
    if isinstance(n_per_class, int):
        counts: dict[int, int] = {lbl: n_per_class for lbl in CLASS_NAMES}
    else:
        counts = n_per_class

    rng = np.random.default_rng(seed)

    # (mean, std, low, high) for primary channels per class
    cfgs: dict[int, dict] = {
        0: dict(  # Normal
            z_rms=(0.8, 0.4, 0.1, 2.7),  x_rms=(0.6, 0.3, 0.1, 2.0),
            kurtosis=(2.5, 0.3, 1.0, 2.95), crest=(2.4, 0.3, 1.5, 3.4),
            temp=(35, 5, 20, 54),  z_accel=(0.4, 0.15, 0.05, 1.2),
            x_accel=(0.3, 0.12, 0.05, 1.0), freq=(50, 5, 38, 65),
        ),
        1: dict(  # Warning
            z_rms=(4.0, 1.0, 2.8, 7.0),  x_rms=(2.8, 0.7, 1.5, 5.5),
            kurtosis=(3.8, 0.5, 3.0, 4.9), crest=(3.6, 0.5, 2.5, 4.9),
            temp=(52, 8, 35, 69),  z_accel=(1.8, 0.5, 0.6, 3.5),
            x_accel=(1.2, 0.4, 0.4, 2.8), freq=(55, 8, 38, 72),
        ),
        2: dict(  # Critical
            z_rms=(10.0, 2.5, 7.1, 18.0), x_rms=(5.5, 1.8, 2.0, 13.0),
            kurtosis=(3.0, 1.0, 1.5, 4.9), crest=(3.0, 0.8, 2.0, 4.9),
            temp=(76, 8, 70, 95),  z_accel=(5.0, 1.5, 2.0, 10.0),
            x_accel=(3.0, 1.0, 1.0, 7.0), freq=(60, 10, 38, 85),
        ),
        3: dict(  # BearingFault
            z_rms=(4.5, 1.2, 1.5, 9.0),  x_rms=(3.2, 0.9, 1.0, 7.0),
            kurtosis=(7.5, 1.5, 5.0, 14.0), crest=(6.5, 1.5, 4.0, 12.0),
            temp=(57, 8, 35, 73),  z_accel=(3.2, 0.9, 1.0, 7.0),
            x_accel=(2.2, 0.7, 0.7, 5.0), freq=(53, 7, 35, 72),
        ),
        4: dict(  # Imbalance
            z_rms=(5.5, 1.2, 2.0, 9.0),  x_rms=(1.5, 0.3, 0.3, 2.4),
            kurtosis=(2.8, 0.4, 1.5, 3.9), crest=(3.2, 0.5, 2.0, 4.5),
            temp=(46, 6, 28, 62),  z_accel=(2.8, 0.7, 1.0, 5.0),
            x_accel=(0.9, 0.2, 0.2, 1.7), freq=(48, 5, 36, 62),
        ),
    }

    def bounded(mean, std, lo, hi, n=1):
        return np.clip(rng.normal(mean, std, n), lo, hi)

    samples: list[dict] = []
    for label, c in cfgs.items():
        n = counts.get(label, 0)
        if n == 0:
            continue
        for _ in range(n):
            z_rms     = float(bounded(*c["z_rms"])[0])
            x_rms     = float(bounded(*c["x_rms"])[0])
            kurtosis  = float(bounded(*c["kurtosis"])[0])
            crest     = float(bounded(*c["crest"])[0])
            temp      = float(bounded(*c["temp"])[0])
            z_accel   = float(bounded(*c["z_accel"])[0])
            x_accel   = float(bounded(*c["x_accel"])[0])
            freq      = float(bounded(*c["freq"])[0])

            # Secondary channels derived from primary with noise
            z_peak         = z_rms * float(rng.uniform(1.2, 2.5))
            x_peak         = x_rms * float(rng.uniform(1.2, 2.5))
            x_freq         = freq * float(rng.uniform(0.88, 1.12))
            z_axis_rms     = z_rms * float(rng.uniform(0.93, 1.07))
            iso_peak_peak  = z_peak * float(rng.uniform(1.7, 2.3))
            z_true_peak    = z_peak * float(rng.uniform(0.88, 1.12))
            z_band_rms     = z_rms * float(rng.uniform(0.55, 0.90))
            x_band_rms     = x_rms * float(rng.uniform(0.55, 0.90))
            x_kurtosis     = kurtosis * float(rng.uniform(0.65, 1.35))
            x_crest        = crest * float(rng.uniform(0.65, 1.35))
            z_hf           = z_accel * float(rng.uniform(0.35, 0.70))
            x_hf           = x_accel * float(rng.uniform(0.35, 0.70))
            z_x_ratio      = z_rms / x_rms if x_rms > 0 else 0.0

            row = dict(
                z_axis_rms    = round(z_axis_rms,   4),
                z_rms         = round(z_rms,         4),
                iso_peak_peak = round(iso_peak_peak, 4),
                temperature   = round(temp,          2),
                z_true_peak   = round(z_true_peak,   4),
                x_rms         = round(x_rms,         4),
                z_accel       = round(z_accel,        4),
                x_accel       = round(x_accel,        4),
                frequency     = round(freq,           2),
                x_frequency   = round(x_freq,         2),
                z_band_rms    = round(z_band_rms,     4),
                x_band_rms    = round(x_band_rms,     4),
                kurtosis      = round(kurtosis,       4),
                x_kurtosis    = round(x_kurtosis,     4),
                crest_factor  = round(crest,          4),
                x_crest_factor= round(x_crest,        4),
                z_hf_rms_accel= round(z_hf,           4),
                z_peak        = round(z_peak,         4),
                x_hf_rms_accel= round(x_hf,           4),
                x_peak        = round(x_peak,         4),
                z_x_ratio     = round(z_x_ratio,      4),
                label         = label,
                source        = "synthetic",
            )
            samples.append(row)

    return samples


# ---------------------------------------------------------------------------
# Real data loader
# ---------------------------------------------------------------------------

def load_real_data(csv_path: Path) -> list[dict]:
    """
    Load real hardware readings from a CSV produced by collect_dataset.py.
    Physics-based labels are applied automatically.
    Returns [] if the file does not exist or is empty.
    """
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return []

    samples: list[dict] = []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                data: dict[str, float] = {
                    k: float(v)
                    for k, v in row.items()
                    if k != "timestamp"
                }
                # Back-fill z_x_ratio if an older CSV omitted it
                if "z_x_ratio" not in data:
                    z = data.get("z_rms", 0.0)
                    x = data.get("x_rms", 0.0)
                    data["z_x_ratio"] = round(z / x, 4) if x > 0 else 0.0
                data["label"]  = label_sample(data)
                data["source"] = "real"
                samples.append(data)
            except (ValueError, KeyError):
                continue

    log.info("Loaded %d real samples from %s", len(samples), csv_path)
    return samples


# ---------------------------------------------------------------------------
# Live Modbus data collection
# ---------------------------------------------------------------------------

def collect_live_data(
    n_samples: int,
    host: str = MODBUS_HOST,
    port: int  = MODBUS_PORT,
    slave: int = MODBUS_SLAVE_ID,
) -> list[dict]:
    """
    Collect real register readings from the hardware controller.
    Requires pymodbus installed (sync client).
    Returns empty list if connection fails or pymodbus is unavailable.
    """
    try:
        from pymodbus.client import ModbusTcpClient
    except ImportError:
        log.warning("pymodbus not available – skipping live data collection.")
        return []

    log.info("Connecting to Modbus %s:%d slave=%d …", host, port, slave)
    client = ModbusTcpClient(host=host, port=port, timeout=3)
    if not client.connect():
        log.warning("Cannot reach Modbus device – skipping live data collection.")
        return []

    log.info("Connected. Collecting %d samples …", n_samples)
    samples: list[dict] = []
    try:
        for i in range(n_samples):
            raw = None
            for addr in (5200, 0):          # try primary range, then fallback
                result = client.read_holding_registers(
                    address=addr, count=22, slave=slave
                )
                if not result.isError() and result.registers:
                    regs = result.registers
                    if any(r != 0 for r in regs):
                        raw = regs
                        break

            if raw:
                data = decode_registers(list(raw))
                if data:
                    data["label"]  = label_sample(data)
                    data["source"] = "real"
                    samples.append(data)

            if (i + 1) % 50 == 0:
                log.info("  %d / %d samples collected", i + 1, n_samples)

            time.sleep(SAMPLE_INTERVAL)

    except KeyboardInterrupt:
        log.warning("Interrupted – collected %d live samples.", len(samples))
    finally:
        client.close()

    return samples


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train_and_save(
    samples: list[dict],
    feature_names: list[str],
    output_dir: Path,
) -> tuple[RandomForestClassifier, StandardScaler, float]:
    """Train a RandomForestClassifier, evaluate it, and persist the artefacts."""

    df = pd.DataFrame(samples)
    X  = df[FEATURE_NAMES].values.astype(np.float32)
    y  = df["label"].values.astype(int)

    # ---- Source breakdown ------------------------------------------------
    real_count  = int((df.get("source", pd.Series()) == "real").sum()) if "source" in df.columns else 0
    synth_count = len(df) - real_count

    # ---- Dataset summary --------------------------------------------------
    print(f"\n{'='*60}")
    print(f"Dataset: {len(df):,} total samples  ({real_count:,} real / {synth_count:,} synthetic)")
    for lbl, name in CLASS_NAMES.items():
        cnt = int((y == lbl).sum())
        pct = 100.0 * cnt / len(y)
        r   = int(((df["source"] == "real") & (df["label"] == lbl)).sum()) if "source" in df.columns else 0
        print(f"  Class {lbl}  {name:<12s}: {cnt:5d} ({pct:.1f}%)  [{r} real / {cnt-r} synth]")

    # ---- Train / test split -----------------------------------------------
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    # ---- Scale ------------------------------------------------------------
    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)
    X_te_s = scaler.transform(X_te)

    # ---- Train ------------------------------------------------------------
    print(f"\nTraining RandomForest (n_estimators=200, max_depth=15, class_weight='balanced') …")
    clf = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    clf.fit(X_tr_s, y_tr)

    # ---- Evaluate ---------------------------------------------------------
    y_pred  = clf.predict(X_te_s)
    acc     = accuracy_score(y_te, y_pred)
    report  = classification_report(
        y_te, y_pred, target_names=[CLASS_NAMES[k] for k in sorted(CLASS_NAMES)]
    )
    cm      = confusion_matrix(y_te, y_pred)

    print(f"\nTest accuracy : {acc*100:.1f}%")
    print("\nClassification report:\n", report)
    print("Confusion matrix:\n", cm)

    # ---- Cross-validation -------------------------------------------------
    X_s     = scaler.transform(X)
    cv      = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_sc   = cross_val_score(clf, X_s, y, cv=cv, scoring="accuracy")
    print(f"\n5-fold CV: {cv_sc.mean()*100:.1f}% ± {cv_sc.std()*100:.1f}%")

    # ---- Feature importance -----------------------------------------------
    importances = dict(zip(feature_names, clf.feature_importances_))
    top10 = sorted(importances.items(), key=lambda x: x[1], reverse=True)[:10]
    print("\nTop-10 features by importance:")
    for fname, imp in top10:
        print(f"  {fname:<20s}: {imp:.4f}")

    # ---- Persist -----------------------------------------------------------
    output_dir.mkdir(parents=True, exist_ok=True)

    # Model pickle (dict so ml_engine.py can load it directly)
    model_path = output_dir / "rf_model.pkl"
    with open(model_path, "wb") as fh:
        pickle.dump({"model": clf, "scaler": scaler}, fh)
    print(f"\n✓  Model saved        : {model_path}")

    # Feature names JSON  (read by ml_engine.py at startup)
    fn_path = output_dir / "feature_names.json"
    with open(fn_path, "w") as fh:
        json.dump(feature_names, fh, indent=2)
    print(f"✓  Feature names saved : {fn_path}")

    # Metadata JSON
    meta = {
        "feature_names":   feature_names,
        "class_names":     {str(k): v for k, v in CLASS_NAMES.items()},
        "n_features":      len(feature_names),
        "n_classes":       len(CLASS_NAMES),
        "n_samples_train": int(len(X_tr)),
        "n_samples_test":  int(len(X_te)),
        "n_real":          real_count,
        "n_synthetic":     synth_count,
        "accuracy":        round(float(acc), 4),
        "cv_mean":         round(float(cv_sc.mean()), 4),
        "cv_std":          round(float(cv_sc.std()),  4),
        "trained_at":      datetime.now(timezone.utc).isoformat(),
        "feature_importance": {k: round(float(v), 6) for k, v in importances.items()},
    }
    meta_path = output_dir / "model_metadata.json"
    with open(meta_path, "w") as fh:
        json.dump(meta, fh, indent=2)
    print(f"✓  Metadata saved      : {meta_path}")

    # Human-readable training report text
    report_path = output_dir / "training_report.txt"
    lines = [
        "Railway Vibration Health Monitor – Training Report",
        "=" * 60,
        f"Trained at : {meta['trained_at']}",
        f"",
        f"Dataset summary",
        f"  Total samples : {len(df):,}  ({real_count:,} REAL  /  {synth_count:,} synthetic)",
    ]
    for lbl, name in CLASS_NAMES.items():
        cnt = int((y == lbl).sum())
        r   = int(((df["source"] == "real") & (df["label"] == lbl)).sum()) if "source" in df.columns else 0
        lines.append(f"  Class {lbl}  {name:<12s}: {cnt:5d}  [{r} real / {cnt-r} synth]")
    lines += [
        f"",
        f"Test accuracy : {acc*100:.1f}%",
        f"CV 5-fold     : {cv_sc.mean()*100:.1f}% ± {cv_sc.std()*100:.1f}%",
        f"",
        "Classification report:",
        report,
        "Confusion matrix:",
        str(cm),
        "",
        "Feature importances (all):",
    ]
    for fname, imp in sorted(importances.items(), key=lambda x: x[1], reverse=True):
        lines.append(f"  {fname:<22s}: {imp:.6f}")
    report_path.write_text("\n".join(lines))
    print(f"✓  Training report     : {report_path}")

    return clf, scaler, acc


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train the railway vibration health monitoring RandomForest model."
    )
    parser.add_argument("--host",         default=MODBUS_HOST)
    parser.add_argument("--port",         type=int, default=MODBUS_PORT)
    parser.add_argument("--slave",        type=int, default=MODBUS_SLAVE_ID)
    parser.add_argument("--dataset",      default="models/dataset.csv",
                        help="Real sensor CSV from collect_dataset.py (loaded automatically if present)")
    parser.add_argument("--samples",      type=int, default=0,
                        help="Live Modbus samples to collect right now (0 = skip)")
    parser.add_argument("--synthetic",    type=int, default=DEFAULT_SYNTH,
                        help=f"Target samples per class; synthetic fills the gap (default: {DEFAULT_SYNTH})")
    parser.add_argument("--no-real-data", action="store_true",
                        help="Ignore dataset CSV — train on synthetic only")
    parser.add_argument("--output",       default="models")
    args = parser.parse_args()

    output_dir     = Path(args.output)
    all_samples:   list[dict]     = []
    real_by_class: dict[int, int] = {lbl: 0 for lbl in CLASS_NAMES}
    dataset_path   = Path(args.dataset)

    # ── Step 1: load real CSV data ─────────────────────────────────────────
    print(f"\n{'='*60}")
    print("STEP 1 – Loading real sensor data …")
    print(f"{'='*60}")
    if not args.no_real_data:
        real_samples = load_real_data(dataset_path)
        if real_samples:
            for s in real_samples:
                real_by_class[s["label"]] = real_by_class.get(s["label"], 0) + 1
            all_samples.extend(real_samples)
            print(f"Loaded {len(real_samples):,} real samples from {dataset_path}")
            for lbl, name in CLASS_NAMES.items():
                cnt = real_by_class[lbl]
                bar = "█" * min(40, cnt // 5) if cnt else "(none)"
                print(f"  Class {lbl}  {name:<12s}: {cnt:5d}  {bar}")
        else:
            print(f"No real data found at {dataset_path}")
            print(f"  → Tip: run  python models/collect_dataset.py --count 600")
            print(f"    (~5 minutes) to collect real sensor readings before training.")
    else:
        print("[Skipped] Real data loading (--no-real-data flag set).")

    # ── Step 2: optional live collection ──────────────────────────────────
    print(f"\n{'='*60}")
    if args.samples > 0:
        print(f"STEP 2 – Collecting {args.samples} live readings from {args.host}:{args.port} …")
        print(f"{'='*60}")
        live = collect_live_data(args.samples, args.host, args.port, args.slave)
        if live:
            for s in live:
                real_by_class[s["label"]] = real_by_class.get(s["label"], 0) + 1
            all_samples.extend(live)
            print(f"Added {len(live):,} live samples.")
        else:
            print("No live samples collected – check hardware connection.")
    else:
        print("STEP 2 – [Skipped] Inline live collection (pass --samples N to collect now).")
        print(f"{'='*60}")

    # ── Step 3: synthetic gap-fill ─────────────────────────────────────────
    print(f"\n{'='*60}")
    print("STEP 3 – Synthetic gap-fill …")
    print(f"{'='*60}")
    target   = args.synthetic
    deficits = {lbl: max(0, target - real_by_class[lbl]) for lbl in CLASS_NAMES}
    total_synth = sum(deficits.values())

    if total_synth > 0:
        print(f"Target {target} samples/class – synthetic fill:")
        for lbl, name in CLASS_NAMES.items():
            have = real_by_class[lbl]
            need = deficits[lbl]
            if need > 0:
                print(f"  Class {lbl}  {name:<12s}: {have} real  +{need} synthetic → {have+need}")
            else:
                print(f"  Class {lbl}  {name:<12s}: {have} real  (sufficient – no synthetic)")
        synthetic = generate_synthetic(deficits)
        all_samples.extend(synthetic)
        print(f"Generated {len(synthetic):,} synthetic fill samples.")
    else:
        print(f"All classes have ≥{target} real samples – no synthetic data needed.")

    if not all_samples:
        print("ERROR: no samples to train on. Exiting.")
        sys.exit(1)

    # ── Step 4: train ──────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("STEP 4 – Training model …")
    print(f"{'='*60}")
    _, _, acc = train_and_save(all_samples, FEATURE_NAMES, output_dir)

    total_real = sum(real_by_class.values())
    print(f"\n{'='*60}")
    print(f"DONE  – Accuracy     : {acc*100:.1f}%")
    print(f"        Real samples : {total_real:,} / {len(all_samples):,}  ({100*total_real/len(all_samples):.0f}%)")
    print(f"        Artefacts    : {output_dir.resolve()}/")
    if total_real == 0:
        print(f"  ⚠  Model trained on SYNTHETIC data only.")
        print(f"     Run 'python models/collect_dataset.py --count 600' then re-train")
        print(f"     to ground the model on real sensor behaviour.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
