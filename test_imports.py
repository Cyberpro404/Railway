#!/usr/bin/env python
"""
Test script to validate all imports and basic functionality.
"""

import sys
import traceback


def test_imports():
    """Test all critical imports."""
    errors = []
    
    tests = [
        ("gandiva_error", "from utils.gandiva_error import GandivaError, handle_errors, error_handler"),
        ("errors", "from utils.errors import SensorError, DatabaseError, TrainingError"),
        ("models", "from models import Alert, ConnectionConfig, Thresholds"),
        ("config", "from config.settings import Config"),
        ("database", "from database.operational_db import get_db, init_db"),
        ("training_api", "from api.training_api import setup_training_routes"),
        ("sensor_api", "from api.sensor_api import setup_sensor_routes"),
        ("monitoring_api", "from api.monitoring_api import setup_monitoring_routes"),
        ("logger", "from utils.logger import setup_logger"),
        ("validators", "from utils.validators import validate_threshold_pair, validate_port"),
    ]
    
    for name, import_str in tests:
        try:
            exec(import_str)
            print(f"✓ {name:20} OK")
        except Exception as e:
            print(f"✗ {name:20} FAILED: {e}")
            errors.append((name, e))
            traceback.print_exc()
    
    return errors


def test_classes():
    """Test instantiation of key classes."""
    errors = []
    
    try:
        from utils.gandiva_error import GandivaError
        err = GandivaError("test message")
        assert err.message == "test message"
        assert err.code == "internal_error"
        print(f"✓ GandivaError instantiation OK")
    except Exception as e:
        print(f"✗ GandivaError instantiation FAILED: {e}")
        errors.append(("GandivaError", e))
    
    try:
        from config.settings import Config
        assert Config.DEFAULT_PORT == "COM5"
        assert Config.DEFAULT_Z_RMS_WARNING_MM_S == 2.0
        print(f"✓ Config values OK")
    except Exception as e:
        print(f"✗ Config values FAILED: {e}")
        errors.append(("Config", e))
    
    try:
        from models import ConnectionConfig
        cfg = ConnectionConfig(port="COM5")
        assert cfg.port == "COM5"
        print(f"✓ ConnectionConfig OK")
    except Exception as e:
        print(f"✗ ConnectionConfig FAILED: {e}")
        errors.append(("ConnectionConfig", e))
    
    return errors


if __name__ == "__main__":
    print("=" * 60)
    print("TESTING IMPORTS")
    print("=" * 60)
    import_errors = test_imports()
    
    print("\n" + "=" * 60)
    print("TESTING CLASSES")
    print("=" * 60)
    class_errors = test_classes()
    
    print("\n" + "=" * 60)
    if not import_errors and not class_errors:
        print("ALL TESTS PASSED ✓")
        sys.exit(0)
    else:
        print(f"FAILED: {len(import_errors)} import errors, {len(class_errors)} class errors")
        sys.exit(1)
