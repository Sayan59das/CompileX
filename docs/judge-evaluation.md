# Choosing the judge (Phase 2, step 1)

**The question.** Where should players' code run once it leaves the web server? This page compares three options and recommends one.
It was written from the code and from public information (November 2026). Nothing was installed or run for it: both outside judges need
privileged containers, and those are not run on the owner's machine.

## 1. What our app needs from a judge

1. **Five languages:** Python (today `python:3.14-alpine`), C and C++ (`gcc:14`), Java (`eclipse-temurin:17-alpine`), JavaScript (`node:18-alpine`).
2. **Whole programs that read standard input.** The locked starter (`starter_lock.py`) already contains the reading and printing code, so a judge
   only has to run a program, feed it each test's input, and return what it printed.
3. **Limits per run:** time, memory, no network, a cap on processes.
4. **Proof it grades the same.** `backend/tests/test_pool_starters.py` runs 333 checks on the built-in questions' starters in all five languages (the C ones compiled with gcc). Any judge must pass it.
5. **Hidden tests stay ours.** Test inputs and answers are secret (`hidden_tests.py`); a judge run by someone else would receive them.

## 2. The three options

| | A. Judge0 (self-hosted) | B. Piston (self-hosted) | C. Our own judge worker |
|---|---|---|---|
| What it is | A ready-made judge with its own API, database and queue | A smaller ready-made judge with an API | Today's executor (`code_executor.py`) moved to its own machine, fed by a queue |
| Our 5 languages | Yes, but its own versions, not ours | Yes, as installable packages, its own versions | Yes, the exact images we use today |
| Grades the same as today? | Must be re-proved (333 checks), harness may need changes | Must be re-proved (333 checks), harness may need changes | Already proved: the 333 checks pass on these images |
| Privileged container needed | Yes (`privileged: true`). A 2024 advisory showed an escape through it, fixed in v1.13.1 | Yes (`--privileged`) | No: sandboxes are ordinary containers. The worker uses the Docker socket, but on a machine that holds nothing else |
| Maintenance | Last release v1.13.1, April 2024 | Free public service closed Feb 2026 (self-hosting still works) | Ours to maintain (it is code we already have and test) |
| Work to adopt | Medium: new client, new language ids, re-prove grading | Medium: same as Judge0 | Small to medium: a queue and a worker loop around existing code |
| Paid managed version | Yes (no machine to run, cost per run, **our hidden tests go to a third party**) | No longer free | No |

## 3. Recommendation: C, our own judge worker

In simple steps, why:

1. **Lowest risk to grading.** It runs the same images that the 333 starter checks already pass on. A or B would change language versions
   and could change results in ways players notice.
2. **No privileged containers.** Both A and B need them, and that is exactly where Judge0's 2024 escape came from.
3. **Hidden tests never leave our machines.** A managed judge would receive every secret test.
4. **Less to learn and run.** No second API, database or queue product: the queue is Redis, which Phase 1 already uses.

**When A would be better:** if the owner would rather pay per run than look after a judge machine, managed Judge0 is the only
no-machine option. The price is the cost per run and sending hidden tests outside.

## 4. Gaps in today's sandbox (to fix in the worker, whichever option)

Read from `code_executor.py` (not tested yet). Today a sandbox has no network, 256 MB of memory and half a CPU. It does not yet have:

1. **A process limit.** A program that keeps starting copies of itself (a fork bomb) is only stopped by the timeout. Fix: `pids_limit`.
2. **A read-only file system.** The program can write anywhere in its container. Fix: `read_only` plus a small writable `/sandbox` and `/tmp`.
3. **Dropped capabilities and a non-root user.** The program runs as root inside its container. Fix: `cap_drop=["ALL"]`,
   `security_opt=["no-new-privileges"]`, and a plain user.
4. **Input passed safely.** Each test's input goes through `echo "..."` in a shell with only `"` escaped, so an input containing `$`, a backtick or
   a backslash could reach the program changed. Fix: write the input to a file and redirect it, with no shell in between.

Each fix needs the 333 starter checks re-run through real Docker afterwards (a long run: ask first).

**Status (2026-11-18):**
- Done in `code_executor.py`: process limit (128), no swap, all capabilities dropped, `no-new-privileges`, and test input passed as a file (gap 4). Checked
  with real Docker on python, node and C: an input with `'`, `"`, `$`, backticks and a backslash arrives unchanged, and a fork loop stops at the limit.
  The tests in `test_sandbox_hardening.py` keep those settings from being removed.
- Not done: a read-only file system and a non-root user (gaps 2 and 3). Files are copied into the container with `put_archive`, which does not work
  on a read-only root or a tmpfs `/sandbox`, so this needs a small redesign (a writable volume per run) and a full re-run of the 333 checks.
- **New finding:** when Docker cannot be reached, `_execute_with_subprocess` runs the player's code directly on the server with no sandbox at all.
  Fine on a developer's laptop, dangerous in production. It should be switched off there (an environment setting that refuses to run code without Docker).

## 5. What the owner decides

1. **Option C (recommended):** rent one small Linux VM with Docker for the judge worker. More can be added later as the queue grows.
2. **Option A, managed:** no machine, but a cost per run and hidden tests sent to the provider.

Once decided, the next steps are: the four sandbox fixes, the queue (submission returns a job id, the result comes over the socket or by
polling), the worker, and removing `docker.sock` from the web server's compose service.

## Sources

- Judge0 releases (v1.13.1, April 2024): https://github.com/judge0/judge0/releases/tag/v1.13.1
- Judge0 advisory on the privileged-container escape: https://github.com/judge0/judge0/security/advisories/GHSA-h9g2-45c8-89cf
- Judge0 API (batch submissions, `wait`, `callback_url`): https://ce.judge0.com/
- Piston public API closing on 15 Feb 2026 (third-party notice; no official announcement found): https://glama.ai/mcp/servers/alvii147/piston-mcp
- Piston self-hosting (privileged container): https://github.com/engineer-man/piston (via https://github.com/coryvirok/piston)
