# videogen

Give it a coding topic, get back a narrated explainer video that teaches one
concept properly — hook, intuition, mechanism, animated code trace, summary.

```bash
set ANTHROPIC_API_KEY=your_api_key_here
python generator.py "hash tables"
```

## From the web app

The landing page's **Learn More** section is a front end for this CLI. The API
server drives `generator.py` as a child process — it never imports it, because
the backend environment has no manim — and polls the child's progress lines:

```
POST /api/v1/videos/generate   {"topic": "hash tables"}  -> {"slug": ...}
GET  /api/v1/videos/{slug}                               -> status, stage, elapsed
GET  /api/v1/videos/{slug}/file                          -> the mp4
GET  /api/v1/videos                                      -> every rendered topic
```

Videos rendered by hand with the commands below are picked up and served by
those endpoints, and vice versa: both read the same `media/videos/` tree, keyed
on the same slug. To enable it, give the backend `ANTHROPIC_API_KEY` and point
`VIDEOGEN_PYTHON` at an interpreter that has this directory's requirements
installed (see `backend/.env.example`). Without those, the section explains what
is missing and already-rendered topics still play.

## Why it is built this way

The obvious design is to ask a model to write the Manim scene. That was the
first version, and against a local 8B model it failed in a specific way: it
emitted three shapes all placed with `next_to(plate, RIGHT)` (so they rendered
on top of each other) and five code lines that were never arranged (so they
collapsed onto the origin). Layout correctness was being left to a token
predictor.

The current design keeps the model writing scene code — Claude does spatial
reasoning that Llama 3 8B could not — but takes away the blank page. The
generator hands Claude the full source of `layout.py` and `theme.py` and
requires it to compose those primitives, which return mobjects already fitted to
the content band. Then every generated file is put through a static gate before
it goes near the renderer.

| Layer | Owner |
| --- | --- |
| Pedagogy, analogies, narration | Claude (stage 1) |
| Animation choreography | Claude (stage 2), built on `layout.py` |
| Position, spacing, colour, type | `theme.py` / `layout.py`, hand-written |
| Whether any of it ships | the runtime gate and the static gate |

## Pipeline

```
topic
  -> lesson_plan.py     stage 1: Claude designs the lesson as schema-enforced
                        JSON. Regenerated until it passes the runtime gate.
  -> plans/<topic>.json
  -> scene_writer.py    stage 2: Claude writes a VoiceoverScene on top of
                        layout.py. Regenerated until it passes the static gate.
  -> scenes_generated/<topic>.py
  -> media/videos/<topic>/1080p30/<topic>.mp4
```

Both paths are keyed on a slug of the topic (`"hash tables"` -> `hash-tables`),
so topics accumulate side by side. Manim names its output after the scene class
by default, which `-o <slug>` overrides.

## The five acts

The lesson shape is fixed; Claude fills it.

| Act | Must do |
| --- | --- |
| **Hook** | Open with a question or problem — *"How can Google search billions of pages in milliseconds?"* Never a definition. |
| **Intuition** | A real-world analogy (bookshelf, mailboxes, parking lot, supermarket queue, pipes, dominoes). Why before how. |
| **Mechanism** | The core idea, shown visually rather than stated. |
| **Trace** | A real Python example, executed line by line with live state. |
| **Summary** | Intuition, algorithm, complexity, common mistakes, one challenge question. |

Every lesson carries an explicit objective: *"By the end of this lesson you will
understand how hash maps work and know when to use them."*

## The two gates

**Runtime gate** (`lesson_plan.py`). Narration word count is the only reliable
predictor of video length, so the design is measured before anything renders:
2–7 minutes hard, 4–6 target. Outside the window, the design goes back with
specific feedback ("estimated 95 seconds, target 300 — expand the narration").
The same pass rejects a hook that opens with a definition, a missing analogy, a
code snippet that does not parse, and a walkthrough too thin to animate.

**Static gate** (`scene_writer.py`). Every generated scene must pass all of
these or it is regenerated with the failures fed back:

- parses and compiles
- exactly one class, subclassing `VoiceoverScene`
- calls `set_speech_service(GTTSService(...))`
- **every narration block references `tracker.duration`** — audio sync cannot
  silently break
- no `Code` mobject; listings use `markup_code_block()` (MarkupText)
- content positioned through `place` / `place_top` / `split`
- `construct()` under 60 statements, at least three helper methods
- imports restricted to `manim`, `manim_voiceover`, `layout`, `theme`, `numpy`,
  `math`; no `open` / `exec` / `eval`

## Files

- `theme.py` — palette, type scale, frame geometry. All design tokens.
- `layout.py` — overlap-proof primitives: `fit`, `place`, `split`, `panel`,
  `diagram`, `markup_code_block`, and the execution primitives `VarTable`,
  `ArrayRow`, `Pointer`, `StackFrames`.
- `llm.py` — the Claude client, the missing-key message, error translation.
- `lesson_plan.py` — stage 1: schema, prompt, sanitising, runtime gate.
- `scene_writer.py` — stage 2: prompt, static gate, retry loop.
- `scenes.py` — `CompilotsScene`, the hand-written fallback renderer.
- `generator.py` — CLI.
- `plans/` — one saved design per topic. Edit one by hand and re-run with
  `--reuse-plan` to change wording without paying for a new design.

## Animating execution

The trace act is the reason `layout.py` grew execution primitives. Rather than
displaying a listing, generated scenes walk it:

```python
code = markup_code_block(LINES)          # one MarkupText per line, indexable
state = VarTable(["i", "total"])         # live variable panel
arr = ArrayRow([5, 2, 9, 1])             # indexed cells
i = Pointer("i")                         # walks the cells
stack = StackFrames(max_frames=5)        # recursion, push and pop

with self.voiceover(text="...") as tracker:
    self.play(state.set_value("total", 7), run_time=tracker.duration)
```

## Options

```
--model NAME        Claude model (default claude-opus-5)
--minutes N         target runtime, 2..7 (default 5)
--effort LEVEL      low|medium|high|xhigh|max (default xhigh)
--quality l|m|h|k   480p / 720p / 1080p / 4K (default h)
--fps N             frame rate (default 30)
--reuse-plan        skip stage 1, use the saved design
--reuse-scene       skip both stages, render the saved scene
--plan-only         write the design and stop
--scene-only        write the scene code and stop
--static-scene      render with scenes.py (needs a legacy section-based plan)
--no-preview        do not open the player when finished
```

## Keeping cost and render time down

Generation is now the expensive part before Manim even starts — two API calls,
roughly 15–40k output tokens at `xhigh`. The levers:

- **`--reuse-scene`** makes iteration free. Generate once, then re-render.
- **`--effort high`** is meaningfully cheaper than `xhigh` and usually fine for
  a familiar topic; `xhigh` is the documented setting for code generation.
- **The system prompt is prompt-cached.** It contains the whole of `layout.py`
  and `theme.py` and is byte-identical across topics, so renders within the
  cache window read it at a tenth of the price.

Render time then scales with `duration x fps x pixels`:

- **`--fps`** defaults to 30, not Manim's 60 for `-qh`. This content is fades,
  writes and highlights, so 30 is visually indistinguishable and halves the
  frame count.
- **`--quality m`** (720p) is a quarter of the pixels for review passes.
- **Manim's cache is left enabled**, so a re-render only redoes changed sections.
- **gTTS audio is cached** by manim-voiceover, keyed on the narration text.

Fast loop: `--plan-only`, then `--scene-only`, then
`--reuse-plan --reuse-scene --quality m` until it looks right, then one final
`--reuse-plan --reuse-scene --quality h`.

Audio prefetching is deliberately *not* parallelised: manim-voiceover keeps a
single `cache.json`, and concurrent writers can corrupt it.

## Requirements

- `pip install -r requirements.txt`
- `ANTHROPIC_API_KEY` in the environment:
  - cmd.exe: `set ANTHROPIC_API_KEY=your_api_key_here`
  - PowerShell: `$env:ANTHROPIC_API_KEY = "your_api_key_here"`
  - persist it: `setx ANTHROPIC_API_KEY "your_api_key_here"`
- An internet connection for gTTS (voice synthesis)

The key is read from the environment only. It is never hardcoded, never written
to a plan, and never included in generated scene code.

## Known limits

The three plans already in `plans/` predate the act-based design and use the old
13-section format. Render them with `--static-scene`; new topics use the new
pipeline.

The static gate proves a scene is structurally sound, not that it is
*beautiful*. A generated scene can still pace an act badly. `--reuse-plan` and
re-running stage 2 is cheap, and hand-editing `scenes_generated/<topic>.py`
before `--reuse-scene` always wins.
