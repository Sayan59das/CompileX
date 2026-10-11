"""
Code execution tests.
Run with: python tests/test_execution.py
"""
import json, time
import requests

BASE = "http://127.0.0.1:8000"
RUN_ID = str(int(time.time()))[-5:]


def post(path, data, token=None):
    headers = {"Content-Type": "application/json", "Connection": "close"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.post(BASE + path, json=data, headers=headers, timeout=15)
    try:
        return r.json(), r.status_code
    except Exception:
        return {"raw": r.text}, r.status_code


def check(label, status, expected, body=None):
    icon = "✓" if status == expected else "✗"
    print(f"  {icon} [{status}] {label}")
    if status != expected:
        print(f"      body: {body}")
        raise SystemExit(f"FAILED: {label}")


print("\n=== Code Execution Tests ===\n")

# Register + login
post("/api/v1/auth/register", {"username": f"exec_{RUN_ID}", "email": f"exec_{RUN_ID}@test.com", "password": "password123"})
r, s = post("/api/v1/auth/login", {"username": f"exec_{RUN_ID}", "password": "password123"})
check("Login", s, 200)
token = r["access_token"]

# Create question
test_cases = json.dumps([
    {"input": "1 2",   "output": "3"},
    {"input": "10 20", "output": "30"},
    {"input": "-5 5",  "output": "0"},
])
r, s = post("/api/v1/questions", {
    "title": "Sum Two Numbers",
    "description": "Read two integers, print their sum.",
    "difficulty": "easy", "topic": "math",
    "starter_code": "a, b = map(int, input().split()); print(a + b)",
    "base_points": 100, "time_bonus": 50,
    "max_execution_time_ms": 2000, "test_cases": test_cases,
}, token)
check("Create question", s, 201, r)
qid = r["id"]
print(f"      question_id={qid}")

# Join a lobby so player record exists
r, s = post("/api/v1/lobbies", {"name": "Exec Lobby", "max_players": 2, "time_limit": 600}, token)
check("Create lobby", s, 201, r)
lid = r["id"]
r, s = post(f"/api/v1/lobbies/{lid}/join", {}, token)
check("Join lobby", s, 200, r)

# Correct code
correct_code = "a, b = map(int, input().split())\nprint(a + b)"
r, s = post("/api/v1/submissions", {"code": correct_code, "language": "python", "question_id": qid}, token)
check("Submit correct Python", s, 201, r)
assert r["status"] == "passed", f"Expected passed, got {r['status']}"
assert r["passed_tests"] == 3, f"Expected 3 passed, got {r['passed_tests']}"
assert r["score"] > 0, f"Expected score > 0, got {r['score']}"
print(f"      passed={r['passed_tests']}/{r['total_tests']} score={r['score']}")

# Wrong code
r, s = post("/api/v1/submissions", {"code": "print(999)", "language": "python", "question_id": qid}, token)
check("Submit wrong Python", s, 201, r)
assert r["status"] == "failed", f"Expected failed, got {r['status']}"
assert r["passed_tests"] == 0, f"Expected 0 passed, got {r['passed_tests']}"
print(f"      passed={r['passed_tests']}/{r['total_tests']} score={r['score']}")

print("\n=== All execution tests passed ===\n")
