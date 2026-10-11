"""Visual design tokens for the video engine.

Every layout constant lives here so the whole video reads as one system.
Coordinates are Manim scene units on a 16:9 frame (14.222 x 8.0).
"""

import numpy as np

# --- Canvas geometry -------------------------------------------------------
FRAME_W = 14.222222
FRAME_H = 8.0
MARGIN = 0.55

# Horizontal bands. Nothing is ever drawn outside CONTENT_TOP/CONTENT_BOTTOM,
# which is what guarantees the heading and the body can never collide.
TITLE_Y = 3.12
CONTENT_TOP = 2.25
CONTENT_BOTTOM = -3.35

CONTENT_W = FRAME_W - 2 * MARGIN
CONTENT_H = CONTENT_TOP - CONTENT_BOTTOM
CONTENT_CENTER = np.array([0.0, (CONTENT_TOP + CONTENT_BOTTOM) / 2.0, 0.0])

PROGRESS_Y = -3.72
PROGRESS_HALF_W = 6.4

# --- Palette ---------------------------------------------------------------
BG = "#0E1116"
FG = "#E9EEF5"
MUTED = "#94A3B8"

ACCENT = "#4CC9F0"     # cyan   - primary
ACCENT_2 = "#F72585"   # magenta- contrast / "wrong"
ACCENT_3 = "#FFD166"   # amber  - highlight / focus
ACCENT_4 = "#06D6A0"   # green  - success / "right"
ACCENT_5 = "#B892FF"   # violet

# Categorical series for multi-element diagrams.
SERIES = [ACCENT, ACCENT_4, ACCENT_3, ACCENT_5, ACCENT_2]

PANEL_FILL = "#161C26"
PANEL_STROKE = "#2A3547"
NODE_FILL = "#1B2230"
TRACK = "#232B39"

# --- Typography ------------------------------------------------------------
FONT = "Segoe UI"
MONO = "Consolas"

SIZE_TITLE = 56
SIZE_SUB = 30
SIZE_HEAD = 38
SIZE_BODY = 28
SIZE_SMALL = 23
SIZE_CODE = 25

# --- syntax highlighting ---------------------------------------------------
CODE_KW = "#FF7B9C"    # keywords
CODE_FN = "#4CC9F0"    # function names
CODE_STR = "#9EE493"   # string literals
CODE_NUM = "#FFD166"   # numbers
CODE_COM = "#6B7A90"   # comments

DIM = 0.18             # resting opacity for not-yet-narrated content

# Conservative wrap widths (characters). `fit()` scales down if these
# still overflow, so they only need to be in the right neighbourhood.
WRAP_FULL = 58
WRAP_HALF = 30
WRAP_HEAD = 46
