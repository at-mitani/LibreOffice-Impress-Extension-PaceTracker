# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Render src/icons/*.svg to PNG files using LibreOffice's graphic filters.

Start LibreOffice listening on a socket first, e.g.
  soffice --headless --accept="socket,host=localhost,port=2099;urp;"
then run with LibreOffice's bundled Python:
  "C:\\Program Files\\LibreOffice\\program\\python.exe" tools/render_icons.py
"""
import os
import re
import sys

import uno
from com.sun.star.beans import PropertyValue

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICONS = os.path.join(ROOT, "src", "icons")

# svg name -> list of (png name, pixel size)
TARGETS = {
    "turtle": [("turtle.png", 256)],
    "rabbit": [("rabbit.png", 256)],
    "start_flag": [("start_flag.png", 256)],
    "goal_flag": [("goal_flag.png", 256)],
    "logo": [("logo.png", 128), ("toolbar_16.png", 16), ("toolbar_26.png", 26)],
}


def props(**kw):
    out = []
    for k, v in kw.items():
        p = PropertyValue()
        p.Name, p.Value = k, v
        out.append(p)
    return tuple(out)


def main(port=2099):
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
    ctx = resolver.resolve("uno:socket,host=localhost,port=%d;urp;StarOffice.ComponentContext" % port)
    gp = ctx.ServiceManager.createInstanceWithContext("com.sun.star.graphic.GraphicProvider", ctx)
    for name, outputs in TARGETS.items():
        with open(os.path.join(ICONS, name + ".svg"), encoding="utf-8") as f:
            src = f.read()
        for png, size in outputs:
            # The SVG import applies the screen scale factor, so adjust the
            # declared size until the stored PNG has the wanted pixel size.
            declared = size
            for _ in range(4):
                actual = render(gp, src, declared, os.path.join(ICONS, png))
                if actual == size:
                    break
                declared = declared * size / actual
            print("rendered %s (%dpx)" % (png, actual))


def render(gp, src, declared, out):
    tmp = os.path.join(ICONS, "_tmp.svg")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(re.sub(r'width="\d+" height="\d+"', 'width="%.3f" height="%.3f"' % (declared, declared),
                       src, count=1))
    graphic = gp.queryGraphic(props(URL=uno.systemPathToFileUrl(tmp)))
    gp.storeGraphic(graphic, props(URL=uno.systemPathToFileUrl(out), MimeType="image/png"))
    os.remove(tmp)
    return gp.queryGraphic(props(URL=uno.systemPathToFileUrl(out))).SizePixel.Width


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2099)
