# The question pool (serving side)

A player picks a topic and a difficulty and gets a question in milliseconds. Nothing is generated on the click: questions are made
offline, reviewed by a person, stored in a database, and this package only *chooses* one. It never calls a model, a verifier or a
generator, and it imports no torch (a test checks both).

## What is in here

| File | Job |
|---|---|
| `schema.py` | The tables: `questions`, `pool_index` (the only table a pick reads), `approvals`. One definition for SQLite and PostgreSQL. |
| `repository.py` | Every database call, behind `PoolRepository`. Enforces: pending -> approved -> live only through a recorded approval, one problem shape per topic and difficulty for ever, unique titles. |
| `history.py` | Which questions a player has been given: Redis (`seen:{player}:{topic}:{difficulty}` + a sorted set of times), or in memory. |
| `service.py` | The choice, the fallbacks, grading and status. No web framework. |
| `api.py` | The HTTP routes. |

## Configuration (environment variables of the service)

| Variable | Meaning | Default |
|---|---|---|
| `POOL_DATABASE_URL` | `postgresql://user:pass@host/db`, or a SQLite file path | `data/pool.db` if that file exists, otherwise an empty in-memory pool (the reviewed bank and the older generators still serve) |
| `REDIS_URL` | e.g. `redis://localhost:6379/0` | none: history lives in the process only |
| `SEEN_TTL_SECONDS` | how long a player's history is kept (renewed on every question) | 30 days |
| `INTERNAL_TOKEN` | secret for `/internal/...`; unset switches those routes off | unset |

`docker-compose.yml` already defines PostgreSQL 15 and Redis 7. Start them with `docker compose up -d db redis`, then
`POOL_DATABASE_URL=postgresql://... REDIS_URL=redis://localhost:6379/0 uvicorn main_dynamic:app`.

## Routes

* `GET /api/question?topic=arrays&difficulty=easy&player_id=7` (repeat `player_id` or comma-separate for a lobby). Returns the problem,
  starter code (python, cpp, java, javascript) and the sample test, never the hidden tests. `404` if there is nothing at all.
* `GET /api/question/prefetch?...` the same, for fetching the next question in the background; it counts as served.
* `GET /api/pool/status` sizes per topic and difficulty (pending / approved / live / retired / reviewed bank), counted from the database.
* `POST /api/submit {"question_id": "12", "results": ["...stdout of test 1...", ...]}` grades the outputs a program produced against the
  hidden tests and answers `{passed, total, failed, all_passed}`. It does not run code: the backend's executor does, and asks
  `GET /internal/questions/{id}/tests` (header `X-Internal-Token`) for the inputs and expected outputs.
* `POST /generate` (the game backend's existing route) asks the pool first, then the older banks. The old transformer is retired.

## How a question is chosen

1. Draw as many random live questions as the player has already seen, plus 4 (`ORDER BY RANDOM() LIMIT n` on `pool_index`): at least one is
   unseen whenever any unseen question exists, and the read never grows with the pool.
2. Otherwise an unseen question from the reviewed bank for that topic and difficulty.
3. Otherwise, only for a topic with no pool or bank questions at all, the older generators.
4. Otherwise the question the lobby was given longest ago, flagged `"repeat": true`.

## Starter code: the player writes the logic, the harness is locked

Every question served carries `starter_code` for python, cpp, java, javascript and c: a function that takes the parsed input as
**arguments**, followed by a harness that reads stdin, calls the function and prints what it returns. The shape is the same in every
language, because the editor locks against it (`frontend/src/utils/protectedRegion.js`):

```
<imports>
<function signature line>                 locked  (the arguments the harness passes in)
    // Write your logic here              the player's part: the body, plus helpers and imports above the marker
<end of the function>

// ===== Reads the input and prints the answer. You do not need to edit below. =====      locked from here to the end
<reader, the call with the parsed arguments, the printing of the result>
```

* The marker text lives in `model/scaffold.py` (`MARKER_TEXT`) and in the editor helper; change both together.
* C has no vectors or strings, so an array arrives as `(arr, arr_len)`, a grid as `(grid, grid_cols, grid_len)`, and a list result
  is written into the `result` buffer the harness provides while the function returns how many values it wrote.
* Reviewed questions were built before C existed; `model.scaffold.with_c_starter` adds the C entry from the question's own schema
  when it is served. The other four languages are returned exactly as stored.
* Questions from the older banks have no declared input structure. `model/legacy_typing.py` reads one from their stored tests and
  serves the question only when that structure parses **every** stored input (and the sample), every list is as long as its count says,
  every number fits 64 bits, and the stored outputs fit one type. Anything else is skipped (`[API] Skipped ... no verified starter code`),
  so a player is never locked into a reader that cannot read the question's own tests.
* The lock lives in the player's browser. For graded play the backend should re-attach its own harness to what the player submits.

## Tests

```
cd question-service
pip install -r requirements.txt pytest httpx
pytest tests -q
```

To run the database tests against PostgreSQL as well: `COMPILEX_TEST_PG_URL=postgresql://... pytest tests/test_pool_repository.py -q`
(that test empties the three tables).

## Scaling later

There is one database and one Redis, on purpose. Everything goes through `PoolRepository` and `SeenStore`, so sharding the player history
by player id means a `SeenStore` that picks a Redis per player, with no change to the API. The trigger: p95 of the history lookup staying
above the 50 ms target under a load test. Until then, do not shard.
