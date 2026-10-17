# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Package src/ into dist/PresentationPaceTracker-<version>.oxt.

Usage:  python tools/build_oxt.py
"""
import os
import re
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
DIST = os.path.join(ROOT, "dist")

# files that are not part of the package
EXCLUDE_EXT = (".svg", ".pyc")


def version():
    with open(os.path.join(SRC, "description.xml"), encoding="utf-8") as f:
        return re.search(r'<version value="([^"]+)"', f.read()).group(1)


def main():
    os.makedirs(DIST, exist_ok=True)
    out = os.path.join(DIST, "PresentationPaceTracker-%s.oxt" % version())
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for folder, dirs, files in os.walk(SRC):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for name in sorted(files):
                if name.endswith(EXCLUDE_EXT):
                    continue
                path = os.path.join(folder, name)
                arc = os.path.relpath(path, SRC).replace(os.sep, "/")
                z.write(path, arc)
                print("  +", arc)
    print("built", out)


if __name__ == "__main__":
    main()
