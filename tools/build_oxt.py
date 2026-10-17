# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Package src/ into dist/PresentationPaceTracker-<version>.oxt.

The version is set in one place only: the VERSION file in the repository
root. The build writes it into src/description.xml and uses it in the name
of the package.

Usage:  python tools/build_oxt.py
"""
import os
import re
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
DIST = os.path.join(ROOT, "dist")
VERSION_FILE = os.path.join(ROOT, "VERSION")
DESCRIPTION = os.path.join(SRC, "description.xml")

# files that are not part of the package
EXCLUDE_EXT = (".svg", ".pyc")

VERSION_RE = re.compile(r'(<version value=")([^"]*)("\s*/>)')


def version():
    with open(VERSION_FILE, encoding="utf-8") as f:
        value = f.read().strip()
    if not re.fullmatch(r"\d+(\.\d+){0,3}", value):
        raise SystemExit("VERSION must look like 1.2.3, not %r" % value)
    return value


def sync_description(value):
    """Write the version into src/description.xml (only if it differs)."""
    with open(DESCRIPTION, encoding="utf-8", newline="") as f:
        text = f.read()
    match = VERSION_RE.search(text)
    if match is None:
        raise SystemExit('src/description.xml has no <version value="..."/>')
    if match.group(2) != value:
        with open(DESCRIPTION, "w", encoding="utf-8", newline="") as f:
            f.write(VERSION_RE.sub(r"\g<1>%s\g<3>" % value, text, count=1))
        print("description.xml: version %s -> %s" % (match.group(2), value))


def main():
    value = version()
    sync_description(value)
    os.makedirs(DIST, exist_ok=True)
    out = os.path.join(DIST, "PresentationPaceTracker-%s.oxt" % value)
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
