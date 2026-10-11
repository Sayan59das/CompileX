"""The single, hand-written Manim scene that renders any lesson plan.

The LLM never writes animation code. It only produces `lesson_plan.json`,
which this scene interprets using the vetted layout primitives in layout.py.

Two invariants keep the frame clean:
  1. Every section clears the stage before the next one starts.
  2. Every body mobject is fitted into the content band before it is shown.
"""

import json
import os

from manim import (
    BOLD,
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Create,
    FadeIn,
    FadeOut,
    LaggedStart,
    Line,
    SurroundingRectangle,
    Transform,
    VGroup,
    Write,
)
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService

from layout import (
    bullet_rows,
    code_block,
    column,
    diagram,
    header,
    panel,
    para,
    place,
    place_top,
    split,
)
from theme import (
    ACCENT,
    ACCENT_2,
    ACCENT_3,
    ACCENT_4,
    BG,
    CONTENT_BOTTOM,
    DIM,
    MUTED,
    PROGRESS_HALF_W,
    PROGRESS_Y,
    SIZE_CODE,
    SIZE_SMALL,
    SIZE_SUB,
    SIZE_TITLE,
    TRACK,
    WRAP_FULL,
    WRAP_HALF,
)

PLAN_PATH = os.environ.get("LESSON_PLAN", "lesson_plan.json")


class CompilotsScene(VoiceoverScene):
    def construct(self):
        self.camera.background_color = BG
        self.set_speech_service(GTTSService(lang="en", tld="com"))

        with open(PLAN_PATH, "r", encoding="utf-8") as fh:
            plan = json.load(fh)

        sections = plan.get("sections", [])
        self._build_chrome()

        handlers = {
            "title": self.sec_title,
            "bullets": self.sec_bullets,
            "summary": self.sec_summary,
            "analogy": self.sec_analogy,
            "diagram": self.sec_diagram,
            "code": self.sec_code,
            "compare": self.sec_compare,
        }

        for index, section in enumerate(sections):
            kind = section.get("type", "bullets")
            self._set_progress((index + 1) / max(len(sections), 1))

            if kind != "title":
                self.play(FadeIn(header(section.get("heading", "")), shift=DOWN * 0.2), run_time=0.6)

            try:
                handlers.get(kind, self.sec_bullets)(section)
            except Exception as exc:  # one bad section must not kill the render
                print(f"[scene] section {index} ({kind}) failed: {exc}")

            self._clear(keep=[self.chrome])

        self._outro(plan)

    # --- narration helper --------------------------------------------------
    def narrate(self, text, anims=None, run_time=1.0):
        """Speak `text`; play `anims` under it. Remaining audio is auto-padded
        by manim-voiceover, so animations keep their natural pacing."""
        speech = " ".join(str(text or "").split())
        if not speech:
            speech = "Let us continue."
        with self.voiceover(text=speech) as tracker:
            if anims:
                self.play(*anims, run_time=max(0.4, min(run_time, tracker.duration)))

    # --- chrome ------------------------------------------------------------
    def _build_chrome(self):
        track = Line(
            LEFT * PROGRESS_HALF_W, RIGHT * PROGRESS_HALF_W,
            stroke_width=4, color=TRACK,
        ).move_to([0, PROGRESS_Y, 0])
        self.progress = Line(
            LEFT * PROGRESS_HALF_W, LEFT * PROGRESS_HALF_W,
            stroke_width=4, color=ACCENT,
        ).move_to([-PROGRESS_HALF_W, PROGRESS_Y, 0])
        self.chrome = VGroup(track, self.progress)
        self.add(self.chrome)

    def _set_progress(self, frac):
        frac = max(0.02, min(1.0, frac))
        end = -PROGRESS_HALF_W + 2 * PROGRESS_HALF_W * frac
        self.progress.put_start_and_end_on(
            [-PROGRESS_HALF_W, PROGRESS_Y, 0], [end, PROGRESS_Y, 0]
        )

    def _clear(self, keep):
        keep_ids = {id(m) for m in keep}
        doomed = [m for m in self.mobjects if id(m) not in keep_ids]
        if doomed:
            self.play(*[FadeOut(m) for m in doomed], run_time=0.45)

    # --- section renderers -------------------------------------------------
    def sec_title(self, s):
        title = para(s.get("heading", ""), width=26, size=SIZE_TITLE, weight=BOLD)
        sub = para(s.get("subtitle", ""), width=44, size=SIZE_SUB, color=ACCENT)
        group = VGroup(title, sub).arrange(DOWN, buff=0.5)
        place(group)
        self.narrate(
            s.get("narration"),
            [FadeIn(title, shift=UP * 0.35), FadeIn(sub, shift=UP * 0.2)],
            run_time=1.4,
        )

    def _reveal_points(self, s, width=WRAP_FULL):
        """Show the whole list dimmed, then light each item as it is narrated.

        Revealing rows one at a time left the stage empty during the section
        intro; dimming shows the shape of the argument up front instead.
        """
        points = s.get("points", [])
        rows = bullet_rows([p.get("text", "") for p in points], width=width)
        if not len(rows):
            return
        place_top(rows)
        rows.set_opacity(DIM)
        self.narrate(s.get("narration"), [FadeIn(rows)], 0.8)
        for row, point in zip(rows, points):
            self.narrate(point.get("narration"), [row.animate.set_opacity(1.0)], 0.5)

    def sec_bullets(self, s):
        self._reveal_points(s)

    def sec_summary(self, s):
        self._reveal_points(s)
        badge = para("You now understand this topic.", width=40, size=SIZE_SMALL, color=ACCENT_4)
        badge.move_to([0, CONTENT_BOTTOM + 0.3, 0])
        self.play(FadeIn(badge), run_time=0.5)

    def sec_analogy(self, s):
        art, _ = diagram(s.get("shape", "stack"), s.get("items", []))
        points = s.get("points", [])
        rows = bullet_rows([p.get("text", "") for p in points], width=WRAP_HALF, size=SIZE_SMALL)
        split(art, rows)
        rows.set_opacity(DIM)
        self.narrate(s.get("narration"), [FadeIn(art, shift=UP * 0.2), FadeIn(rows)], 1.0)
        for row, point in zip(rows, points):
            self.narrate(point.get("narration"), [row.animate.set_opacity(1.0)], 0.5)

    def sec_diagram(self, s):
        art, node_list = diagram(s.get("shape", "flow"), s.get("items", []))
        place(art)
        self.narrate(s.get("narration"), [FadeIn(art, shift=UP * 0.2)], 1.0)

        focus = None
        for beat in s.get("beats", []):
            idx = beat.get("highlight")
            anims = []
            if isinstance(idx, int) and 0 <= idx < len(node_list):
                box = SurroundingRectangle(node_list[idx], color=ACCENT_3, buff=0.1, stroke_width=4)
                if focus is None:
                    focus = box
                    anims = [Create(focus)]
                else:
                    anims = [Transform(focus, box)]
            self.narrate(beat.get("narration"), anims, 0.55)

    def sec_code(self, s):
        code = code_block(s.get("lines", []), SIZE_CODE)
        if not len(code):
            return
        card = panel(code, pad_x=0.6, pad_y=0.45)
        place(card)

        # Type the listing out under the intro narration rather than in silence.
        self.narrate(
            s.get("narration"),
            [FadeIn(card[0]), LaggedStart(*[Write(l) for l in code], lag_ratio=0.5)],
            0.34 * len(code) + 0.9,
        )

        focus = None
        for beat in s.get("walkthrough", []):
            idxs = [i for i in beat.get("lines", []) if isinstance(i, int) and 0 <= i < len(code)]
            anims = []
            if idxs:
                target = VGroup(*[code[i] for i in idxs])
                box = SurroundingRectangle(target, color=ACCENT_3, buff=0.09, stroke_width=3)
                if focus is None:
                    focus = box
                    anims = [Create(focus)]
                else:
                    anims = [Transform(focus, box)]
            self.narrate(beat.get("narration"), anims, 0.5)

    def sec_compare(self, s):
        left = panel(column(s.get("left_title", "Option A"), s.get("left_points", []), 26, ACCENT))
        right = panel(column(s.get("right_title", "Option B"), s.get("right_points", []), 26, ACCENT_2))
        pair = VGroup(left, right).arrange(RIGHT, buff=0.55)
        place(pair)
        self.narrate(s.get("narration"), [FadeIn(left, shift=LEFT * 0.2), FadeIn(right, shift=RIGHT * 0.2)], 1.0)

    # --- outro -------------------------------------------------------------
    def _outro(self, plan):
        end = para(plan.get("title", "Thanks for watching"), width=30, size=SIZE_TITLE, weight=BOLD)
        tag = para("Generated with Manim + Claude", width=44, size=SIZE_SMALL, color=MUTED)
        group = VGroup(end, tag).arrange(DOWN, buff=0.45)
        place(group)
        self.play(FadeIn(group, shift=UP * 0.25), run_time=1.0)
        self.wait(1.6)
        self.play(FadeOut(group), FadeOut(self.chrome), run_time=0.8)
