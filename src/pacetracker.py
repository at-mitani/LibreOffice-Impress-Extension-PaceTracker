# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# LibreOffice Impress Pace Tracker
#
# Shows the elapsed presentation time and the slide progress as two icons
# (turtle = time, rabbit = slides by default) that move from a start flag to
# a goal flag along a band at the bottom of the running slide show.
#
# The band has no background of its own. On the slides, the flags, the icons
# and the pace line are each a small frameless floating window owned by the
# slide show window: the slide show never paints over such windows, and the
# slide stays visible between them. On the Presenter Console they share one
# floating window filled with the console's background color. The background
# of the icons is set to the color behind them (the slide background, or the
# background of the Presenter Console).
#
import json
import os
import shutil
import threading
import time
import traceback

import uno
import unohelper
from com.sun.star.awt import XActionListener, XCallback, XItemListener, XTopWindowListener
from com.sun.star.awt import Rectangle, WindowDescriptor
from com.sun.star.awt.PosSize import POS, POSSIZE
from com.sun.star.awt.WindowClass import TOP
from com.sun.star.beans import PropertyValue
from com.sun.star.frame import XTerminateListener
from com.sun.star.task import XJobExecutor

EXTENSION_ID = "jp.atmitani.impress.pacetracker"
IMPL_NAME = EXTENSION_ID + ".PaceTracker"

TICK_SECONDS = 0.25

# Colors of the progress band
WHITE = 0xFFFFFF
PRESENTER_BACKGROUND = 0x404552  # background of the Presenter Console
PACE_OK = 0x2E7D32       # slides are ahead of (or level with) the time
PACE_WARN = 0xEF6C00     # slides are slightly behind the time
PACE_LATE = 0xC62828     # slides are clearly behind, or time is over

TEXTS = {
    "ja": {
        "title": "発表ペーストラッカー",
        "planned": "発表予定時間:",
        "min": "分",
        "sec": "秒",
        "autostart": "開始時にスライドショーも開始する",
        "measure": "計測",
        "elapsed": "経過時間: %s / %s",
        "slide": "スライド: %d / %d",
        "slide_none": "スライド: (スライドショー停止中)",
        "state_idle": "状態: 停止中",
        "state_run": "状態: 計測中",
        "state_over": "状態: 計測中 (予定時間を超過)",
        "no_presenter": " ※発表者コンソールがないため非表示",
        "target": "表示先:",
        "target_slides": "スライド (聴衆も見える)",
        "target_presenter": "発表者コンソールのみ",
        "start": "開始",
        "reset": "リセット",
        "area": "表示領域 (画面に対する %)",
        "area_pos": "開始位置",
        "area_size": "大きさ",
        "area_x": "X:",
        "area_x_note": "% 左端から",
        "area_y": "Y:",
        "area_y_note": "% 下端から",
        "area_y_note_top": "% 上端から",
        "area_w": "幅:",
        "area_w_note": "% 横幅比",
        "area_h": "高さ:",
        "area_h_note": "% 縦幅比",
        "icons": "アイコン",
        "time_icon": "時間アイコン:",
        "slide_icon": "スライドアイコン:",
        "start_icon": "スタートアイコン:",
        "goal_icon": "ゴールアイコン:",
        "upload": "アップロード...",
        "default": "初期アイコン",
        "close": "閉じる",
        "language": "言語:",
        "lang_auto": "自動 (LibreOffice の表示言語)",
        "not_impress": "Impress のプレゼンテーションを開いてから実行してください。",
        "pick_title": "アイコン画像を選択",
        "images": "画像ファイル",
        "copy_failed": "アイコンを読み込めませんでした:\n%s",
    },
    "en": {
        "title": "Presentation Pace Tracker",
        "planned": "Planned duration:",
        "min": "min",
        "sec": "sec",
        "autostart": "Also start the slide show",
        "measure": "Measurement",
        "elapsed": "Elapsed: %s / %s",
        "slide": "Slide: %d / %d",
        "slide_none": "Slide: (slide show not running)",
        "state_idle": "State: stopped",
        "state_run": "State: measuring",
        "state_over": "State: measuring (over time)",
        "no_presenter": " - hidden, no Presenter Console",
        "target": "Show on:",
        "target_slides": "Slides (audience)",
        "target_presenter": "Presenter Console only",
        "start": "Start",
        "reset": "Reset",
        "area": "Display area (% of the screen)",
        "area_pos": "Position",
        "area_size": "Size",
        "area_x": "X:",
        "area_x_note": "% from left",
        "area_y": "Y:",
        "area_y_note": "% from bottom",
        "area_y_note_top": "% from top",
        "area_w": "Width:",
        "area_w_note": "% of width",
        "area_h": "Height:",
        "area_h_note": "% of height",
        "icons": "Icons",
        "time_icon": "Time icon:",
        "slide_icon": "Slide icon:",
        "start_icon": "Start icon:",
        "goal_icon": "Goal icon:",
        "upload": "Upload...",
        "default": "Default",
        "close": "Close",
        "language": "Language:",
        "lang_auto": "Auto (LibreOffice UI language)",
        "not_impress": "Please open an Impress presentation first.",
        "pick_title": "Select an icon image",
        "images": "Image files",
        "copy_failed": "The icon could not be loaded:\n%s",
    },
}

DEFAULT_SETTINGS = {
    "planned_seconds": 20 * 60,
    "autostart_show": True,
    "time_icon": "",    # empty = default icon (turtle)
    "slide_icon": "",   # empty = default icon (rabbit)
    "start_icon": "",   # empty = default icon (green flag)
    "goal_icon": "",    # empty = default icon (checkered flag)
    "language": "auto",  # language of the dialog: "auto", "ja" or "en"
    "display_target": "slides",  # where the band is shown: "slides" or "presenter" (Presenter Console)
    # display area of the band on the slides, in % of the slide show window
    "area_x_pct": 0.0,      # left edge, from the left of the screen
    "area_y_pct": 0.0,      # bottom edge, from the bottom of the screen
    "area_w_pct": 100.0,    # width, relative to the screen width
    "area_h_pct": 8.5,      # height, relative to the screen height
    # display area on the Presenter Console: at the top, so that the
    # console's own toolbar at the bottom stays usable. Here Y is the top
    # edge of the band, measured from the top of the screen.
    "presenter_area_x_pct": 0.0,
    "presenter_area_y_pct": 0.0,
    "presenter_area_w_pct": 100.0,
    "presenter_area_h_pct": 8.5,
    "presenter_y_from_top": True,  # marks settings saved with Y from the top on the Presenter Console
}

# (setting, dialog field, minimum, maximum) of the display area values
AREA_FIELDS = (
    ("area_x_pct", "area_x", 0.0, 95.0),
    ("area_y_pct", "area_y", 0.0, 95.0),
    ("area_w_pct", "area_w", 5.0, 100.0),
    ("area_h_pct", "area_h", 2.0, 50.0),
)
MIN_BAND_PX = 24
DISPLAY_TARGETS = ("slides", "presenter")


def area_key(target, key):
    """Settings key of a display area value (AREA_FIELDS key) for a display target."""
    return key if target == "slides" else target + "_" + key

# icons that can be replaced: (kind, default icon file in icons/ without ".png")
ICONS = (("time", "turtle"), ("slide", "rabbit"), ("start", "start_flag"), ("goal", "goal_flag"))

# entries of the language list box: (setting value, label; None = TEXTS[...]["lang_auto"])
LANGUAGES = (("auto", None), ("ja", "日本語"), ("en", "English"))


def _props(**kw):
    out = []
    for k, v in kw.items():
        p = PropertyValue()
        p.Name, p.Value = k, v
        out.append(p)
    return tuple(out)


def _fmt(seconds):
    seconds = int(max(0, seconds))
    h, rest = divmod(seconds, 3600)
    m, s = divmod(rest, 60)
    return "%d:%02d:%02d" % (h, m, s) if h else "%02d:%02d" % (m, s)


_LOG_FILE = None


def _log(msg):
    # Errors are written to <user profile>/pacetracker/pacetracker.log
    try:
        if _LOG_FILE:
            with open(_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
        else:
            print("[PaceTracker] " + msg)
    except Exception:
        pass


# --------------------------------------------------------------------------
# Main-thread callback and ticker thread
# --------------------------------------------------------------------------

class _MainThreadCallback(unohelper.Base, XCallback):
    def __init__(self, func):
        self.func = func

    def notify(self, data):
        try:
            self.func()
        except Exception:
            _log(traceback.format_exc())


class _Ticker(threading.Thread):
    """Posts a callback to the main (VCL) thread every TICK_SECONDS."""

    def __init__(self, ctx, func):
        threading.Thread.__init__(self, name="PaceTrackerTicker", daemon=True)
        self.async_cb = ctx.ServiceManager.createInstanceWithContext("com.sun.star.awt.AsyncCallback", ctx)
        self.callback = _MainThreadCallback(self._run_once)
        self.func = func
        self.stopped = threading.Event()
        self.pending = threading.Event()

    def _run_once(self):
        self.pending.clear()
        if not self.stopped.is_set():
            self.func()

    def run(self):
        while not self.stopped.wait(TICK_SECONDS):
            if self.pending.is_set():
                continue  # main thread is busy (e.g. a modal dialog); do not pile up calls
            self.pending.set()
            try:
                self.async_cb.addCallback(self.callback, None)
            except Exception:
                self.pending.clear()

    def stop(self):
        self.stopped.set()


# --------------------------------------------------------------------------
# Progress band shown at the bottom of the slide show
# --------------------------------------------------------------------------

class _Part(object):
    """One control of the band and the floating window it is shown in."""

    def __init__(self, ctl, window):
        self.ctl = ctl
        self.window = window  # None: the control is in the shared band window


class Overlay(object):
    """The flags, the moving icons and the pace line.

    There is no visible band: windows drawn over the slide show cannot be
    really transparent, so the background of the parts is set to the color
    behind them.

    shared=False (slides): each part is a small floating window owned by the
    slide show window, so the slide shows between the parts.
    shared=True (Presenter Console): all parts are in one floating window
    filled with the console's background color. The console does not repaint
    the area a moving window leaves, so the icons move inside that window.
    """

    def __init__(self, tracker, parent, background=WHITE, shared=False):
        """parent: top window of the slide show or of the Presenter Console."""
        self.tracker = tracker
        self.parent = parent
        self.background = background
        self.band_window = self._new_window() if shared else None
        self.parts = []
        self.track = self._add_box(PACE_OK)
        self.start_img = self._add_image(tracker.icon_url("start"))
        self.goal_img = self._add_image(tracker.icon_url("goal"))
        self.slide_img = self._add_image(tracker.icon_url("slide"))
        self.time_img = self._add_image(tracker.icon_url("time"))
        self.images = [self.start_img, self.goal_img, self.slide_img, self.time_img]
        self.size = None
        self.last = None
        self.moved = False
        self.layout()
        for part in self.parts:
            part.ctl.setVisible(True)
        for window in self.windows():
            window.setVisible(True)

    def _new_window(self):
        desc = WindowDescriptor()
        desc.Type = TOP
        desc.WindowServiceName = "floatingwindow"
        desc.Parent = self.parent
        desc.Bounds = Rectangle(0, 0, 1, 1)
        desc.WindowAttributes = 0  # no attributes: no frame around the window
        window = self.tracker.toolkit.createWindow(desc)
        window.setBackground(self.background)
        return window

    def _create(self, kind, background, **props):
        tracker = self.tracker
        window = None if self.band_window is not None else self._new_window()
        model = tracker.smgr.createInstanceWithContext("com.sun.star.awt.UnoControl%sModel" % kind, tracker.ctx)
        model.BackgroundColor = background
        model.Border = 0
        for k, v in props.items():
            setattr(model, k, v)
        ctl = tracker.smgr.createInstanceWithContext("com.sun.star.awt.UnoControl%s" % kind, tracker.ctx)
        ctl.setModel(model)
        ctl.createPeer(tracker.toolkit, window if window is not None else self.band_window)
        part = _Part(ctl, window)
        self.parts.append(part)
        return part

    def _add_box(self, color):
        return self._create("FixedText", color, Label="")

    def _add_image(self, url):
        return self._create("ImageControl", self.background, ScaleImage=True,
                            ScaleMode=1,  # ISOTROPIC: keep the aspect ratio
                            Tabstop=False, ImageURL=url)

    def windows(self):
        if self.band_window is not None:
            return [self.band_window]
        return [part.window for part in self.parts]

    def set_icon(self, which, url):
        part = {"time": self.time_img, "slide": self.slide_img,
                "start": self.start_img, "goal": self.goal_img}[which]
        part.ctl.getModel().ImageURL = url

    def set_background(self, color):
        """Color behind the icons, so that their background does not show."""
        if color == self.background:
            return
        self.background = color
        for part in self.images:
            part.ctl.getModel().BackgroundColor = color
            if part.window is not None:
                part.window.setBackground(color)
        if self.band_window is not None:
            self.band_window.setBackground(color)
            self.moved = True

    def alive(self):
        try:
            self.parent.getPosSize()
            return True
        except Exception:
            return False

    def area(self, screen_w, screen_h):
        """Position and size (x, y, width, height) of the band in pixels."""
        st = self.tracker.settings
        target = st["display_target"]

        def pct(key):
            return st[area_key(target, key)]
        band = max(MIN_BAND_PX, int(round(screen_h * pct("area_h_pct") / 100.0)))
        band = min(band, screen_h)
        # the flags and both icons must fit next to each other
        width = min(screen_w, max(int(round(screen_w * pct("area_w_pct") / 100.0)), 4 * band))
        x = min(int(round(screen_w * pct("area_x_pct") / 100.0)), screen_w - width)
        offset = min(int(round(screen_h * pct("area_y_pct") / 100.0)), screen_h - band)
        if target == "presenter":
            return x, offset, width, band              # Y from the top of the screen
        return x, screen_h - offset - band, width, band  # Y from the bottom of the screen

    def _place(self, part, x, y, w=0, h=0):
        """Position a part at band coordinates (w, h = 0: keep the size)."""
        if part.window is None:
            # in the shared band window
            if w and h:
                part.ctl.setPosSize(x, y, w, h, POSSIZE)
            else:
                part.ctl.setPosSize(x, y, 0, 0, POS)
        elif w and h:
            part.window.setPosSize(self.ox + x, self.oy + y, w, h, POSSIZE)
            part.ctl.setPosSize(0, 0, w, h, POSSIZE)
        else:
            part.window.setPosSize(self.ox + x, self.oy + y, 0, 0, POS)

    def layout(self):
        # floating windows are positioned relative to their parent window
        r = self.parent.getPosSize()
        x, y, W, band = self.area(r.Width, r.Height)
        if self.size == (x, y, W, band):
            return
        self.size = (x, y, W, band)
        self.ox, self.oy = x, y
        if self.band_window is not None:
            self.band_window.setPosSize(x, y, W, band, POSSIZE)
        pad = max(2, band // 30)
        # two rows: slide icon on top, time icon below, the pace line between them
        line = max(3, band // 24)
        self.icon = (band - 3 * pad - line) // 2
        self.row_top = pad
        self.row_bottom = band - pad - self.icon
        # the start and goal flags have the same size as the moving icons
        flag = self.icon
        flag_y = (band - flag) // 2
        self._place(self.start_img, pad, flag_y, flag, flag)
        self._place(self.goal_img, W - pad - flag, flag_y, flag, flag)
        self.x0 = pad + flag + pad
        self.x1 = W - pad - flag - pad - self.icon
        self._place(self.track, self.x0, self.row_top + self.icon + (self.row_bottom - self.row_top - self.icon - line) // 2,
                    W - 2 * self.x0, line)
        self._place(self.slide_img, self.x0, self.row_top, self.icon, self.icon)
        self._place(self.time_img, self.x0, self.row_bottom, self.icon, self.icon)
        self.last = None

    def repaint_if_needed(self):
        # moved icons leave a trail in the shared band window unless it is repainted
        if self.band_window is not None and self.moved:
            self.moved = False
            try:
                self.band_window.invalidate(1 | 8)  # InvalidateStyle CHILDREN | UPDATE
            except Exception:
                pass

    def update(self, time_progress, slide_progress):
        self.layout()
        xs = int(self.x0 + (self.x1 - self.x0) * min(max(slide_progress, 0.0), 1.0))
        xt = int(self.x0 + (self.x1 - self.x0) * min(max(time_progress, 0.0), 1.0))
        behind = time_progress - slide_progress
        if time_progress >= 1.0 and slide_progress < 1.0 or behind > 0.10:
            color = PACE_LATE
        elif behind > 0.02:
            color = PACE_WARN
        else:
            color = PACE_OK
        state = (xs, xt, color)
        if state == self.last:
            return
        self.moved = True
        if self.last is None or self.last[0] != xs:
            self._place(self.slide_img, xs, self.row_top)
        if self.last is None or self.last[1] != xt:
            self._place(self.time_img, xt, self.row_bottom)
        if self.last is None or self.last[2] != color:
            self.track.ctl.getModel().BackgroundColor = color
        self.last = state

    def dispose(self):
        for part in self.parts:
            try:
                part.ctl.setVisible(False)
                part.ctl.dispose()
            except Exception:
                pass
        for window in self.windows():
            try:
                window.setVisible(False)
                window.dispose()
            except Exception:
                pass


# --------------------------------------------------------------------------
# Management dialog
# --------------------------------------------------------------------------

class _DialogListener(unohelper.Base, XActionListener, XItemListener, XTopWindowListener):
    def __init__(self, tracker):
        self.tracker = tracker

    def itemStateChanged(self, ev):
        try:
            self.tracker.on_language_selected(ev.Selected)
        except Exception:
            _log(traceback.format_exc())

    def actionPerformed(self, ev):
        try:
            self.tracker.on_command(ev.ActionCommand)
        except Exception:
            _log(traceback.format_exc())

    def windowClosing(self, ev):
        self.tracker.close_dialog()

    def windowOpened(self, ev): pass
    def windowClosed(self, ev): pass
    def windowMinimized(self, ev): pass
    def windowNormalized(self, ev): pass
    def windowActivated(self, ev): pass
    def windowDeactivated(self, ev): pass
    def disposing(self, ev): pass


class _TerminateListener(unohelper.Base, XTerminateListener):
    def __init__(self, tracker):
        self.tracker = tracker

    def queryTermination(self, ev):
        pass

    def notifyTermination(self, ev):
        self.tracker.shutdown()

    def disposing(self, ev):
        pass


class Tracker(object):
    """Process wide state of the extension (one measurement at a time)."""

    instance = None

    @classmethod
    def get(cls, ctx):
        if cls.instance is None:
            cls.instance = Tracker(ctx)
        return cls.instance

    def __init__(self, ctx):
        self.ctx = ctx
        self.smgr = ctx.ServiceManager
        self.toolkit = self.smgr.createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)
        self.desktop = self.smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
        self.ui_language = self._ui_language()
        pip = ctx.getValueByName("/singletons/com.sun.star.deployment.PackageInformationProvider")
        self.ext_url = pip.getPackageLocation(EXTENSION_ID)
        subst = self.smgr.createInstanceWithContext("com.sun.star.util.PathSubstitution", ctx)
        self.user_dir = uno.fileUrlToSystemPath(subst.substituteVariables("$(user)/pacetracker", True))
        self.settings = self._load_settings()
        global _LOG_FILE
        _LOG_FILE = os.path.join(self.user_dir, "pacetracker.log")

        self.doc = None            # presentation being tracked
        self.edit_frames = []      # frames of self.doc that are not the slide show
        self.started_at = None     # time.monotonic() when measuring started; None = stopped
        self.overlay = None
        self.last_slide = None
        self.dialog = None
        self.ticker = None
        self.desktop.addTerminateListener(_TerminateListener(self))

    # ---------------- settings / icons ----------------

    def _ui_language(self):
        try:
            cp = self.smgr.createInstanceWithContext("com.sun.star.configuration.ConfigurationProvider", self.ctx)
            node = cp.createInstanceWithArguments("com.sun.star.configuration.ConfigurationAccess",
                                                  _props(nodepath="/org.openoffice.Setup/L10N"))
            lang = (node.getByName("ooLocale") or "en").lower()
        except Exception:
            lang = "en"
        return "ja" if lang.startswith("ja") else "en"

    @property
    def texts(self):
        lang = self.settings.get("language", "auto")
        return TEXTS[lang if lang in TEXTS else self.ui_language]

    def _settings_path(self):
        return os.path.join(self.user_dir, "settings.json")

    def _load_settings(self):
        os.makedirs(self.user_dir, exist_ok=True)
        settings = dict(DEFAULT_SETTINGS)
        try:
            with open(self._settings_path(), encoding="utf-8") as f:
                loaded = json.load(f)
            # Before presenter_y_from_top, the Presenter Console Y was measured
            # from the bottom like on the slides: convert it to "from the top".
            if "presenter_area_y_pct" in loaded and not loaded.get("presenter_y_from_top"):
                loaded["presenter_area_y_pct"] = max(0.0, 100.0 - float(loaded["presenter_area_y_pct"])
                                                     - float(loaded.get("presenter_area_h_pct", 8.5)))
            loaded["presenter_y_from_top"] = True
            settings.update(loaded)
        except Exception:
            pass
        for key in [kind + "_icon" for kind, _ in ICONS]:
            if settings[key] and not os.path.isfile(settings[key]):
                settings[key] = ""
        if settings["display_target"] not in DISPLAY_TARGETS:
            settings["display_target"] = "slides"
        if settings["language"] not in [value for value, _ in LANGUAGES]:
            settings["language"] = "auto"
        for target in DISPLAY_TARGETS:
            for base, _, low, high in AREA_FIELDS:
                key = area_key(target, base)
                try:
                    settings[key] = min(max(float(settings[key]), low), high)
                except (TypeError, ValueError):
                    settings[key] = DEFAULT_SETTINGS[key]
        return settings

    def save_settings(self):
        try:
            os.makedirs(self.user_dir, exist_ok=True)
            with open(self._settings_path(), "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception:
            _log(traceback.format_exc())

    def icon_url(self, which):
        """which: 'time', 'slide', 'start' or 'goal'."""
        custom = self.settings[which + "_icon"]
        if custom:
            return uno.systemPathToFileUrl(custom)
        return self.ext_url + "/icons/" + dict(ICONS)[which] + ".png"

    def upload_icon(self, which):
        picker = self.smgr.createInstanceWithContext("com.sun.star.ui.dialogs.FilePicker", self.ctx)
        picker.setTitle(self.texts["pick_title"])
        picker.appendFilter(self.texts["images"], "*.png;*.svg;*.jpg;*.jpeg;*.gif;*.bmp;*.webp")
        if picker.execute() != 1:
            return
        src = uno.fileUrlToSystemPath(picker.getSelectedFiles()[0])
        try:
            os.makedirs(self.user_dir, exist_ok=True)
            ext = os.path.splitext(src)[1].lower() or ".png"
            # a new file name each time, so the image cache never shows the old icon
            dst = os.path.join(self.user_dir, "%s_icon_%d%s" % (which, int(time.time()), ext))
            shutil.copyfile(src, dst)
        except Exception as e:
            self.message(self.texts["copy_failed"] % e)
            return
        self._remove_custom_icon(which)
        self.settings[which + "_icon"] = dst
        self.save_settings()
        self._icon_changed(which)

    def reset_icon(self, which):
        self._remove_custom_icon(which)
        self.settings[which + "_icon"] = ""
        self.save_settings()
        self._icon_changed(which)

    def _remove_custom_icon(self, which):
        old = self.settings[which + "_icon"]
        if old and os.path.dirname(os.path.abspath(old)) == os.path.abspath(self.user_dir):
            try:
                os.remove(old)
            except Exception:
                pass

    def _icon_changed(self, which):
        url = self.icon_url(which)
        if self.dialog is not None:
            self.dialog.getControl(which + "_preview").getModel().ImageURL = url
        if self.overlay is not None:
            self.overlay.set_icon(which, url)

    # ---------------- measurement ----------------

    @property
    def planned_seconds(self):
        return max(1, int(self.settings["planned_seconds"]))

    def elapsed(self):
        return 0.0 if self.started_at is None else time.monotonic() - self.started_at

    def start(self):
        self._read_dialog_values()
        self.save_settings()
        if self.started_at is None:
            self.started_at = time.monotonic()
        if self.settings["autostart_show"] and self.doc is not None and self._controller() is None:
            self._remember_edit_frames()
            self.doc.Presentation.start()
        self._ensure_ticker()
        self.tick()

    def reset(self):
        self.started_at = None
        ctrl = self._controller()
        if ctrl is not None:
            try:
                ctrl.gotoFirstSlide()
            except Exception:
                pass
        self.tick()

    def _controller(self):
        """The XSlideShowController of the running show, or None."""
        if self.doc is None:
            return None
        try:
            ctrl = self.doc.Presentation.getController()
            if ctrl is not None and ctrl.isRunning():
                return ctrl
        except Exception:
            # the document was closed
            self.doc = None
            self.edit_frames = []
        return None

    def _frames_of_doc(self):
        frames = []
        try:
            all_frames = self.desktop.getFrames()
            for i in range(all_frames.getCount()):
                f = all_frames.getByIndex(i)
                ctl = f.getController()
                if ctl is not None and ctl.getModel() == self.doc:
                    frames.append(f)
        except Exception:
            pass
        return frames

    def _remember_edit_frames(self):
        self.edit_frames = self._frames_of_doc()

    def _show_frame(self):
        """The frame of the full screen slide show of self.doc."""
        candidates = [f for f in self._frames_of_doc() if not any(f == e for e in self.edit_frames)]
        if not candidates:
            # The show was started before we knew the edit frames:
            # the slide show frame is the one without a menu bar.
            for f in self._frames_of_doc():
                try:
                    if f.LayoutManager.getElement("private:resource/menubar/menubar") is None:
                        candidates.append(f)
                except Exception:
                    pass
        if not candidates:
            return None

        def area(f):
            r = f.getContainerWindow().getPosSize()
            return r.Width * r.Height
        return max(candidates, key=area)

    @staticmethod
    def _slide_background(ctrl):
        """Background color of the current slide (white if it is not a plain color)."""
        try:
            page = ctrl.getCurrentSlide()
            for p in (page, page.MasterPage):
                try:
                    bg = p.Background
                except Exception:
                    bg = None
                if bg is None:
                    continue
                style = bg.FillStyle.value
                if style == "SOLID":
                    return bg.FillColor
                if style == "GRADIENT":
                    # the band is usually at the bottom: use the end color
                    return bg.FillGradient.EndColor
                if style != "NONE":
                    break  # bitmap or hatch: no single color
        except Exception:
            pass
        return WHITE

    def _overlay_parent(self):
        """The window the band is shown in, or None."""
        if self.settings["display_target"] == "presenter":
            return self._presenter_window()
        frame = self._show_frame()
        return frame.getContainerWindow() if frame is not None else None

    def _presenter_window(self):
        """The Presenter Console window of the running slide show, or None.

        The Presenter Console is a top level window that, unlike the slide show
        and the document windows, does not belong to a frame.
        """
        frame_windows = []
        frames = self.desktop.getFrames()
        for i in range(frames.getCount()):
            try:
                frame_windows.append(frames.getByIndex(i).getContainerWindow())
            except Exception:
                pass
        dialog_peer = self.dialog.getPeer() if self.dialog is not None else None
        own = self.overlay.windows() if self.overlay is not None else []
        best, best_area = None, 0
        for i in range(self.toolkit.getTopWindowCount()):
            w = self.toolkit.getTopWindow(i)
            try:
                if not w.isVisible():
                    continue
                r = w.getPosSize()
                if r.Width < 400 or r.Height < 300:  # message boxes and other small windows
                    continue
                if any(w == f for f in frame_windows) or (dialog_peer is not None and w == dialog_peer):
                    continue
                if any(w == o for o in own):  # the parts of the band itself
                    continue
                if r.Width * r.Height > best_area:
                    best, best_area = w, r.Width * r.Height
            except Exception:
                pass
        return best

    def tick(self):
        ctrl = self._controller()
        if ctrl is None:
            self._remember_edit_frames()
            self._drop_overlay()
        else:
            parent = self._overlay_parent()
            if self.overlay is not None and (not self.overlay.alive() or not self.overlay.parent == parent):
                self._drop_overlay()
            if self.overlay is None and parent is not None:
                presenter = self.settings["display_target"] == "presenter"
                self.overlay = Overlay(self, parent, shared=presenter,
                                       background=PRESENTER_BACKGROUND if presenter else self._slide_background(ctrl))
        self._read_dialog_values()
        elapsed = self.elapsed()
        time_progress = elapsed / self.planned_seconds
        index, count = (ctrl.getCurrentSlideIndex(), ctrl.getSlideCount()) if ctrl is not None else (0, 0)
        measuring = self.started_at is not None
        if measuring and count > 1:
            slide_progress = max(0, index) / float(count - 1)
        elif measuring and count == 1:
            slide_progress = 1.0
        else:
            slide_progress = 0.0
        if self.overlay is not None:
            if index != self.last_slide and self.settings["display_target"] == "slides":
                self.overlay.set_background(self._slide_background(ctrl))
            self.overlay.update(time_progress, slide_progress)
            self.overlay.repaint_if_needed()
        self.last_slide = index
        self._update_dialog(elapsed, index, count, ctrl is not None and self.overlay is None)
        if not measuring and self.dialog is None and self.overlay is None:
            self._stop_ticker()

    def _drop_overlay(self):
        if self.overlay is not None:
            self.overlay.dispose()
            self.overlay = None

    def _ensure_ticker(self):
        if self.ticker is None:
            self.ticker = _Ticker(self.ctx, self.tick)
            self.ticker.start()

    def _stop_ticker(self):
        if self.ticker is not None:
            self.ticker.stop()
            self.ticker = None

    def shutdown(self):
        self._stop_ticker()
        self._drop_overlay()
        self.close_dialog()

    # ---------------- dialog ----------------

    def find_presentation(self):
        """The active Impress document, else the tracked one, else any open one."""
        def is_presentation(doc):
            try:
                return doc is not None and doc.supportsService("com.sun.star.presentation.PresentationDocument")
            except Exception:
                return False
        current = self.desktop.getCurrentComponent()
        if is_presentation(current):
            return current
        if self._controller() is not None or is_presentation(self.doc):
            return self.doc
        docs = self.desktop.getComponents().createEnumeration()
        while docs.hasMoreElements():
            doc = docs.nextElement()
            if is_presentation(doc):
                return doc
        return None

    def open_dialog(self, doc):
        if self.doc is None or not doc == self.doc:
            if self.doc is not None and self._controller() is None:
                self.started_at = None  # switching to another presentation
            self.doc = doc
            self._remember_edit_frames()
        if self.dialog is not None:
            self.dialog.setVisible(True)
            try:
                self.dialog.toFront()
            except Exception:
                pass
            return
        self.dialog = self._build_dialog()
        self._ensure_ticker()
        self.tick()

    def close_dialog(self):
        if self.dialog is None:
            return
        self._read_dialog_values()
        self.save_settings()
        dialog, self.dialog = self.dialog, None
        try:
            dialog.setVisible(False)
            dialog.dispose()
        except Exception:
            pass

    def on_language_selected(self, index):
        if not 0 <= index < len(LANGUAGES) or LANGUAGES[index][0] == self.settings["language"]:
            return
        self.settings["language"] = LANGUAGES[index][0]
        # Rebuild the dialog after the list box event has finished.
        self._run_later(self._rebuild_dialog)

    def _run_later(self, func):
        self._later = _MainThreadCallback(func)  # keep a reference until it runs
        self.smgr.createInstanceWithContext("com.sun.star.awt.AsyncCallback", self.ctx).addCallback(self._later, None)

    def _rebuild_dialog(self):
        if self.dialog is None:
            return
        pos = self.dialog.getPosSize()
        self.close_dialog()
        self.dialog = self._build_dialog()
        self.dialog.setPosSize(pos.X, pos.Y, 0, 0, POS)
        self.tick()

    def on_command(self, cmd):
        if cmd == "start":
            self.start()
        elif cmd == "reset":
            self.reset()
        elif cmd == "close":
            self.close_dialog()
        elif cmd.startswith("upload_"):
            self.upload_icon(cmd[len("upload_"):])
        elif cmd.startswith("default_"):
            self.reset_icon(cmd[len("default_"):])

    def _read_dialog_values(self):
        if self.dialog is None:
            return
        minutes = int(self.dialog.getControl("minutes").getModel().Value or 0)
        seconds = int(self.dialog.getControl("seconds").getModel().Value or 0)
        self.settings["planned_seconds"] = max(1, minutes * 60 + seconds)
        self.settings["autostart_show"] = self.dialog.getControl("autostart").getModel().State == 1
        target = "presenter" if self.dialog.getControl("target_presenter").getModel().State == 1 else "slides"
        if target != self.settings["display_target"]:
            # the display area fields show the values of the selected target
            self.settings["display_target"] = target
            self.dialog.getControl("note_area_y").getModel().Label = self._area_note("area_y")
            for base, field, _, _ in AREA_FIELDS:
                self.dialog.getControl(field).getModel().Value = self.settings[area_key(target, base)]
            return
        for base, field, low, high in AREA_FIELDS:
            value = self.dialog.getControl(field).getModel().Value
            if value is not None:
                self.settings[area_key(target, base)] = min(max(float(value), low), high)

    def _update_dialog(self, elapsed, index, count, hidden=False):
        if self.dialog is None:
            return
        t = self.texts
        measuring = self.started_at is not None

        def label(name, text):
            model = self.dialog.getControl(name).getModel()
            if model.Label != text:
                model.Label = text
        label("elapsed", t["elapsed"] % (_fmt(elapsed), _fmt(self.planned_seconds)))
        label("slide", t["slide"] % (index + 1, count) if count else t["slide_none"])
        if not measuring:
            state = t["state_idle"]
        else:
            state = t["state_over"] if elapsed > self.planned_seconds else t["state_run"]
        if hidden and self.settings["display_target"] == "presenter":
            state += t["no_presenter"]
        label("state", state)
        start_model = self.dialog.getControl("start").getModel()
        if start_model.Enabled == measuring:
            start_model.Enabled = not measuring

    def _area_note(self, field):
        """Unit label of a display area field; Y is from the top on the Presenter Console."""
        if field == "area_y" and self.settings["display_target"] == "presenter":
            return self.texts["area_y_note_top"]
        return self.texts[field + "_note"]

    def _build_dialog(self):
        t = self.texts
        smgr, ctx = self.smgr, self.ctx
        dm = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialogModel", ctx)
        dm.Title = t["title"]
        dm.Width, dm.Height = 252, 314
        dm.Closeable = True
        dm.Moveable = True

        def add(name, kind, x, y, w, h, **props):
            m = dm.createInstance("com.sun.star.awt.UnoControl%sModel" % kind)
            m.PositionX, m.PositionY, m.Width, m.Height = x, y, w, h
            for k, v in props.items():
                setattr(m, k, v)
            dm.insertByName(name, m)
            return m

        planned = self.planned_seconds
        add("lbl_planned", "FixedText", 8, 10, 70, 10, Label=t["planned"])
        add("minutes", "NumericField", 80, 8, 40, 13, Value=planned // 60, ValueMin=0, ValueMax=999,
            DecimalAccuracy=0, Spin=True, StrictFormat=True)
        add("lbl_min", "FixedText", 123, 10, 18, 10, Label=t["min"])
        add("seconds", "NumericField", 142, 8, 34, 13, Value=planned % 60, ValueMin=0, ValueMax=59,
            DecimalAccuracy=0, Spin=True, StrictFormat=True)
        add("lbl_sec", "FixedText", 179, 10, 20, 10, Label=t["sec"])
        add("autostart", "CheckBox", 8, 26, 236, 10, Label=t["autostart"],
            State=1 if self.settings["autostart_show"] else 0)

        add("grp_measure", "GroupBox", 4, 40, 244, 64, Label=t["measure"])
        add("state", "FixedText", 10, 52, 210, 10, Label="")
        add("elapsed", "FixedText", 10, 63, 210, 10, Label="")
        add("slide", "FixedText", 10, 74, 210, 10, Label="")
        add("start", "Button", 10, 86, 60, 14, Label=t["start"], DefaultButton=True)
        add("reset", "Button", 76, 86, 60, 14, Label=t["reset"])

        add("grp_area", "GroupBox", 4, 108, 244, 62, Label=t["area"])
        presenter = self.settings["display_target"] == "presenter"
        add("lbl_target", "FixedText", 10, 122, 34, 10, Label=t["target"])
        add("target_slides", "RadioButton", 46, 121, 92, 11, Label=t["target_slides"],
            State=0 if presenter else 1)
        add("target_presenter", "RadioButton", 142, 121, 104, 11, Label=t["target_presenter"],
            State=1 if presenter else 0)
        add("lbl_area_pos", "FixedText", 10, 138, 34, 10, Label=t["area_pos"])
        add("lbl_area_size", "FixedText", 10, 154, 34, 10, Label=t["area_size"])
        for i, (base, field, low, high) in enumerate(AREA_FIELDS):
            key = area_key(self.settings["display_target"], base)
            # X, Y on the first row, width, height on the second row
            x = 46 if i % 2 == 0 else 142
            y = 136 + (i // 2) * 16
            add("lbl_" + field, "FixedText", x, y + 2, 28, 10, Label=t[field])
            add(field, "NumericField", x + 29, y, 30, 13, Value=self.settings[key], ValueMin=low, ValueMax=high,
                DecimalAccuracy=1, Spin=True, ValueStep=0.5, StrictFormat=True)
            add("note_" + field, "FixedText", x + 61, y + 2, 33 if i % 2 == 0 else 44, 10,
                Label=self._area_note(field))

        add("grp_icons", "GroupBox", 4, 174, 244, 118, Label=t["icons"])
        for i, (which, _) in enumerate(ICONS):
            y = 186 + i * 26
            add("lbl_" + which, "FixedText", 10, y + 6, 60, 10, Label=t[which + "_icon"])
            add(which + "_preview", "ImageControl", 72, y, 22, 22, ImageURL=self.icon_url(which),
                ScaleImage=True, ScaleMode=1, Border=1)
            add("upload_" + which, "Button", 104, y + 4, 76, 14, Label=t["upload"])
            add("default_" + which, "Button", 186, y + 4, 56, 14, Label=t["default"])

        add("lbl_language", "FixedText", 8, 298, 34, 10, Label=t["language"])
        languages = tuple(label or t["lang_auto"] for _, label in LANGUAGES)
        current = [value for value, _ in LANGUAGES].index(self.settings["language"])
        lb = add("language", "ListBox", 44, 296, 130, 14, Dropdown=True, StringItemList=languages,
                 LineCount=len(languages))
        uno.invoke(lb, "setPropertyValue", ("SelectedItems", uno.Any("[]short", (current,))))
        add("close", "Button", 186, 296, 60, 14, Label=t["close"])

        dialog = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialog", ctx)
        dialog.setModel(dm)
        listener = _DialogListener(self)
        commands = ["start", "reset", "close"]
        for which, _ in ICONS:
            commands += ["upload_" + which, "default_" + which]
        for name in commands:
            ctl = dialog.getControl(name)
            ctl.setActionCommand(name)
            ctl.addActionListener(listener)
        dialog.getControl("language").addItemListener(listener)
        parent = None
        try:
            parent = self.doc.getCurrentController().getFrame().getContainerWindow()
        except Exception:
            pass
        dialog.createPeer(self.toolkit, parent)
        dialog.addTopWindowListener(listener)
        self._center(dialog, parent)
        dialog.setVisible(True)
        return dialog

    @staticmethod
    def _center(dialog, parent):
        if parent is None:
            return
        try:
            p = parent.getPosSize()
            d = dialog.getPosSize()
            dialog.setPosSize(p.X + (p.Width - d.Width) // 2, p.Y + (p.Height - d.Height) // 3, 0, 0, POS)
        except Exception:
            pass

    def message(self, text):
        parent = self.dialog.getPeer() if self.dialog is not None else None
        try:
            box = self.toolkit.createMessageBox(parent, uno.Enum("com.sun.star.awt.MessageBoxType", "INFOBOX"),
                                                1, self.texts["title"], text)
            box.execute()
        except Exception:
            _log(text)


# --------------------------------------------------------------------------
# UNO component (called from the menu / toolbar)
# --------------------------------------------------------------------------

class PaceTrackerJob(unohelper.Base, XJobExecutor):
    def __init__(self, ctx):
        self.ctx = ctx

    def trigger(self, args):
        try:
            tracker = Tracker.get(self.ctx)
            doc = tracker.find_presentation()
            if doc is None:
                tracker.message(tracker.texts["not_impress"])
                return
            if args == "start":
                tracker.open_dialog(doc)
                tracker.start()
            elif args == "reset":
                tracker.open_dialog(doc)
                tracker.reset()
            else:
                tracker.open_dialog(doc)
        except Exception:
            _log(traceback.format_exc())


g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(PaceTrackerJob, IMPL_NAME, ("com.sun.star.task.Job",))
