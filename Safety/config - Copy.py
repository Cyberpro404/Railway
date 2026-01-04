import os

# Base directory of the project
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ML Model Files
MODEL_FILE = os.path.join(BASE_DIR, "gandiva_vib_model.joblib")
SCALER_FILE = os.path.join(BASE_DIR, "gandiva_scaler.joblib")
TRAINING_DATA_FILE = os.path.join(BASE_DIR, "training_data.json")

# API Configuration
API_HOST = "0.0.0.0"
API_PORT = 8000

# Database Configuration
DATABASE_URL = "sqlite:///./gandiva.db"

# Sensor Configuration
SENSOR_PORT = "COM5"
SENSOR_SLAVE_ID = 1
SENSOR_FREQUENCY = 3200.0  # Hz
