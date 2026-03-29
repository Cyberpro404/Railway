
import sys
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFIER")

try:
    logger.info("Checking pymodbus imports...")
    from pymodbus.client import AsyncModbusSerialClient, AsyncModbusTcpClient
    logger.info("✅ pymodbus Async Clients found.")
except ImportError as e:
    logger.error(f"❌ ImportError in pymodbus: {e}")
    # Try to list available attributes in pymodbus.client
    try:
        import pymodbus.client
        logger.info(f"Available in pymodbus.client: {dir(pymodbus.client)}")
    except:
        pass

try:
    logger.info("Checking core module imports...")
    from core.connection_manager import ConnectionManager
    from core.data_receiver import DataReceiver
    from core.realtime_data_stream import RealtimeStream
    logger.info("✅ Core modules imported successfully.")
except ImportError as e:
    logger.error(f"❌ ImportError in core modules: {e}")
except Exception as e:
    logger.error(f"❌ Error importing core modules: {e}")

try:
    logger.info("Checking app.py...")
    from app import app
    logger.info("✅ app.py imported successfully.")
except Exception as e:
    logger.error(f"❌ Error importing app.py: {e}")
    import traceback
    traceback.print_exc()

if __name__ == "__main__":
    logger.info("Verification Complete.")
