# CompileX Roadmap

Status baseline (2026-07-29): full stack verified working locally on Python 3.10.11 (venv at `.venv`). Deployed on Vercel + Render free tier. Analysis found 4 leaked API keys, no CI, SQLite in prod, dead files, dependency drift.

---

## Phase 0 — Security & Hygiene (do immediately, ~1 day)

- [ ] **Rotate all 4 NVIDIA API keys** at build.nvidia.com — 3 were in the (now deleted) `test_keys.py`, 1 is still a hardcoded fallback in `backend/app/services/nvidia_image_service.py:8`. **They remain in git history, so deletion is not enough.**
- [ ] Remove the hardcoded fallback key from `nvidia_image_service.py` (env var only, fail loudly if missing).
- [ ] **Code execution escapes the sandbox when Docker is absent**: `backend/app/services/code_executor.py:443` silently falls back to `_execute_with_subprocess`, running untrusted user code directly on the host. Verified locally — code ran with the Docker daemon stopped. Must hard-fail instead of falling back before any public deployment.
- [x] Delete `test_keys.py` (keys still need rotating).
- [x] Delete dead one-off scripts: `replace.js`, `replace_violet.js`, `update_game.py`, `update_practice.py`.
- [x] Replace `start_fresh.bat` (referenced a missing `clear_database.py`) with `scripts/reset-db.bat` + `backend/reset_db.py`.
- [x] Pin Python in bat files: launcher now uses the repo `.venv` explicitly instead of bare `python` (PATH resolves to 3.14 → breaks pinned deps).
- [x] Fix latent bug: missing `List` import in `question-service/model/generator.py`. It killed the trained-generator path at runtime and broke CI test collection. Fixed along with two torch guards that contradicted the module's own "works without torch" comment (`generator.py` calling `torch.cuda.is_available()` unconditionally in `__init__`; `debugger_generator.py` using `@torch.no_grad()` as a class-body decorator).
- [x] Set `PYTHONUTF8=1` in the startup scripts (question service 500s on `/generate` without it — cp1252 vs '✓' prints).

## Phase 1 — Stability (week 1–2)

- [x] Delete the root `requirements.txt` (duplicated per-service files, pulled unused torch ~2GB).
- [ ] Decide whether torch stays. The deployed entrypoint (`main_dynamic.py`) never imports it, so the Dockerfile's ~2GB install is dead weight for production — but the legacy `main.py`, the debugger model, and 22 of the tests do need it, and CI installs the CPU wheel for that reason. Dropping torch means retiring `main.py` and its torch-dependent tests too; keeping it means the image stays large. Pick one rather than leaving it ambiguous.
- [ ] Remove unused Redis/Celery deps from `backend/requirements.txt` (or actually wire them up).
- [ ] Migrate SQLite → Supabase Postgres (already scaffolded in `.env.example`). Render's ephemeral disk loses SQLite data on every redeploy.
- [x] CI: GitHub Actions — import-boot smoke test for both services + frontend build + question-service pytest.
- [ ] Add ruff lint to CI.
- [ ] Convert `backend/tests` smoke scripts to real pytest with `TestClient` (no live server needed).
- [x] Repo restructure: `backend/`, `frontend/`, `question-service/`, `scripts/`, `docs/`.
- [ ] Move the 82MB of datasets + `model.pt` out of git (LFS or release asset).
- [x] Honest README: correct Python version (3.10+), accurate structure and paths.
- [ ] Remove remaining unverified perf claims from README ("100+ concurrent users", "Self-learning AI").

## Phase 2 — Product Readiness (month 1)

- [ ] Rate-limit code execution & question generation per user (currently open).
- [ ] Structured logging + error tracking (Sentry free tier) on both services.
- [ ] Redis Socket.IO adapter (deps already listed) → horizontal scaling; or explicitly single-instance and drop the deps.
- [ ] Post-match AI explanations (NVIDIA NIM already wired) — high-value, low-effort retention feature.
- [ ] Daily challenge + streaks; surface existing ELO as visible ranked ladder.
- [ ] Spectator mode / shareable match-result links (organic growth loop).

## Phase 3 — Business (month 2+)

Primary wedge: **"never-repeating questions" kills LeetCode memorization** — sell that.

- [ ] **B2B pilot: colleges & bootcamps** — private classrooms, instructor dashboards, assignment mode. Most realistic first paying customer.
- [ ] **Recruiter/screening mode** — companies run timed battles, export candidate reports; question uniqueness = no leaked answers (real pain point, real budgets).
- [ ] Premium tier: unlimited AI feedback, analytics dashboards, private tournaments.
- [ ] Campus ambassador tournaments for growth; seasonal ranked ladders for retention.
- [ ] Infra upgrade off free tiers once first paying users exist (Render paid / Fly.io; managed Postgres).

## Deferred / open questions

- Trained transformer model (`model.pt`): the template+dataset system outperforms it in practice — decide whether to invest in it or delete it and simplify.
- Orphan demo frontend `AI/coding-question-ai/frontend`: archive or delete.
- Multi-language execution images (gcc/java/node) — verify all four actually work under the Docker executor before advertising them.
