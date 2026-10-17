# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Generate the SVG icons of the extension into src/icons/.

Usage:  python tools/gen_icons.py
Then render PNG files with tools/render_icons.py (needs LibreOffice).
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "src", "icons")

TURTLE = """
<path d="M30 166 L4 178 L32 184 Z" fill="#8BC34A" stroke="#33691E" stroke-width="5" stroke-linejoin="round"/>
<g fill="#7CB342" stroke="#33691E" stroke-width="5">
  <ellipse cx="62" cy="196" rx="20" ry="26"/>
  <ellipse cx="168" cy="196" rx="20" ry="26"/>
</g>
<ellipse cx="212" cy="140" rx="36" ry="29" fill="#8BC34A" stroke="#33691E" stroke-width="5"/>
<circle cx="224" cy="130" r="7" fill="#212121"/>
<circle cx="226" cy="127" r="2.5" fill="#FFFFFF"/>
<path d="M220 152 q12 7 24 -3" stroke="#33691E" stroke-width="4" fill="none" stroke-linecap="round"/>
<path d="M22 178 C22 98 70 62 118 62 C166 62 206 98 206 178 Z" fill="#43A047" stroke="#1B5E20" stroke-width="6" stroke-linejoin="round"/>
<g fill="none" stroke="#1B5E20" stroke-width="4" stroke-linejoin="round" opacity="0.75">
  <path d="M94 100 L142 100 L162 136 L142 172 L94 172 L74 136 Z"/>
  <path d="M94 100 L82 70 M142 100 L156 70 M162 136 L204 136 M74 136 L24 136"/>
</g>
<rect x="16" y="170" width="198" height="18" rx="9" fill="#9CCC65" stroke="#1B5E20" stroke-width="5"/>
"""

RABBIT = """
<g transform="rotate(-22 166 96)">
  <ellipse cx="166" cy="48" rx="17" ry="50" fill="#FFFFFF" stroke="#757575" stroke-width="5"/>
  <ellipse cx="166" cy="52" rx="7" ry="35" fill="#F8BBD0"/>
</g>
<g transform="rotate(6 196 96)">
  <ellipse cx="196" cy="48" rx="17" ry="50" fill="#FFFFFF" stroke="#757575" stroke-width="5"/>
  <ellipse cx="196" cy="52" rx="7" ry="35" fill="#F8BBD0"/>
</g>
<circle cx="34" cy="158" r="20" fill="#FFFFFF" stroke="#757575" stroke-width="5"/>
<ellipse cx="78" cy="214" rx="42" ry="15" fill="#FFFFFF" stroke="#757575" stroke-width="5"/>
<ellipse cx="108" cy="170" rx="78" ry="54" fill="#FFFFFF" stroke="#757575" stroke-width="5"/>
<ellipse cx="166" cy="218" rx="22" ry="11" fill="#FFFFFF" stroke="#757575" stroke-width="5"/>
<circle cx="186" cy="124" r="45" fill="#FFFFFF" stroke="#757575" stroke-width="5"/>
<circle cx="202" cy="112" r="7.5" fill="#212121"/>
<circle cx="204.5" cy="109" r="2.5" fill="#FFFFFF"/>
<circle cx="204" cy="142" r="9" fill="#F8BBD0" opacity="0.9"/>
<ellipse cx="229" cy="130" rx="6" ry="5" fill="#EC407A"/>
<g stroke="#9E9E9E" stroke-width="3" stroke-linecap="round">
  <path d="M232 138 L252 134 M232 142 L252 146"/>
</g>
"""

POLE = """
<ellipse cx="67" cy="238" rx="38" ry="11" fill="#8D6E63"/>
<rect x="60" y="22" width="14" height="216" rx="7" fill="#6D4C41"/>
<circle cx="67" cy="22" r="11" fill="#FFC107" stroke="#6D4C41" stroke-width="4"/>
"""

WAVE = "M74 34 C120 14 152 54 218 32 L218 124 C152 146 120 106 74 126 Z"

START = POLE + """
<path d="%s" fill="#43A047" stroke="#1B5E20" stroke-width="5" stroke-linejoin="round"/>
<path d="M128 56 L176 80 L128 104 Z" fill="#FFFFFF"/>
""" % WAVE


def _checks():
    cells = []
    for row in range(4):
        for col in range(6):
            if (row + col) % 2 == 0:
                cells.append('<rect x="%d" y="%d" width="25" height="30" fill="#212121"/>'
                             % (74 + col * 24, 14 + row * 34))
    return "\n".join(cells)


GOAL = POLE + """
<defs><clipPath id="wave"><path d="%s"/></clipPath></defs>
<path d="%s" fill="#FFFFFF"/>
<g clip-path="url(#wave)">%s</g>
<path d="%s" fill="none" stroke="#212121" stroke-width="5" stroke-linejoin="round"/>
""" % (WAVE, WAVE, _checks(), WAVE)


def svg(body, size, viewbox="0 0 256 256"):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="%s">\n%s\n</svg>\n'
            % (size, size, viewbox, body))


def place(body, x, y, scale):
    return '<g transform="translate(%g %g) scale(%g)">%s</g>' % (x, y, scale, body)


LOGO = """
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#42A5F5"/><stop offset="1" stop-color="#1565C0"/>
  </linearGradient>
</defs>
<rect x="4" y="4" width="248" height="248" rx="40" fill="url(#bg)"/>
<rect x="24" y="200" width="208" height="8" rx="4" fill="#FFFFFF" opacity="0.9"/>
""" + place(START, 8, 120, 0.36) + place(GOAL, 166, 120, 0.36) \
    + place(RABBIT, 70, 36, 0.52) + place(TURTLE, 44, 136, 0.42)

ICONS = {
    "turtle": TURTLE,
    "rabbit": RABBIT,
    "start_flag": START,
    "goal_flag": GOAL,
    "logo": LOGO,
}


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, body in ICONS.items():
        with open(os.path.join(OUT, name + ".svg"), "w", encoding="utf-8") as f:
            f.write(svg(body, 256))
    print("SVG icons written to", OUT)


if __name__ == "__main__":
    main()
