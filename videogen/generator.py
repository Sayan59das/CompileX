"""Local video engine: a coding topic in, a narrated explainer video out.

    python generator.py "binary search"

Pipeline:
    topic -> Claude designs the lesson      (JSON, schema-enforced, runtime-gated)
          -> plans/<topic>.json
          -> Claude writes the Manim scene  (built on layout.py, statically checked)
          -> scenes_generated/<topic>.py
          -> manim renders it

Everything is keyed on a slug of the topic, so plans, scenes and videos for
different topics sit side by side instead of overwriting each other.

Re-render without re-querying the model:
    python generator.py "binary search" --reuse-plan --reuse-scene
"""

import argparse
import json
import os
import re
import subprocess
import sys

from lesson_plan import MAX_SECONDS, MIN_SECONDS, build, estimate_seconds
from llm import MODEL, ClaudeUnavailable, require_key
from scene_writer import class_name, write_scene

HERE = os.path.dirname(os.path.abspath(__file__))
PLAN_DIR = "plans"
SCENE_DIR = "scenes_generated"
QUALITY = {"l": "-ql", "m": "-qm", "h": "-qh", "k": "-qk"}


def slugify(topic):
    slug = re.sub(r"[^a-z0-9]+", "-", str(topic).lower()).strip("-")
    return slug or "lesson"


def parse_args():
    p = argparse.ArgumentParser(
        description="Generate a narrated explainer video for a coding topic."
    )
    p.add_argument("topic", help="the coding topic to explain, e.g. \"hash maps\"")
    p.add_argument("--model", default=MODEL, help=f"Claude model (default: {MODEL})")
    p.add_argument("--minutes", type=float, default=5.0,
                   help=f"target runtime in minutes, "
                        f"{MIN_SECONDS / 60:.0f}-{MAX_SECONDS / 60:.0f} (default: 5)")
    p.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"],
                   default="high",
                   help="how hard Claude thinks. The scene prompt already carries "
                        "the whole of layout.py, so xhigh tends to spend the entire "
                        "token budget thinking before it writes anything "
                        "(default: high)")
    p.add_argument("--quality", choices=list(QUALITY), default="h",
                   help="l=480p m=720p h=1080p k=4K (default: h)")
    p.add_argument("--fps", type=int, default=30,
                   help="frame rate; render time scales with it. 30 looks identical "
                        "to 60 for this content and takes half as long (default: 30)")
    p.add_argument("--reuse-plan", action="store_true",
                   help="use this topic's saved lesson design instead of designing again")
    p.add_argument("--reuse-scene", action="store_true",
                   help="render this topic's saved scene instead of generating again")
    p.add_argument("--plan-only", action="store_true",
                   help="write the lesson design and stop")
    p.add_argument("--scene-only", action="store_true",
                   help="write the scene code and stop, without rendering")
    p.add_argument("--static-scene", action="store_true",
                   help="render with the built-in scenes.py instead of a generated "
                        "one; requires a legacy plan file")
    p.add_argument("--no-preview", action="store_true",
                   help="do not open the video when done")
    return p.parse_args()


def load_design(args, plan_path):
    """The saved design, or a fresh one from Claude."""
    if args.reuse_plan or args.reuse_scene:
        if os.path.exists(plan_path):
            with open(plan_path, "r", encoding="utf-8") as fh:
                design = json.load(fh)
            print(f"Reusing {plan_path}: {design.get('title')}")
            return design
        if args.reuse_plan:
            sys.exit(f"error: --reuse-plan given but {plan_path} does not exist")

    print(f"Designing a lesson on \"{args.topic}\" with {args.model} ...")
    design = build(args.topic, model=args.model, minutes=args.minutes,
                   effort=args.effort)

    os.makedirs(PLAN_DIR, exist_ok=True)
    with open(plan_path, "w", encoding="utf-8") as fh:
        json.dump(design, fh, indent=2, ensure_ascii=False)
    print(f"Wrote {plan_path}")
    return design


def load_scene(args, design, slug, scene_path):
    """The saved scene module, or a freshly generated and checked one."""
    if args.reuse_scene:
        if not os.path.exists(scene_path):
            sys.exit(f"error: --reuse-scene given but {scene_path} does not exist")
        print(f"Reusing {scene_path}")
        return scene_path, class_name(slug)

    print("Writing the Manim scene ...")
    source, cls = write_scene(design, slug, model=args.model, effort=args.effort)

    os.makedirs(SCENE_DIR, exist_ok=True)
    with open(scene_path, "w", encoding="utf-8") as fh:
        fh.write(source)
    print(f"Wrote {scene_path}")
    return scene_path, cls


def render(args, slug, scene_path, scene_class):
    # `-o <slug>` keeps each topic's video distinct; Manim would otherwise name
    # every output after the scene class and silently overwrite the last one.
    flags = [QUALITY[args.quality], "--fps", str(args.fps), "-o", slug]
    if not args.no_preview:
        flags.append("-p")

    # Generated scenes live in a subdirectory but import layout/theme from the
    # project root, so put the root on the path for the child process.
    env = dict(os.environ)
    env["PYTHONPATH"] = HERE + os.pathsep + env.get("PYTHONPATH", "")

    print("Rendering (first run synthesises gTTS audio, so it is the slow one) ...")
    # `-m manim` uses this interpreter's manim, so it works without activating the venv.
    result = subprocess.run(
        [sys.executable, "-m", "manim", *flags, scene_path, scene_class],
        env=env, cwd=HERE, check=False,
    )
    return result.returncode


def main():
    # Lesson titles and narration come back from a model and routinely contain
    # curly quotes and dashes. The default Windows console codepage cannot encode
    # those, and an UnicodeEncodeError while printing progress would throw away a
    # design that was already paid for.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    args = parse_args()
    slug = slugify(args.topic)
    plan_path = os.path.join(PLAN_DIR, f"{slug}.json")
    scene_path = os.path.join(SCENE_DIR, f"{slug}.py")

    # Check credentials before announcing any work, but only when this run will
    # actually call the API. A fully cached re-render needs no key at all.
    needs_design = not (args.reuse_plan or args.reuse_scene) or not os.path.exists(plan_path)
    needs_scene = not (args.reuse_scene or args.static_scene or args.plan_only)
    if needs_design or needs_scene:
        require_key()

    try:
        design = load_design(args, plan_path)
    except ClaudeUnavailable as exc:
        sys.exit(f"\nerror: {exc}")

    secs = estimate_seconds(design)
    print(f"{design.get('title')} | estimated runtime "
          f"~{int(secs // 60)}m {int(secs % 60)}s")
    if design.get("objective"):
        print(f"objective: {design['objective']}")

    if args.plan_only:
        return

    if args.static_scene:
        # The built-in scene reads the older section-based plan format.
        if "sections" not in design:
            sys.exit("error: --static-scene needs a legacy plan (one with a "
                     "\"sections\" array). This topic's plan is the new "
                     "act-based design; drop the flag to render it.")
        os.environ["LESSON_PLAN"] = plan_path
        sys.exit(render(args, slug, "scenes.py", "CompilotsScene"))

    try:
        scene_path, scene_class = load_scene(args, design, slug, scene_path)
    except ClaudeUnavailable as exc:
        sys.exit(f"\nerror: {exc}")

    if args.scene_only:
        return

    sys.exit(render(args, slug, scene_path, scene_class))


if __name__ == "__main__":
    main()
