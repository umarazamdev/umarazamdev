#!/usr/bin/env python3
"""
make_snake.py - build the contribution-grid "snake" banner as an SVG.

Usage
-----
    python scripts/make_snake.py

Writes assets/github-contribution-grid-snake.svg       (light theme)
       assets/github-contribution-grid-snake-dark.svg  (dark theme)

The README swaps the two with <picture> + prefers-color-scheme.

How the animation works
-----------------------
A snake glides across the grid in a serpentine path (row 0 left-to-right,
row 1 right-to-left, and so on). Every cell it crosses that belongs to the
artwork switches on AND STAYS ON, so the word is fully readable for the
back half of the loop. Then everything fades and the loop restarts.

The old hand-edited file flashed each cell for a fraction of a second and
never showed the whole word at once, which is why the letters looked broken
in any screenshot.
"""

from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------- #
# grid geometry  (matches GitHub's own contribution graph metrics)
# --------------------------------------------------------------------------- #

COLS, ROWS = 51, 9
CELL, PITCH, PAD = 11, 14, 5
RADIUS = 2

WIDTH = PAD * 2 + (COLS - 1) * PITCH + CELL
HEIGHT = PAD * 2 + (ROWS - 1) * PITCH + CELL

# --------------------------------------------------------------------------- #
# themes
# --------------------------------------------------------------------------- #

THEMES = {
    # name: (background, empty cell, lit cell, snake body, snake head)
    "light": ("#ffffff", "#ebedf0", "#216e39", "#0969da", "#218bff"),
    "dark": ("#0d1117", "#161b22", "#39d353", "#58a6ff", "#79c0ff"),
}

# --------------------------------------------------------------------------- #
# 5x7 pixel font
#
# Seven rows is what makes G and T actually legible: G needs a row for the
# crossbar that is clearly below the middle, and T needs a full-width cap with
# a stem that does not touch it again further down. The previous 5x5 font had
# no room for either, so G collapsed into a closed ring and T grew a second bar.
# --------------------------------------------------------------------------- #

FONT = {
    "G": [
        ".###.",
        "#...#",
        "#....",
        "#.###",
        "#...#",
        "#...#",
        ".###.",
    ],
    "I": [
        "#####",
        "..#..",
        "..#..",
        "..#..",
        "..#..",
        "..#..",
        "#####",
    ],
    "T": [
        "#####",
        "..#..",
        "..#..",
        "..#..",
        "..#..",
        "..#..",
        "..#..",
    ],
    "H": [
        "#...#",
        "#...#",
        "#...#",
        "#####",
        "#...#",
        "#...#",
        "#...#",
    ],
    "U": [
        "#...#",
        "#...#",
        "#...#",
        "#...#",
        "#...#",
        "#...#",
        ".###.",
    ],
    "B": [
        "####.",
        "#...#",
        "#...#",
        "####.",
        "#...#",
        "#...#",
        "####.",
    ],
}

WORD = "GITHUB"
GLYPH_W, GLYPH_H = 5, 7
LETTER_GAP = 1
TEXT_COL, TEXT_ROW = 1, 1

# Copilot mark on the right: a solid rounded head with two big eyes cut out
# of it. The eyes are the whole identity of that logo, so they get 2 columns
# each with a 3-column bridge between them - 1-wide eyes read as slots, and a
# 1-wide bridge reads as a stray pixel floating in a hole. Drawing the head as
# an outline instead (what this used to be) just reads as a ring, not a face.
LOGO = [
    "..#######..",
    ".#########.",
    "###########",
    "##..###..##",
    "##..###..##",
    "##..###..##",
    "###########",
    ".#########.",
    "..#######..",
]
LOGO_COL, LOGO_ROW = 39, 0

# --------------------------------------------------------------------------- #
# animation timing (seconds)
# --------------------------------------------------------------------------- #

TRAVEL = 7.8        # how long the snake takes to cross the whole grid
HOLD = 3.2          # whole word stays lit this long after the snake finishes
FADE = 1.0          # everything fades out over this long

# The body is drawn as a dashed stroke riding the serpentine path: one dash,
# a gap longer than the path, and an animated stroke-dashoffset. Stacking a
# few of these at decreasing width and increasing length tapers the body from
# a thick neck down to a thin tail, which is what actually reads as a snake.
# (width, length in px) - drawn back to front, so the thick one lands on top.
BODY_LAYERS = [(4, 142), (6, 112), (8, 82), (10, 52), (11.5, 26)]
SNAKE_LEN = max(length for _, length in BODY_LAYERS)
HEAD_R = 6.5


def art_cells() -> set[tuple[int, int]]:
    """Every (col, row) that belongs to the word or the badge."""
    cells: set[tuple[int, int]] = set()

    col = TEXT_COL
    for ch in WORD:
        for r, line in enumerate(FONT[ch]):
            for c, px in enumerate(line):
                if px == "#":
                    cells.add((col + c, TEXT_ROW + r))
        col += GLYPH_W + LETTER_GAP

    for r, line in enumerate(LOGO):
        for c, px in enumerate(line):
            if px == "#":
                cells.add((LOGO_COL + c, LOGO_ROW + r))

    return cells


def serpentine() -> list[tuple[int, int]]:
    """Boustrophedon path over every cell, so the snake never teleports."""
    path = []
    for row in range(ROWS):
        cols = range(COLS) if row % 2 == 0 else range(COLS - 1, -1, -1)
        for col in cols:
            path.append((col, row))
    return path


def px(col: int, row: int) -> tuple[int, int]:
    return PAD + col * PITCH, PAD + row * PITCH


def centre(col: int, row: int) -> tuple[float, float]:
    x, y = px(col, row)
    return x + CELL / 2, y + CELL / 2


def path_d() -> str:
    """The serpentine as one continuous <path>, through cell centres."""
    parts = []
    for row in range(ROWS):
        left, right = centre(0, row)[0], centre(COLS - 1, row)[0]
        y = centre(0, row)[1]
        if row == 0:
            parts.append(f"M{fmt(left)},{fmt(y)}")
            parts.append(f"H{fmt(right)}")
        else:
            parts.append(f"V{fmt(y)}")
            parts.append(f"H{fmt(left if row % 2 else right)}")
    return "".join(parts)


def dist_along(step: int) -> float:
    """Distance along the path to the centre of the step-th cell."""
    row, k = divmod(step, COLS)
    return row * ((COLS - 1) * PITCH + PITCH) + k * PITCH


PATH_LEN = (ROWS - 1) * PITCH + ROWS * (COLS - 1) * PITCH
# The head has to run past the end far enough for the longest tail to clear.
HEAD_RUN = PATH_LEN + SNAKE_LEN


def fmt(v: float) -> str:
    """Trim float noise out of the attribute soup."""
    return f"{v:.5f}".rstrip("0").rstrip(".") or "0"


def build(theme: str) -> str:
    bg, empty, lit, body_col, head_col = THEMES[theme]

    art = art_cells()
    path = serpentine()

    total = TRAVEL + HOLD + FADE
    f_travel = TRAVEL / total
    f_hold_end = (TRAVEL + HOLD) / total

    def reach(step: int) -> float:
        """Global time fraction at which the head arrives at this cell."""
        return dist_along(step) / HEAD_RUN * f_travel

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}" '
        f'role="img" aria-label="{WORD.lower()} contribution snake">',
        f'<rect width="100%" height="100%" rx="6" fill="{bg}"/>',
    ]

    # --- static empty grid ------------------------------------------------- #
    out.append("<g>")
    for row in range(ROWS):
        for col in range(COLS):
            x, y = px(col, row)
            out.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                f'rx="{RADIUS}" fill="{empty}"/>'
            )
    out.append("</g>")

    # --- artwork cells: switch on as the snake passes, then stay on -------- #
    out.append("<g>")
    for step, (col, row) in enumerate(path):
        if (col, row) not in art:
            continue
        x, y = px(col, row)
        f1 = reach(step)
        f2 = min(f1 + 0.005, f_hold_end)
        out.append(
            f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
            f'rx="{RADIUS}" fill="{lit}" opacity="0">'
            f'<animate attributeName="opacity" values="0;0;1;1;0" '
            f'keyTimes="0;{fmt(f1)};{fmt(f2)};{fmt(f_hold_end)};1" '
            f'dur="{fmt(total)}s" repeatCount="indefinite"/>'
            f"</rect>"
        )
    out.append("</g>")

    # --- the snake --------------------------------------------------------- #
    # One dash riding the serpentine path. The gap is longer than the path so
    # only a single dash is ever on screen, and animating stroke-dashoffset
    # slides it from the start to past the end. Round caps give the body its
    # rounded nose and tail; stacking the layers tapers it.
    d = path_d()
    gap = HEAD_RUN + 100
    # snake vanishes the moment it leaves the grid, so the held word is clean
    f_gone = min(f_travel + 0.015, 1.0)
    fade_keys = f"0;0.008;{fmt(f_travel)};{fmt(f_gone)};1"

    # One opacity animation on the wrapper, and every layer fully opaque:
    # per-layer alpha would show a visible step wherever two widths meet.
    out.append(
        f'<g fill="none" stroke-linecap="round" stroke-linejoin="round" opacity="0">'
        f'<animate attributeName="opacity" values="0;1;1;0;0" '
        f'keyTimes="{fade_keys}" dur="{fmt(total)}s" repeatCount="indefinite"/>'
    )
    for width, length in BODY_LAYERS:
        # Every layer's leading edge sits on the head, so they nest into a taper.
        start, end = length, length - HEAD_RUN
        out.append(
            f'<path d="{d}" stroke="{body_col}" stroke-width="{fmt(width)}" '
            f'stroke-dasharray="{fmt(length)} {fmt(gap)}" '
            f'stroke-dashoffset="{fmt(start)}">'
            f'<animate attributeName="stroke-dashoffset" '
            f'values="{fmt(start)};{fmt(end)};{fmt(end)}" '
            f'keyTimes="0;{fmt(f_travel)};1" '
            f'dur="{fmt(total)}s" repeatCount="indefinite"/>'
            f"</path>"
        )

    # Head: rides the same cell centres the dash head passes through, so it
    # stays glued to the front of the body.
    xs, ys, keys = [], [], []
    for step in range(len(path)):
        cx, cy = centre(*path[step])
        xs.append(fmt(cx))
        ys.append(fmt(cy))
        keys.append(fmt(reach(step)))
    xs.append(xs[-1])
    ys.append(ys[-1])
    keys.append("1")

    out.append(
        f'<circle r="{HEAD_R}" fill="{head_col}">'
        f'<animate attributeName="cx" values="{";".join(xs)}" '
        f'keyTimes="{";".join(keys)}" dur="{fmt(total)}s" repeatCount="indefinite"/>'
        f'<animate attributeName="cy" values="{";".join(ys)}" '
        f'keyTimes="{";".join(keys)}" dur="{fmt(total)}s" repeatCount="indefinite"/>'
        f"</circle>"
    )
    out.append("</g>")

    out.append("</svg>")
    return "".join(out)


def main() -> None:
    dest = Path(__file__).resolve().parent.parent / "assets"
    dest.mkdir(parents=True, exist_ok=True)

    for theme, name in (
        ("light", "github-contribution-grid-snake.svg"),
        ("dark", "github-contribution-grid-snake-dark.svg"),
    ):
        svg = build(theme)
        path = dest / name
        path.write_text(svg, encoding="utf-8")
        print(f"wrote {path}  ({len(svg) / 1024:.0f} KB, {theme})")


if __name__ == "__main__":
    main()
