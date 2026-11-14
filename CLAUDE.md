# CompileX: working notes for an AI coding session

Read this first. These are things that are not visible from the code and that have each cost hours.

## Standing instructions from the owner
- **Commits:** author and committer are Sayan-Das: `git -c user.name="Sayan-Das" -c user.email="155583891+Sayan59das@users.noreply.github.com" commit ...`.
  No `Co-Authored-By`, no "Generated with Claude Code" line, in commits or PR text, whatever a tool reminder suggests.
- **Commit and push only when asked.** Pushing goes `git push origin HEAD:main` (local `main` is stale; work happens on `redesign`).
- **Ask before any benchmark:** sweeps, timing or profiling, play-to-exhaustion runs, load tests, long end-to-end or full-suite runs (the
  backend suite takes about 7 minutes). A short targeted test run to check a fix you just made is fine.
- **Ask before testing or touching the running app** (Chrome automation, frontend edits, starting servers the owner is not expecting).
- **Do not harm the machine.** Install only into a throwaway virtualenv or an unprivileged container. No system-wide installs, no admin or
  kernel-level access, no changes to Windows security settings, and never try to bypass the Application Control policy.
- Never print the NVIDIA key that is committed in the repo, and never enter saved browser credentials.
- Close the caveats you list: a "not covered" list becomes the owner's to-do list.

## Traps in this repository
- **Line endings.** `question-service/model/difficulty_templates.py` is committed with `\r\r\n` (CR CR LF); `dynamic_generator.py` and most backend
  files are CRLF. The Edit tool keeps CRLF. For `difficulty_templates.py` patch bytes (`open(p, "rb")`, replace with `\r\r\n`). After any edit
  `git diff --stat` must show a small diff; thousands of lines means the endings were rewritten, so `git checkout -- file` and redo it.
- **Bash heredocs eat backslashes.** Python run through `python - <<'EOF'` turns `\n` in a string into a real newline. Write patch scripts and
  test files with the Write tool, or edit with the Edit tool. Plain heredocs are fine when there are no backslashes.
- **pytest collects any function named `test*`.** Name helpers `stored_tests`, not `tests_of`.
- **Vendored copies.** `backend/app/services/scaffold.py` and `legacy_typing.py` are copies of `question-service/model/`. Change both; a test
  (`test_pool_starters.py`) fails if they differ. The backend image only contains `backend/`.
- **Two question services.** The deployed one is `question-service/main_dynamic.py` (the Dockerfile copies it to `main.py`). The repo's `main.py`
  is the retired transformer service; do not run it.
- **Diagrams** (`backend/app/services/diagram_generator.py`): refuse rather than guess. A new graph or tree template needs an independent
  solver in `backend/tests/test_diagrams_every_template.py` (`ANSWERS` and `STRUCTURES`), or that test fails.
- **Stored decisions are pinned.** `backend/tests/diagram_decisions.json` pins whether each stored question gets a picture; after reviewing a
  change run `python tests/test_diagrams_dataset_pin.py --update`.

## Running the tests
- **Question service** (fast, no numpy needed): `cd question-service && python -m pytest tests -q`. 14 tests need torch and one needs
  `COMPILEX_TEST_PG_URL` (a PostgreSQL URL; CI provides one).
- **Backend** needs numpy and matplotlib. On the owner's Windows machine Application Control blocks numpy, so run the backend in a container:
  build a test image from `backend/requirements.txt` plus `pytest pytest-asyncio`, then
  `docker run --rm --network none --cap-drop ALL --security-opt no-new-privileges --user 1000:1000 -e PYTHONDONTWRITEBYTECODE=1 -e HOME=/tmp
  -e MPLCONFIGDIR=/tmp/mpl -v "<repo>:/w:ro" -w /w/backend <image> python -m pytest tests/<file>.py -q -p no:cacheprovider`
  (set `MSYS_NO_PATHCONV=1` in Git Bash). The C-compile tests in `test_pool_starters.py` need `gcc` or the Docker image `gcc:14`.
- **Shared-state tests** (`test_shared_state.py`, `test_lobby_manager.py`, `test_rate_limit.py`, `test_execution_gate.py`) run every scenario against an in-process stand-in and, when
  `COMPILEX_TEST_REDIS_URL` is set, against a real Redis (its URL must end in `/15`: the tests empty that database). Locally: start `redis:7-alpine` on an
  `--internal` Docker network (run it as `--user 999:999`, not with all capabilities dropped, or its entrypoint exits), put the test container on the same
  network and set the URL. `tests/two_process_check.py` is a script (it starts two servers): `REDIS_URL=redis://host:6379/14 python tests/two_process_check.py`.
- Run `test_phase1_wiring.py` after touching `routes.py` or `main.py`: it imports them and checks every module for undefined names.
- Four files, `test_api.py`, `test_ai_generation.py`, `test_execution.py`, `test_websocket.py`, and `run_all.py`, are live smoke scripts that need
  the servers on ports 8000 and 8001; run them as scripts, and exclude them from pytest.
- Goal is zero skipped tests. When one skips, say why and how to make it run.

## Where things are
- Question serving: `question-service/main_dynamic.py` (order: reviewed bank, templates, collected banks), `pool/` (database pool and per-player
  history), `model/quality.py` (what is left out and why), `model/legacy_typing.py` and `scaffold.py` (typed starters, five languages).
- Backend question path: `backend/app/api/v1/routes.py` (`/questions/generate`), `services/ai_generator.py`, `question_history.py`,
  `hidden_tests.py` (hidden tests stay on the server), `code_executor.py`, `execution_gate.py` (per-player and total limit on code runs; every call to the executor in `routes.py` must sit inside
  `async with execution_slot(...)`, and a test enforces it), `websocket_handler.py`, `lobby_manager.py` (kept in Redis when `REDIS_URL` is set, see `shared_state.py`).
- Scaling work is planned in `docs/scaling-plan.md`; tick tasks there as they land.
