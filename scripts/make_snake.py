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

COLS, ROWS = 48, 9
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

# 9x9 badge on the right, symmetric on both axes
LOGO = [
    "..#####..",
    ".#######.",
    "##.....##",
    "#.......#",
    "#.##.##.#",
    "#.......#",
    "##.....##",
    ".#######.",
    "..#####..",
]
LOGO_COL, LOGO_ROW = 39, 0

# --------------------------------------------------------------------------- #
# animation timing (seconds)
# --------------------------------------------------------------------------- #

STEP = 0.018        # how long the snake spends on one cell
HOLD = 3.2          # whole word stays lit this long after the snake finishes
FADE = 1.0          # everything fades out over this long
SNAKE_LEN = 4       # head + 3 body segments


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


def fmt(v: float) -> str:
    """Trim float noise out of the attribute soup."""
    return f"{v:.5f}".rstrip("0").rstrip(".") or "0"


def build(theme: str) -> str:
    bg, empty, lit, body_col, head_col = THEMES[theme]

    art = art_cells()
    path = serpentine()

    travel = len(path) * STEP
    total = travel + HOLD + FADE
    f_hold_end = (travel + HOLD) / total

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
        t_on = step * STEP
        f1 = t_on / total
        f2 = min((t_on + 0.06) / total, f_hold_end)
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
    # Each segment walks the same path, just a few steps behind the head.
    # Linear interpolation between adjacent cells is what makes it glide
    # instead of teleporting from square to square.
    f_travel = travel / total
    key_times = ";".join(
        fmt(i / (len(path) - 1) * f_travel) for i in range(len(path))
    )
    key_times += ";1"

    out.append("<g>")
    for seg in range(SNAKE_LEN):
        lag = seg
        pts = [path[0]] * lag + path[: len(path) - lag]
        xs = ";".join(str(px(c, r)[0]) for c, r in pts) + f";{px(*pts[-1])[0]}"
        ys = ";".join(str(px(c, r)[1]) for c, r in pts) + f";{px(*pts[-1])[1]}"

        colour = head_col if seg == 0 else body_col
        # tail segments shrink and dim a little
        opacity = 1.0 if seg == 0 else 0.85 - 0.18 * (seg - 1)

        out.append(
            f'<rect width="{CELL}" height="{CELL}" rx="{RADIUS}" '
            f'fill="{colour}" opacity="0">'
            f'<animate attributeName="x" values="{xs}" keyTimes="{key_times}" '
            f'dur="{fmt(total)}s" repeatCount="indefinite"/>'
            f'<animate attributeName="y" values="{ys}" keyTimes="{key_times}" '
            f'dur="{fmt(total)}s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" '
            f'values="0;{fmt(opacity)};{fmt(opacity)};0;0" '
            f'keyTimes="0;0.01;{fmt(f_travel)};{fmt(min(f_travel + 0.02, 1.0))};1" '
            f'dur="{fmt(total)}s" repeatCount="indefinite"/>'
            f"</rect>"
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
