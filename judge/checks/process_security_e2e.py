"""Attacks on the process sandbox, through the judge's HTTP API (run inside the container). argv: base_url. env: JUDGE_TOKEN."""
import concurrent.futures
import json
import os
import sys
import urllib.request

BASE = sys.argv[1]
TOKEN = os.environ["JUDGE_TOKEN"]
bad = []


def run(code, language="python", tests=(("", "ok"),), timeout=120):
    body = {"code": code, "language": language, "test_cases": [{"input_data": i, "expected_output": o} for i, o in tests], "time_limit_ms": 3000}
    req = urllib.request.Request(BASE + "/run", data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "X-Judge-Token": TOKEN})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def attack(name, code, expect_output="ok", language="python"):
    data = run(code, language, (("", expect_output),))
    r = data["results"][0]
    ok = r["passed"]
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"   got output={r['output'][:200]!r} error={str(r['error'])[:200]!r}"))
    if not ok:
        bad.append(name)


# 1. the judge's secret is unreachable: not in the environment, not in other processes' memory/environment
attack("the program's environment has no judge secret",
       "import os\nprint('ok' if not any('JUDGE' in k or 'TOKEN' in k for k in os.environ) else 'LEAK ' + str(list(os.environ)))\n")
attack("cannot read the judge process's environment (/proc/1/environ)",
       "try:\n    d = open('/proc/1/environ','rb').read(); print('LEAK' if b'JUDGE_TOKEN' in d else 'ok')\nexcept Exception:\n    print('ok')\n")
attack("cannot read the judge's memory (/proc/1/mem, /proc/1/maps)",
       "bad = False\nfor p in ('/proc/1/mem', '/proc/1/maps', '/proc/1/cmdline_full'):\n    try:\n        open(p, 'rb').read(10); bad = bad or p != '/proc/1/cmdline_full'\n    except Exception:\n        pass\nprint('LEAK' if bad else 'ok')\n")
attack("cannot signal or ptrace the judge (pid 1)",
       "import os, signal\ntry:\n    os.kill(1, signal.SIGKILL); print('KILLED')\nexcept PermissionError:\n    print('ok')\n")

# 2. cannot touch the machine
attack("cannot write the judge's own files or system folders",
       "bad = []\nfor p in ('/srv/main.py', '/srv/app/services/code_executor.py', '/etc/passwd', '/usr/bin/python3', '/usr/local/bin/python'):\n    try:\n        open(p, 'a').write('x'); bad.append(p)\n    except Exception:\n        pass\nprint('ok' if not bad else 'WROTE ' + str(bad))\n")
attack("cannot become root or change root",
       "import os\nr = []\nfor f, a in ((os.setuid, (0,)), (os.seteuid, (0,)), (os.chroot, ('/',)), (os.setgid, (0,))):\n    try:\n        f(*a); r.append(f.__name__)\n    except OSError:\n        pass\nprint('ok' if not r else 'GOT ' + str(r))\n")

# 3. no network of any kind
attack("no internet or packet sockets, no DNS",
       "import socket\nr = []\nfor fam in (socket.AF_INET, socket.AF_INET6, getattr(socket, 'AF_PACKET', 17)):\n    try:\n        socket.socket(fam, socket.SOCK_STREAM); r.append(int(fam))\n    except OSError:\n        pass\ntry:\n    socket.getaddrinfo('example.com', 80); r.append('dns')\nexcept OSError:\n    pass\nprint('ok' if not r else 'OPEN ' + str(r))\n")
attack("a child process cannot open a network socket either (the filter is inherited)",
       "import subprocess, sys\ntry:\n    p = subprocess.run([sys.executable, '-c', 'import socket; socket.socket(socket.AF_INET)'], capture_output=True)\n    print('ok' if p.returncode != 0 else 'CHILD-OPENED')\nexcept Exception as e:\n    print('EXC ' + type(e).__name__ + ' ' + str(e))\n")
attack("io_uring (which could open sockets around the filter) is refused",
       "import ctypes, os\nlibc = ctypes.CDLL(None, use_errno=True)\nr = libc.syscall(425, 4, 0)\nprint('ok' if r == -1 and ctypes.get_errno() == 1 else 'ALLOWED %s %s' % (r, ctypes.get_errno()))\n")

# 4. resource abuse is contained and the judge survives
attack("a memory bomb ends as an error, not a crash",
       "try:\n    x = bytearray(900 * 1024 * 1024); print('ALLOCATED')\nexcept MemoryError:\n    print('ok')\n")
data = run("print('x' * 1000)\nimport sys\nwhile True:\n    sys.stdout.write('y' * 100000)\n", tests=(("", "z"),))
r = data["results"][0]
print(("PASS " if not r["passed"] else "FAIL ") + "an output flood is cut off and reported", "" if not r["passed"] else "(passed?!)")
bad += [] if not r["passed"] else ["output flood"]
d = run("print('ok')\n")
print(("PASS " if d["results"][0]["passed"] else "FAIL ") + "the judge still works after the abuse")
bad += [] if d["results"][0]["passed"] else ["alive after abuse"]

# 5. runs cannot see each other (they run at the same time under different users)
SPY = ("import os, time, glob\nt = time.time()\nopen('mine.txt', 'w').write('secret-of-' + str(os.getuid()))\n"
       "time.sleep(2)\nseen = []\nmine = os.getcwd()\nfor f in glob.glob('/tmp/judge-run-*/*'):\n    if f.startswith(mine + '/'):\n        continue\n    try:\n        open(f).read(); seen.append(f)\n    except Exception:\n        pass\nprint('ok' if not seen else 'READ-OTHER ' + str(seen))\n")
with concurrent.futures.ThreadPoolExecutor(2) as pool:
    outs = list(pool.map(lambda _: run(SPY), range(2)))
for i, d in enumerate(outs):
    p = d["results"][0]["passed"]
    print(("PASS " if p else "FAIL ") + f"concurrent run {i + 1} cannot read the other run's files" + ("" if p else f"   {d['results'][0]['output']!r} {d['results'][0]['error']!r}"))
    bad += [] if p else [f"isolation {i}"]

# 6. what a run leaves behind: a detached background process must not survive (checked from outside by the caller)
run("import os, subprocess\nsubprocess.Popen(['sleep', '300'], start_new_session=True)\nif os.fork() == 0:\n    os.setsid()\n    os.execvp('sleep', ['sleep', '301'])\nprint('ok')\n")

print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PROCESS-SANDBOX ATTACKS CONTAINED")
sys.exit(1 if bad else 0)
