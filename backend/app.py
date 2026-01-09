"""
Gandiva Pro - FastAPI Industrial Backend
Real-time railway condition monitoring with ML predictions
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any
import json
from pydantic import BaseModel

try:
    from core.modbus_safe import ModbusClient
    from core.ml_engine import MLEngine
    from core.iso_calculator import ISOCalculator
    from database import init_db, get_db
    from api.v1 import thresholds, alerts
except ImportError as e:
    logging.error(f"Import error: {e}")
    logging.error("Please ensure all dependencies are installed: pip install -r requirements.txt")
    raise

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Global state
modbus_client: ModbusClient = None
ml_engine: MLEngine = None
iso_calculator: ISOCalculator = None
active_connections: List[WebSocket] = []
data_buffer: Dict[str, Any] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources"""
    global modbus_client, ml_engine, iso_calculator
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Initialize Modbus client
    modbus_client = ModbusClient()
    logger.info("Modbus client initialized")
    
    # Initialize ML engine
    ml_engine = MLEngine()
    await ml_engine.load_model()
    logger.info("ML engine initialized")
    
    # Initialize ISO calculator
    iso_calculator = ISOCalculator()
    logger.info("ISO10816 calculator initialized")
    
    # Start background polling task
    asyncio.create_task(poll_modbus_loop())
    
    yield
    
    # Cleanup
    if modbus_client:
        await modbus_client.disconnect()
    logger.info("Application shutdown complete")

app = FastAPI(
    title="Gandiva Pro API",
    description="AI-Designed Professional Industrial Dashboard for Railway Condition Monitoring",
    version="4.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(thresholds.router, prefix="/api/v1/thresholds", tags=["thresholds"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])

@app.get("/")
async def root():
    return {
        "name": "Gandiva Pro",
        "version": "4.0.0",
        "status": "operational"
    }

@app.get("/api/v1/health")
async def health_check():
    """System health check"""
    return {
        "status": "healthy",
        "modbus_connected": modbus_client.is_connected() if modbus_client else False,
        "ml_model_loaded": ml_engine.is_model_loaded() if ml_engine else False,
        "active_connections": len(active_connections),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/v1/connection/status")
async def connection_status():
    """Get current connection status"""
    if not modbus_client:
        return {
            "connected": False,
            "port": None,
            "baud": None,
            "slave_id": None,
            "uptime_seconds": 0,
            "last_poll": None,
            "packet_loss": 0.0,
            "auto_reconnect": True
        }
    
    return modbus_client.get_status()

@app.post("/api/v1/connection/scan")
async def scan_ports():
    """Scan available COM ports"""
    if not modbus_client:
        raise HTTPException(status_code=500, detail="Modbus client not initialized")
    ports = await modbus_client.scan_ports()
    return {"ports": ports}

class ConnectionRequest(BaseModel):
    port: str
    baud: int = 19200
    slave_id: int = 1

@app.post("/api/v1/connection/connect")
async def connect_modbus(request: ConnectionRequest):
    """Connect to Modbus device"""
    if not modbus_client:
        raise HTTPException(status_code=500, detail="Modbus client not initialized")
    success = await modbus_client.connect(request.port, request.baud, request.slave_id)
    if success:
        return {"status": "connected", "port": request.port, "baud": request.baud, "slave_id": request.slave_id}
    raise HTTPException(status_code=400, detail="Failed to connect")

@app.post("/api/v1/connection/disconnect")
async def disconnect_modbus():
    """Disconnect from Modbus device"""
    if not modbus_client:
        raise HTTPException(status_code=500, detail="Modbus client not initialized")
    await modbus_client.disconnect()
    return {"status": "disconnected"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time data streaming"""
    await websocket.accept()
    active_connections.append(websocket)
    logger.info(f"WebSocket connected. Total connections: {len(active_connections)}")
    
    try:
        while True:
            # Send latest data every second (1Hz)
            if data_buffer:
                await websocket.send_json(data_buffer)
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(active_connections)}")

async def poll_modbus_loop():
    """Background task to poll Modbus and update data buffer"""
    global data_buffer
    
    while True:
        try:
            if modbus_client and modbus_client.is_connected():
                # Read registers 45201-45217 (17 registers)
                data = await modbus_client.read_safe_registers()
                
                if data:
                    # Calculate features for ML
                    features = ml_engine.calculate_features(data) if ml_engine else {}
                    
                    # Get ML prediction
                    prediction = None
                    if ml_engine and ml_engine.is_model_loaded():
                        prediction = ml_engine.predict(features)
                    
                    # Calculate ISO10816 severity
                    iso_severity = None
                    if iso_calculator and 'z_rms' in data:
                        iso_severity = iso_calculator.calculate_severity(data['z_rms'])
                    
                    # Build data buffer
                    data_buffer = {
                        "timestamp": datetime.utcnow().isoformat(),
                        "sensor_data": data,
                        "features": features,
                        "ml_prediction": prediction,
                        "iso_severity": iso_severity,
                        "connection_status": modbus_client.get_status()
                    }
                    
                    # Broadcast to all WebSocket connections
                    if active_connections:
                        disconnected = []
                        for conn in active_connections:
                            try:
                                await conn.send_json(data_buffer)
                            except Exception as e:
                                logger.error(f"Error sending to WebSocket: {e}")
                                disconnected.append(conn)
                        
                        # Remove disconnected clients
                        for conn in disconnected:
                            if conn in active_connections:
                                active_connections.remove(conn)
            
            await asyncio.sleep(1.0)  # 1Hz polling
            
        except Exception as e:
            logger.error(f"Error in polling loop: {e}")
            await asyncio.sleep(1.0)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

