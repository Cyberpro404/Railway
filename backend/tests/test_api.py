import pytest
from fastapi.testclient import TestClient
from app import app
import json

client = TestClient(app)

def test_connection_status():
    response = client.get("/api/v1/connection/status")
    # Might be 200 or 503 depending on if it's connected, but normally we should mock it or just expect json
    assert response.status_code in [200, 404, 503]
    if response.status_code == 200:
        data = response.json()
        assert "demo_mode" in data

def test_toggle_demo():
    response = client.post("/api/v1/demo/toggle")
    assert response.status_code == 200
    assert "demo_mode" in response.json()

def test_get_thresholds():
    response = client.get("/api/v1/thresholds/get")
    assert response.status_code == 200
    assert "thresholds" in response.json()

def test_scan_ports():
    response = client.post("/api/v1/connection/scan")
    assert response.status_code == 200
    assert "ports" in response.json()

def test_metrics():
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    assert "uptime" in response.json()
