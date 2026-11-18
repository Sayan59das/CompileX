# Checks for a running judge

Two scripts that talk to a judge over HTTP and prove it behaves, with real programs and real attacks. They use only the Python standard library.

| Script | What it proves |
|---|---|
| `judge_e2e.py` | Five languages give right answers; a wrong answer, compile error, runtime error and infinite loop are reported; awkward input arrives unchanged; no network; a fork bomb is contained; a wrong token is refused. Works against either judge (Docker or process mode). |
| `process_security_e2e.py` | The extra attacks that matter for the no-Docker judge: stealing the judge's secret, signalling or reading the judge, writing system files, becoming root, internet or packet sockets, DNS, io_uring, memory and output floods, one run reading another's files. |

Run them with the secret the judge was started with:

```bash
JUDGE_TOKEN=<secret> python judge_e2e.py http://127.0.0.1:9000
JUDGE_TOKEN=<secret> python process_security_e2e.py http://127.0.0.1:10000      # no-Docker judge only
```

CI builds `judge/Dockerfile.render`, starts it the way Render does (an unprivileged container with only the few capabilities it needs, 512 MB), and runs
both scripts inside it (`.github/workflows/ci.yml`, job "Judge without Docker"). Do the same locally after any change to the sandbox:

```bash
docker build -f judge/Dockerfile.render -t compilex-judge-process .
docker run -d --name judge-test --network none --cap-drop ALL --cap-add CHOWN --cap-add DAC_OVERRIDE --cap-add FOWNER --cap-add KILL \
  --cap-add SETUID --cap-add SETGID --security-opt no-new-privileges --tmpfs /tmp:exec,mode=1777,size=256m --memory 512m --pids-limit 512 \
  -e JUDGE_TOKEN=some-long-test-secret-123 -v "$PWD/judge/checks:/checks:ro" compilex-judge-process
docker exec -e JUDGE_TOKEN=some-long-test-secret-123 judge-test python /checks/judge_e2e.py http://127.0.0.1:10000
docker exec -e JUDGE_TOKEN=some-long-test-secret-123 judge-test python /checks/process_security_e2e.py http://127.0.0.1:10000
docker rm -f judge-test
```
