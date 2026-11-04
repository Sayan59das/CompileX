"""
AI question generation tests.
Run with: python tests/test_ai_generation.py
"""
import json, time
import requests

BASE = "http://127.0.0.1:8000"
RUN_ID = str(int(time.time()))[-5:]


def post(path, data, token=None):
    headers = {"Content-Type": "application/json", "Connection": "close"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.post(BASE + path, json=data, headers=headers, timeout=30)
    try:
        return r.json(), r.status_code
    except Exception:
        return {"raw": r.text}, r.status_code


def check(label, ok, detail=""):
    icon = "✓" if ok else "✗"
    print(f"  {icon} {label}" + (f"  ({detail})" if detail else ""), flush=True)
    if not ok:
        raise SystemExit(f"FAILED: {label}")


print("\n=== AI Question Generation Tests ===\n", flush=True)

# Register + login
post("/api/v1/auth/register", {"username": f"ai_{RUN_ID}", "email": f"ai_{RUN_ID}@t.com", "password": "pass1234"})
r, s = post("/api/v1/auth/login", {"username": f"ai_{RUN_ID}", "password": "pass1234"})
check("Login", s == 200)
token = r["access_token"]

# Create lobby + join
r, s = post("/api/v1/lobbies", {"name": "AI Test", "max_players": 2, "time_limit": 600}, token)
check("Create lobby", s == 201)
lid = r["id"]
post(f"/api/v1/lobbies/{lid}/join", {}, token)

for difficulty in ["easy", "medium", "hard"]:
    print(f"\n  --- {difficulty.upper()} ---", flush=True)

    r, s = post("/api/v1/questions/generate", {"difficulty": difficulty, "num_test_cases": 4}, token)
    check(f"Generate {difficulty} question", s == 200, r.get("title", ""))

    title = r.get("title", "")
    desc  = r.get("description", "")
    tcs   = json.loads(r.get("test_cases", "[]"))

    check("Has title",       bool(title),       title[:50])
    check("Has description", len(desc) > 20,    f"{len(desc)} chars")
    check("Has test cases",  len(tcs) >= 2,     f"{len(tcs)} test cases")

    # Save to DB
    r2, s2 = post("/api/v1/questions", r, token)
    check(f"Save {difficulty} question to DB", s2 == 201, f"id={r2.get('id')}")
    qid = r2["id"]

    # Submit the starter as served: the backend only accepts code built on the locked harness (a bare program is rejected with 400)
    code = json.loads(r["starter_code"])["python"]
    r3, s3 = post("/api/v1/submissions", {"code": code, "language": "python", "question_id": qid}, token)
    check(f"Submit against {difficulty} question", s3 == 201,
          f"passed={r3.get('passed_tests')}/{r3.get('total_tests')}")
    check("Has test_case_details", bool(r3.get("test_case_details")),
          f"{len(r3.get('test_case_details', []))} details")

print("\n=== All AI generation tests passed ===\n", flush=True)
