import requests

try:
    resp = requests.post("http://localhost:8000/api/v1/connection/connect", json={"protocol":"TCP", "host":"192.168.0.1"})
    print("Status:", resp.status_code)
    print("JSON:", resp.json())
except Exception as e:
    print(e)
