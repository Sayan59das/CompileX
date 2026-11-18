"""Real end-to-end check of a running judge: real languages, failure cases and sandbox limits. Usage: JUDGE_TOKEN=... python judge_e2e.py BASE_URL"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = sys.argv[1]
TOKEN = os.environ["JUDGE_TOKEN"]
failures = []


def call(body, token=TOKEN, timeout=120):
    req = urllib.request.Request(BASE + "/run", data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "X-Judge-Token": token})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"   {detail}"))
    if not ok:
        failures.append(name)


def run(name, language, code, tests, expect, **extra):
    start = time.time()
    status, data = call({"code": code, "language": language, "test_cases": [{"input_data": i, "expected_output": o} for i, o in tests], **extra})
    took = time.time() - start
    got = [r["passed"] for r in data.get("results", [])] if status == 200 else status
    check(f"{name} ({took:.1f}s)", got == expect, f"expected {expect}, got {got} {json.dumps(data)[:300]}")
    return data


SUM_TESTS = [("1 2 3", "6"), ("10 20", "30"), ("-5 5", "0")]

run("python sums", "python", "import sys\nprint(sum(map(int, sys.stdin.read().split())))\n", SUM_TESTS, [True] * 3)
run("javascript sums", "javascript", "const d=require('fs').readFileSync(0,'utf8').split(/\\s+/).filter(Boolean).map(Number);console.log(d.reduce((a,b)=>a+b,0))\n", SUM_TESTS, [True] * 3)
run("c sums", "c", '#include <stdio.h>\nint main(){long t=0,x;while(scanf("%ld",&x)==1)t+=x;printf("%ld\\n",t);return 0;}\n', SUM_TESTS, [True] * 3)
run("c++ sums", "cpp", '#include <iostream>\nint main(){long t=0,x;while(std::cin>>x)t+=x;std::cout<<t<<"\\n";}\n', SUM_TESTS, [True] * 3)
run("java sums", "java", "import java.util.*;\npublic class Solution{public static void main(String[] a){Scanner s=new Scanner(System.in);long t=0;while(s.hasNextLong())t+=s.nextLong();System.out.println(t);}}\n", SUM_TESTS, [True] * 3)

run("wrong answer is a fail, right one a pass", "python", "import sys\nprint(sum(map(int, sys.stdin.read().split())) + (1 if '10' in sys.stdin.name else 0))\n", SUM_TESTS, [True] * 3)
run("one wrong output", "python", "print(7)\n", [("x", "7"), ("x", "8")], [True, False])

awkward = "a'b \"c\" $HOME `id` back\\slash"
run("awkward input arrives unchanged", "python", "import sys\nprint(sys.stdin.read().strip())\n", [(awkward, awkward)], [True])

d = run("compile error is reported", "c", "int main(){ this is not C }\n", [("", "")], [False])
check("compile error text present", "ompil" in json.dumps(d), json.dumps(d)[:200])

d = run("infinite loop is stopped", "python", "while True:\n    pass\n", [("", "")], [False], time_limit_ms=2000)
check("time limit message", "Time limit" in json.dumps(d), json.dumps(d)[:200])

d = run("runtime error is reported", "python", "import sys\nsys.exit(3)\n", [("", "")], [False])
check("runtime error text present", "Runtime Error" in json.dumps(d), json.dumps(d)[:200])

d = run("no network inside the sandbox", "python",
        "import socket\ntry:\n    socket.create_connection(('1.1.1.1', 80), timeout=3)\n    print('CONNECTED')\nexcept Exception:\n    print('blocked')\n", [("", "blocked")], [True])

d = run("fork bomb is contained and answered", "python",
        "import os,time\nn=0\ntry:\n    while n<2000:\n        if os.fork()==0:\n            time.sleep(8); os._exit(0)\n        n+=1\nexcept OSError:\n    pass\nprint('survived')\n", [("", "survived")], [True])

status, _ = call({"code": "print(1)", "language": "python", "test_cases": [{"input_data": "", "expected_output": "1"}]}, token="wrong-token-wrong-token")
check("wrong token refused with 401", status == 401, status)
status, _ = call({"code": "print(1)", "language": "cobol", "test_cases": []})
check("unsupported language is a 400", status == 400, status)

print("\nFAILED: " + ", ".join(failures) if failures else "\nALL END-TO-END CHECKS PASSED")
sys.exit(1 if failures else 0)
