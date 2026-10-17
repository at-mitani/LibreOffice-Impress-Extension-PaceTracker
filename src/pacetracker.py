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
# The band is a child window of the slide show frame's container window, so
# it is drawn inside the full screen show and never steals the keyboard focus.
# The slide show paints over the band when it changes slides, so the band is
# repainted after every slide change and periodically.
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
from com.sun.star.awt.PosSize import POS, POSSIZE
from com.sun.star.beans import PropertyValue
from com.sun.star.frame import XTerminateListener
from com.sun.star.task import XJobExecutor

EXTENSION_ID = "jp.atmitani.impress.pacetracker"
IMPL_NAME = EXTENSION_ID + ".PaceTracker"

TICK_SECONDS = 0.25
REPAINT_TICKS_AFTER_CHANGE = 12   # repaint every tick for 3 s after a slide change
REPAINT_EVERY_TICKS = 8           # otherwise repaint every 2 s

# Colors of the progress band
BAND_COLOR = 0xF4F4F4
BORDER_COLOR = 0xBDBDBD
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
        "start": "開始",
        "reset": "リセット",
        "area": "表示領域 (画面に対する %)",
        "area_pos": "開始位置",
        "area_size": "大きさ",
        "area_x": "X:",
        "area_x_note": "% 左端から",
        "area_y": "Y:",
        "area_y_note": "% 下端から",
        "area_w": "幅:",
        "area_w_note": "% 横幅比",
        "area_h": "高さ:",
        "area_h_note": "% 縦幅比",
        "icons": "アイコン",
        "time_icon": "時間アイコン:",
        "slide_icon": "スライドアイコン:",
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
        "start": "Start",
        "reset": "Reset",
        "area": "Display area (% of the screen)",
        "area_pos": "Position",
        "area_size": "Size",
        "area_x": "X:",
        "area_x_note": "% from left",
        "area_y": "Y:",
        "area_y_note": "% from bottom",
        "area_w": "Width:",
        "area_w_note": "% of width",
        "area_h": "Height:",
        "area_h_note": "% of height",
        "icons": "Icons",
        "time_icon": "Time icon:",
        "slide_icon": "Slide icon:",
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
    "language": "auto",  # language of the dialog: "auto", "ja" or "en"
    # display area of the band, in % of the slide show window
    "area_x_pct": 0.0,      # left edge, from the left of the screen
    "area_y_pct": 0.0,      # bottom edge, from the bottom of the screen
    "area_w_pct": 100.0,    # width, relative to the screen width
    "area_h_pct": 8.5,      # height, relative to the screen height
}

# (setting, dialog field, minimum, maximum) of the display area values
AREA_FIELDS = (
    ("area_x_pct", "area_x", 0.0, 95.0),
    ("area_y_pct", "area_y", 0.0, 95.0),
    ("area_w_pct", "area_w", 5.0, 100.0),
    ("area_h_pct", "area_h", 2.0, 50.0),
)
MIN_BAND_PX = 24

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

class Overlay(object):
    def __init__(self, tracker, frame):
        self.tracker = tracker
        self.frame = frame
        self.parent = frame.getContainerWindow()
        smgr = tracker.smgr
        ctx = tracker.ctx

        model = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlContainerModel", ctx)
        model.BackgroundColor = BAND_COLOR
        self.container = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlContainer", ctx)
        self.container.setModel(model)
        self.container.createPeer(tracker.toolkit, self.parent)

        self.border = self._add_box("border", BORDER_COLOR)
        self.track = self._add_box("track", PACE_OK)
        self.start_img = self._add_image("start", tracker.icon_url("start_flag"))
        self.goal_img = self._add_image("goal", tracker.icon_url("goal_flag"))
        self.slide_img = self._add_image("slide", tracker.icon_url("slide"))
        self.time_img = self._add_image("time", tracker.icon_url("time"))
        self.size = None
        self.last = None
        self.repaint_ticks = REPAINT_TICKS_AFTER_CHANGE
        self.tick_count = 0
        self.layout()
        self.container.setVisible(True)

    def _add_box(self, name, color):
        model = self.tracker.smgr.createInstanceWithContext("com.sun.star.awt.UnoControlFixedTextModel",
                                                            self.tracker.ctx)
        model.BackgroundColor = color
        model.Label = ""
        model.Border = 0
        ctl = self.tracker.smgr.createInstanceWithContext("com.sun.star.awt.UnoControlFixedText", self.tracker.ctx)
        ctl.setModel(model)
        self.container.addControl(name, ctl)
        return ctl

    def _add_image(self, name, url):
        model = self.tracker.smgr.createInstanceWithContext("com.sun.star.awt.UnoControlImageControlModel",
                                                            self.tracker.ctx)
        model.Border = 0
        model.BackgroundColor = BAND_COLOR
        model.ScaleImage = True
        model.ScaleMode = 1  # ISOTROPIC: keep the aspect ratio
        model.Tabstop = False
        model.ImageURL = url
        ctl = self.tracker.smgr.createInstanceWithContext("com.sun.star.awt.UnoControlImageControl",
                                                          self.tracker.ctx)
        ctl.setModel(model)
        self.container.addControl(name, ctl)
        return ctl

    def set_icon(self, which, url):
        ctl = self.time_img if which == "time" else self.slide_img
        ctl.getModel().ImageURL = url

    def alive(self):
        try:
            self.parent.getPosSize()
            return True
        except Exception:
            return False

    def area(self, screen_w, screen_h):
        """Position and size (x, y, width, height) of the band in pixels."""
        st = self.tracker.settings
        band = max(MIN_BAND_PX, int(round(screen_h * st["area_h_pct"] / 100.0)))
        band = min(band, screen_h)
        # the flags and both icons must fit next to each other
        width = min(screen_w, max(int(round(screen_w * st["area_w_pct"] / 100.0)), 4 * band))
        x = min(int(round(screen_w * st["area_x_pct"] / 100.0)), screen_w - width)
        bottom = min(int(round(screen_h * st["area_y_pct"] / 100.0)), screen_h - band)
        return x, screen_h - bottom - band, width, band

    def layout(self):
        r = self.parent.getPosSize()
        x, y, W, band = self.area(r.Width, r.Height)
        if self.size == (x, y, W, band):
            return
        self.size = (x, y, W, band)
        pad = max(2, band // 30)
        self.band = band
        self.container.setPosSize(x, y, W, band, POSSIZE)
        self.border.setPosSize(0, 0, W, 1, POSSIZE)
        flag = band - 2 * pad
        self.start_img.setPosSize(pad, pad, flag, flag, POSSIZE)
        self.goal_img.setPosSize(W - pad - flag, pad, flag, flag, POSSIZE)
        # two rows: slide icon on top, time icon below, the pace line between them
        line = max(3, band // 24)
        self.icon = (band - 3 * pad - line) // 2
        self.row_top = pad
        self.row_bottom = band - pad - self.icon
        self.x0 = pad + flag + pad
        self.x1 = W - pad - flag - pad - self.icon
        self.track.setPosSize(self.x0, self.row_top + self.icon + (self.row_bottom - self.row_top - self.icon - line) // 2,
                              W - 2 * self.x0, line, POSSIZE)
        self.slide_img.setPosSize(self.x0, self.row_top, self.icon, self.icon, POSSIZE)
        self.time_img.setPosSize(self.x0, self.row_bottom, self.icon, self.icon, POSSIZE)
        self.last = None

    def slide_changed(self):
        self.repaint_ticks = REPAINT_TICKS_AFTER_CHANGE

    def repaint_if_needed(self):
        self.tick_count += 1
        if self.repaint_ticks > 0 or self.tick_count % REPAINT_EVERY_TICKS == 0:
            self.repaint_ticks = max(0, self.repaint_ticks - 1)
            try:
                self.container.getPeer().invalidate(1 | 8)  # InvalidateStyle CHILDREN | UPDATE
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
        if self.last is None or self.last[0] != xs:
            self.slide_img.setPosSize(xs, self.row_top, 0, 0, POS)
        if self.last is None or self.last[1] != xt:
            self.time_img.setPosSize(xt, self.row_bottom, 0, 0, POS)
        if self.last is None or self.last[2] != color:
            self.track.getModel().BackgroundColor = color
        self.last = state

    def dispose(self):
        try:
            self.container.setVisible(False)
            self.container.dispose()
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
                settings.update(json.load(f))
        except Exception:
            pass
        for key in ("time_icon", "slide_icon"):
            if settings[key] and not os.path.isfile(settings[key]):
                settings[key] = ""
        if settings["language"] not in [value for value, _ in LANGUAGES]:
            settings["language"] = "auto"
        for key, _, low, high in AREA_FIELDS:
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
        """which: 'time', 'slide', 'start_flag' or 'goal_flag'."""
        if which in ("time", "slide"):
            custom = self.settings[which + "_icon"]
            if custom:
                return uno.systemPathToFileUrl(custom)
            which = "turtle" if which == "time" else "rabbit"
        return self.ext_url + "/icons/" + which + ".png"

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

    def tick(self):
        ctrl = self._controller()
        if ctrl is None:
            self._remember_edit_frames()
            self._drop_overlay()
        else:
            frame = self._show_frame()
            if self.overlay is not None and (not self.overlay.alive() or not self.overlay.frame == frame):
                self._drop_overlay()
            if self.overlay is None and frame is not None:
                self.overlay = Overlay(self, frame)
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
            if index != self.last_slide:
                self.overlay.slide_changed()
            self.overlay.update(time_progress, slide_progress)
            self.overlay.repaint_if_needed()
        self.last_slide = index
        self._update_dialog(elapsed, index, count)
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
        for key, field, low, high in AREA_FIELDS:
            value = self.dialog.getControl(field).getModel().Value
            if value is not None:
                self.settings[key] = min(max(float(value), low), high)

    def _update_dialog(self, elapsed, index, count):
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
            label("state", t["state_idle"])
        else:
            label("state", t["state_over"] if elapsed > self.planned_seconds else t["state_run"])
        start_model = self.dialog.getControl("start").getModel()
        if start_model.Enabled == measuring:
            start_model.Enabled = not measuring

    def _build_dialog(self):
        t = self.texts
        smgr, ctx = self.smgr, self.ctx
        dm = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialogModel", ctx)
        dm.Title = t["title"]
        dm.Width, dm.Height = 252, 246
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

        add("grp_area", "GroupBox", 4, 108, 244, 46, Label=t["area"])
        add("lbl_area_pos", "FixedText", 10, 122, 34, 10, Label=t["area_pos"])
        add("lbl_area_size", "FixedText", 10, 138, 34, 10, Label=t["area_size"])
        for i, (key, field, low, high) in enumerate(AREA_FIELDS):
            # X, Y on the first row, width, height on the second row
            x = 46 if i % 2 == 0 else 142
            y = 120 + (i // 2) * 16
            add("lbl_" + field, "FixedText", x, y + 2, 28, 10, Label=t[field])
            add(field, "NumericField", x + 29, y, 30, 13, Value=self.settings[key], ValueMin=low, ValueMax=high,
                DecimalAccuracy=1, Spin=True, ValueStep=0.5, StrictFormat=True)
            add("note_" + field, "FixedText", x + 61, y + 2, 33 if i % 2 == 0 else 44, 10,
                Label=t[field + "_note"])

        add("grp_icons", "GroupBox", 4, 158, 244, 66, Label=t["icons"])
        for i, which in enumerate(("time", "slide")):
            y = 170 + i * 26
            add("lbl_" + which, "FixedText", 10, y + 6, 60, 10, Label=t[which + "_icon"])
            add(which + "_preview", "ImageControl", 72, y, 22, 22, ImageURL=self.icon_url(which),
                ScaleImage=True, ScaleMode=1, Border=1)
            add("upload_" + which, "Button", 104, y + 4, 76, 14, Label=t["upload"])
            add("default_" + which, "Button", 186, y + 4, 56, 14, Label=t["default"])

        add("lbl_language", "FixedText", 8, 230, 34, 10, Label=t["language"])
        languages = tuple(label or t["lang_auto"] for _, label in LANGUAGES)
        current = [value for value, _ in LANGUAGES].index(self.settings["language"])
        lb = add("language", "ListBox", 44, 228, 130, 14, Dropdown=True, StringItemList=languages,
                 LineCount=len(languages))
        uno.invoke(lb, "setPropertyValue", ("SelectedItems", uno.Any("[]short", (current,))))
        add("close", "Button", 186, 228, 60, 14, Label=t["close"])

        dialog = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialog", ctx)
        dialog.setModel(dm)
        listener = _DialogListener(self)
        for name in ("start", "reset", "close", "upload_time", "default_time", "upload_slide", "default_slide"):
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
