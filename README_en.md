# Presentation Pace Tracker

English | [日本語](README.md)

A LibreOffice Impress extension that shows a progress band at the bottom of the running slide show. A **turtle** moves with the **elapsed time** and a **rabbit** moves with the **slide progress**, from a start flag to a goal flag, so you can see at a glance whether you will finish on time.

![Progress band](docs/images/screenshot_overlay.png)

## Features

1. Set the planned duration (minutes and seconds) in the settings dialog
2. **Start** in the dialog starts measuring the elapsed time and the slide progress (optionally also starts the slide show)
3. A progress band is shown at the bottom of the slide show
   - Start flag on the left, goal flag on the right
   - The time icon and the slide icon move horizontally from the start to the goal
   - Going back to an earlier slide moves the slide icon back to the left; the time icon keeps moving forward
   - The color of the line shows the pace (green = on time, orange = slightly behind, red = behind)
   - The display area (position X/Y, width, height) can be set in % of the screen. The values are saved and kept after Reset
4. **Reset** in the dialog resets the elapsed time and the slide progress
5. The time and slide icons can be replaced by uploading images in the dialog (defaults: turtle = time, rabbit = slides)
6. The dialog language can be switched between Auto / 日本語 (Japanese) / English (the choice is saved)

## Documentation

| Topic | English | 日本語 |
|---|---|---|
| Installation and usage | [INSTALL_en.md](docs/INSTALL_en.md) | [INSTALL_ja.md](docs/INSTALL_ja.md) |
| Publishing on extensions.libreoffice.org | [PUBLISH_en.md](docs/PUBLISH_en.md) | [PUBLISH_ja.md](docs/PUBLISH_ja.md) |

## Folder layout

```
src/                 contents of the extension (packed into the .oxt as is)
  pacetracker.py     the extension (Python UNO component)
  Addons.xcu         menu and toolbar
  description.xml    ID, version, etc.
  icons/             icons (.svg files are sources and are not packed)
tools/
  build_oxt.py       builds dist/*.oxt from src/
  gen_icons.py       generates the SVG icons
  render_icons.py    renders the SVG icons to PNG with LibreOffice
dist/                built .oxt
docs/                guides and screenshots
```

## Build

```
python tools/build_oxt.py
```

## License

[Mozilla Public License 2.0](LICENSE) (MPL-2.0), the same license as LibreOffice.

This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0. If a copy of the MPL was not distributed with this file, You can obtain one at https://mozilla.org/MPL/2.0/.
