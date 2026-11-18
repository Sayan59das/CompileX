# Scaling plan: 1,000+ concurrent players

**Target.** 1,000 concurrent players with room to 5,000. A question loads in under 200 ms at p95. A submission's result arrives in under
5 s at peak. Losing one server mid-game does not end the game.

**Status (update as tasks land).** Phases 0 and 1 done and pushed (origin/main 17cea44). Phase 2: the admission gate (per-player and total limits on code runs) is
done in the working tree, not yet committed; the judge tier itself waits on the owner's hosting decision. Phases 3 and 4 not started.

**How to work through this.** One phase per session, one task at a time. For each task: read its files, write the tests first, make them pass,
run the commands in `CLAUDE.md`, commit (see its rules), tick the box with the commit hash. Anything marked *decision* is the owner's, so ask.
Do not run a load test or other benchmark without asking.

## What fails first (read from the code, not measured; figures marked "measured" were timed once on the development machine)

1. Code execution: one Docker container per submission, no cap, and the compose file mounts `docker.sock` into the API container (root on the host).
2. All live state in one process: `LobbyManager._lobbies`, Socket.IO without a shared manager, rate limits, generation locks. Redis is
   configured in `config.py` and never used. A restart ends every game.
3. Diagram drawing (matplotlib, about 0.18 s per picture, measured) ran on the event loop.
4. Every generated question was stored whole, diagram included, and each generation first ran an unindexed `DELETE`.
5. CPU in the question service: the N-Queens template solved boards again for every question (about 3 s, measured); typing and starters are rebuilt per request.
6. Database pool of 5 + 5 connections.
7. Content: about 700 distinct questions, so every player sees the same ones.

## Phase 0: quick fixes (done, pushed in 5cc5406)
- [x] Index `issued_questions.issued_at`, added to new databases (model) and existing ones (`_ensure_indexes` in `app/db/database.py`).
- [x] Cap concurrent sandboxes: `MAX_CONCURRENT_EXECUTIONS` (default 8), a semaphore per event loop in `code_executor.py`.
- [x] Draw diagrams off the event loop on `DIAGRAM_WORKERS` (default 2) threads of their own, and remember them (LRU of 256): `_draw_diagram` in `ai_generator.py`.
- [x] Memoise the N-Queens solver (`_n_queens_solutions`).
- [x] `docker-compose.yml`: the `ai` service now runs `main_dynamic:app` on 8001 (the mounted folder's `main.py` is the retired service).
- [x] Latent bug: `DOCKER_AVAILABLE` was undefined when Docker was unreachable at startup, so the first submission raised `NameError` instead of
      using the subprocess fallback.
- Tests: `backend/tests/test_scaling_phase0.py` (20), `question-service/tests/test_template_speed.py` (24). Both run in CI.
- Moved to Phase 1: passing `player_ids` to the question service. Without Redis it only duplicates the backend's own history and would mark
  questions "seen" that a host generated but never showed.

## Phase 1: shared state, several API processes (done, pushed in 5cc5406)
Set `REDIS_URL` and any number of backend processes share lobbies, rate limits, generation and assessment locks, and socket rooms. Without it nothing changes:
the same code runs against an in-process stand-in (`MemoryRedis`).
- [x] `REDIS_URL` setting; `app/services/shared_state.py` (client getter, `MemoryRedis` with the commands the app uses, `locked()`); tests run every scenario
      against both the stand-in and a real Redis so they cannot drift (`tests/state_helpers.py`).
- [x] Rate limits and the per-user generation and assessment locks: `app/services/rate_limit.py`, same limits and messages. Check-and-count runs under a short
      per-user lock; without it 40 parallel requests all passed a limit of 10 on a real Redis (the unit test found this).
- [x] Lobbies: `LobbyManager` is async over one JSON value per lobby, each change a read-modify-write under a per-lobby lock; methods return snapshots. Players are
      stored as a list because a player id can be a number or a socket id. 12 hour TTL.
- [x] Socket.IO `AsyncRedisManager` when `REDIS_URL` is set (`app/main.py`); schema creation at startup is serialised by a lock (two processes starting together on a new
      database collided on `create_all`).
- [x] `player_ids` sent to the question service; compose gives both services `REDIS_URL`.
- [x] Acceptance: `backend/tests/two_process_check.py` starts two real servers on one Redis and one database, plays a lobby across them, kills one mid-game and
      carries on through the other (20 checks, passes). It runs in CI.
- Tests: `test_shared_state.py`, `test_lobby_manager.py`, `test_rate_limit.py`, `test_socket_handlers.py`, `test_phase1_wiring.py`; CI has a Redis service and a pyflakes undefined-name step.
- **Correction to the first plan:** the server has no round timers (timing runs in the browser), so nothing had to move for them.
- **Found on the way:** removing the old rate-limit block also removed imports that `routes.py` still used, so the app did not boot, and no pytest file imported
  `routes.py` or `main.py`. `test_phase1_wiring.py` now imports them and checks every module of the app for undefined names.

**Known limits after Phase 1 (not fixed here):**
- If a process dies, the sockets it held are never told to disconnect, so their players stay in the lobby until their record expires (12 hours) or they rejoin.
  A heartbeat or a short per-player TTL would fix it.
- A client that falls back to long-polling needs the load balancer to keep its requests on one process (sticky sessions). WebSocket clients do not.
- `app/main.py` forces `Connection: close` on every response (for old urllib clients), so every request opens a new connection. Worth revisiting before a load test.
- The win-rate on the stats page reads in-memory leaderboards, which now expire 12 hours after a lobby's last change (before, until the process restarted).
- `docker-compose.yml` now sets `REDIS_URL`, but compose itself was not run.

## Phase 2: judge tier (about 6 to 10 days)
*Decision for the owner:* where the judges run (a VPS or VM with Docker, or a managed Judge0). Render's plain web service cannot host them.
- [x] Evaluate Judge0 and Piston against the five languages and the locked-starter harness (`starter_lock.py`); choose, write down why.
      Written in `docs/judge-evaluation.md` (on paper: both need privileged containers, which are not run on the owner's machine). Recommendation: our own
      judge worker on a separate VM, reusing today's executor. It also lists four gaps in today's sandbox (process limit, read-only files, root user, input
      passed through a shell). The owner's decision is still open.
- [ ] A job queue (Celery is already in `requirements.txt`): submission request returns a job id; the result arrives on the socket and by polling.
- [x] Judge service (`judge/`, built from the same executor as the backend): `POST /run` with a shared secret (`JUDGE_TOKEN`), size limits, 503 and never a local run without
      Docker, no network / memory / process limits and dropped capabilities in each sandbox. The backend sends code there when `JUDGE_URL` is set and answers "temporarily
      unavailable" if the judge cannot be reached, never running code itself. Checked against real Docker with real programs in all five languages (also: compile error, time
      limit, runtime error, no network, a fork bomb contained, wrong token refused). Still open: read-only file system and a non-root user in the sandbox, and a job queue
      (requests are answered synchronously for now; the admission gate bounds the line).
- [x] Admission gate (`app/services/execution_gate.py`, in the working tree): one player may have `MAX_EXECUTIONS_PER_USER` (2) runs going or waiting, and all
      players together `MAX_EXECUTION_BACKLOG` (200); one more is refused with 429, a message and a Retry-After header instead of waiting minutes for a timeout.
      Kept in shared state (sorted sets), so it holds across processes; entries of a dead process drop out after 5 minutes. In front of all four places that run a
      player's code, and a test (`test_execution_gate.py`) fails if a new call to the executor is not inside the gate. Seven deliberate breakages were each caught.
      It works with today's Docker executor and stays in front of the judge tier when that lands.
      Limits: the total is a soft cap (simultaneous admissions can overshoot it by a few); the message says how many are running or waiting, not a position in line;
      a Skill Assessment answer sent by the timer that is refused with 429 is not graded and is closed as unanswered later.
- [x] Setup kit for the judge machine (`judge/deploy/`: compose with HTTPS front door, firewall script, step-by-step README); tests keep its safety choices in place.
      Not validated here: the Caddyfile with the real Caddy binary and the judge image build (both need downloads); do `docker compose config` and `up` on the machine.
- [x] No-Docker judge for hosts like Render (`SANDBOX_MODE=process`, `judge/Dockerfile.render`, `backend/app/services/process_sandbox*.py`): each run is an unprivileged throwaway user
      with limits, no internet sockets (a syscall filter, inherited by children; io_uring refused), a scrubbed environment and a work folder deleted afterwards, behind a startup self-check
      that must pass or the judge refuses to run code. Attacked for real (`judge/checks/`, run by CI): secret theft, signalling the judge, system writes, root, sockets, DNS, memory and
      output floods, cross-run file reads, leftover processes. Found and fixed on the way: orphaned processes stayed as zombies and used up the per-user process limit (tini as process 1).
      Weaker than Docker: a kernel flaw is not stopped, runs share a machine, and a free instance has 512 MB.
- [ ] A wait-time message in the UI. The pages already show the server's text for a refused submit (Practice, Skill Assessment, the Game page's Submit); the Game page's
      Run with sample inputs shows nothing on any error, as before. Ask before touching the frontend.
- [x] `/var/run/docker.sock` is removed from the API container in `docker-compose.yml`; only the `judge` service has it (a test enforces this).
- [ ] Acceptance: 200 simultaneous submissions queue, none lost, results correct, API latency unaffected (the load test in Phase 4 measures this).

## Phase 3: precomputed pool and variants (about 6 to 10 days)
- [ ] Offline builder that, per question and per template variant, stores the typed starters, the quality verdict and the diagram (as a file or object, not
      inside the database row).
- [ ] Template variants: about 100 verified seeds per template, so a template question is `(template, seed)` and is rebuilt on demand. Each template's solver must pass
      `backend/tests/test_diagrams_every_template.py` where it is drawn. 11 templates cannot be served yet (operation lists, uneven rows, square grids).
- [ ] `IssuedQuestion` stores `(ref, user_id, question_id or template+seed)` with a TTL, not the whole question.
- [ ] Serve from the Postgres pool (`pool/`), with Redis per-player history; drop the 1,000-title `exclude_titles` list.
- [ ] Acceptance: a served question does no typing, no template solving and no drawing on the request path.

## Phase 4: prove it (about 4 to 6 days; ask before every run)
- [ ] Metrics: request latency, queue depth, judge latency, event-loop lag.
- [ ] Locust script: register, join a lobby, get a question, submit, on a staging copy.
- [ ] Targets above met at 1,000 concurrent; kill one API process and one judge mid-run.
- [ ] PgBouncer in front of Postgres; tune the pool; autoscale judges by queue depth.

## Not changing
One backend codebase with Redis, not many microservices. The judge tier is the only separate service.
