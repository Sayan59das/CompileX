"""
Shared HTTP helper using requests (compatible with Python 3.14 + socketio ASGI).
Uses a fresh connection per request to avoid RemoteDisconnected errors.
"""
import requests

def http_post(base, path, data, token=None):
    headers = {"Content-Type": "application/json", "Connection": "close"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        r = requests.post(base + path, json=data, headers=headers, timeout=15)
        try:
            return r.json(), r.status_code
        except Exception:
            return {"raw": r.text}, r.status_code
    except Exception as e:
        return {"error": str(e)}, 0

def http_get(base, path, token=None):
    headers = {"Connection": "close"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        r = requests.get(base + path, headers=headers, timeout=15)
        try:
            return r.json(), r.status_code
        except Exception:
            return {"raw": r.text}, r.status_code
    except Exception as e:
        return {"error": str(e)}, 0
