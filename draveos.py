# -*- coding: utf-8 -*-
# DraveOS - een eigen bureaublad bovenop Windows voor de Drave-apps.
# Copyright (C) 2026 Dravenlock (Roger & Claudio). Vrije software onder de GNU GPL v3.0.
"""DraveOS

Geen echt besturingssysteem, maar een eigen bureaublad bovenop Windows:
- Taakbalk onderaan: links de tijd, in het midden je open apps, rechts de menuknop.
- Menu met alle apps per categorie, een zoekveld, en onderaan Instellingen, Doneren,
  Snelgids en Afsluiten.
- Apps openen IN DraveOS, elk in een eigen venster met titelbalk (minimaliseren, maximaliseren, sluiten).
- Volledig scherm of een venster zo groot als het scherm (F11 wisselt).
- Favorieten op het bureaublad.

De apps worden gezocht in de app-mappen uit de instellingen. Alles staat in DraveOS-data naast de app.
"""
import datetime
import json
import locale
import os
import subprocess
import sys
import threading
import traceback
import webbrowser

VERSIE = "0.1.2"
APP = "DraveOS"


def _base():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _res(*parts):
    base = getattr(sys, "_MEIPASS", None) or _base()
    p = os.path.join(base, *parts)
    return p if os.path.exists(p) else os.path.join(_base(), *parts)


DATA = os.path.join(_base(), "DraveOS-data")
try:
    os.makedirs(DATA, exist_ok=True)
except Exception:
    pass
INSTEL = os.path.join(DATA, "instellingen.json")
LOG = os.path.join(DATA, "error.log")


def _log(t):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("[%s] %s\n" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), t))
    except Exception:
        pass


sys.excepthook = lambda t, v, tb: (_log("".join(traceback.format_exception(t, v, tb))), sys.__excepthook__(t, v, tb))

from PyQt6.QtCore import Qt, QTimer, QSize, QRectF, QPointF, QFileInfo, QUrl, pyqtSignal, QObject
from PyQt6.QtGui import (QIcon, QPixmap, QImage, QPainter, QColor, QRadialGradient, QFont,
                         QWindow, QKeySequence, QShortcut, QDesktopServices)
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QPushButton, QHBoxLayout,
                             QVBoxLayout, QFrame, QMdiArea, QMdiSubWindow, QLineEdit, QScrollArea,
                             QGridLayout, QToolButton, QMenu, QDialog, QCheckBox, QListWidget,
                             QComboBox, QFileDialog, QMessageBox, QFileIconProvider, QSizeGrip)

import venster_win as vw

# ------------------------------------------------------------------ taal
try:
    _T = (locale.getlocale()[0] or "nl")
except Exception:
    _T = "nl"
NL = _T.lower().startswith(("nl", "dutch"))

TX = {
    "menu": ("Menu", "Menu"),
    "zoek": ("Typ om een app te zoeken ...", "Type to search for an app ..."),
    "alle": ("Alle apps", "All apps"),
    "instel": ("⚙  Instellingen", "⚙  Settings"),
    "doneer": ("♥  Doneren", "♥  Donate"),
    "gids": ("📖  Snelgids", "📖  Quick guide"),
    "over": ("ℹ  Over DraveOS", "ℹ  About DraveOS"),
    "uit": ("⏻  Afsluiten", "⏻  Shut down"),
    "geen_apps": ("Geen apps gevonden.\nKies bij Instellingen de map waar je Drave-apps staan.",
                  "No apps found.\nChoose the folder with your Drave apps in Settings."),
    "starten": ("%s wordt gestart ...", "Starting %s ..."),
    "geen_venster": ("%s draait, maar heeft geen venster om te tonen (misschien zit hij in het systeemvak).",
                     "%s is running, but has no window to show (maybe it sits in the system tray)."),
    "kon_niet": ("%s kon niet starten.", "%s could not start."),
    "op_bureaublad": ("Op het bureaublad zetten", "Put on the desktop"),
    "van_bureaublad": ("Van het bureaublad halen", "Remove from the desktop"),
    "buiten": ("Openen buiten DraveOS (gewoon venster)", "Open outside DraveOS (normal window)"),
    "verberg": ("Verbergen in het menu", "Hide from the menu"),
    "map_open": ("Map openen", "Open folder"),
    "uit_vraag": ("DraveOS afsluiten?\n\nAlle open apps worden ook gesloten.",
                  "Shut down DraveOS?\n\nAll open apps will be closed too."),
    "nog_vraag": ("%s vraagt nog iets (bijvoorbeeld of je wilt opslaan).\n\nToch alles sluiten?",
                  "%s is still asking something (for example whether to save).\n\nClose everything anyway?"),
    "uit_titel": ("Afsluiten", "Shut down"),
    "i_titel": ("Instellingen", "Settings"),
    "i_vol": ("Volledig scherm (F11 wisselt)", "Full screen (F11 toggles)"),
    "i_vol_start": ("Starten in volledig scherm", "Start in full screen"),
    "i_mappen": ("Mappen waar je apps staan:", "Folders with your apps:"),
    "i_map_bij": ("Map toevoegen", "Add folder"),
    "i_map_weg": ("Map weghalen", "Remove folder"),
    "i_verborgen": ("Verborgen apps (dubbelklik om weer te tonen):", "Hidden apps (double-click to show again):"),
    "i_achter": ("Achtergrond:", "Background:"),
    "i_tekst": ("Tekstgrootte:", "Text size:"),
    "i_foto": ("Eigen foto kiezen ...", "Choose own photo ..."),
    "i_ok": ("Opslaan", "Save"),
    "normaal": ("Normaal", "Normal"),
    "groot": ("Groot", "Large"),
    "extra": ("Extra groot", "Extra large"),
    "a_paars": ("Dravenlock paars", "Dravenlock purple"),
    "a_nacht": ("Nachtblauw", "Night blue"),
    "a_bos": ("Bos", "Forest"),
    "a_foto": ("Eigen foto", "Own photo"),
    "a_zon": ("Zonsondergang", "Sunset"),
    "a_grijs": ("Antraciet", "Anthracite"),
    "a_windows": ("Mijn Windows-achtergrond", "My Windows background"),
    "b_achter": ("🖼  Achtergrond", "🖼  Background"),
    "b_vullen": ("Foto: scherm vullen", "Photo: fill screen"),
    "b_passend": ("Foto: passend (hele foto)", "Photo: fit (whole photo)"),
    "b_rekken": ("Foto: uitrekken", "Photo: stretch"),
    "b_midden": ("Foto: in het midden", "Photo: centred"),
    "b_logo": ("DraveOS-logo op de achtergrond", "DraveOS logo on the background"),
    "b_instel": ("⚙  Instellingen ...", "⚙  Settings ..."),
    "i_passen": ("Foto:", "Photo:"),
    "bureau_hint": ("Rechtsklik op een app in het menu en kies 'Op het bureaublad zetten'.  Rechtsklik hier voor een andere achtergrond.",
                    "Right-click an app in the menu and choose 'Put on the desktop'.  Right-click here for another background."),
    "over_tekst": ("DraveOS %s\n\nEen eigen bureaublad voor de Drave-apps, bovenop Windows.\n\nGratis (donationware) · GNU GPL v3.0\nservice@dravenlock.nl · dravenlock.nl",
                   "DraveOS %s\n\nYour own desktop for the Drave apps, on top of Windows.\n\nFree (donationware) · GNU GPL v3.0\nservice@dravenlock.nl · dravenlock.nl"),
    "scan": ("Apps zoeken ...", "Looking for apps ..."),
    "vol_aan": ("Volledig scherm", "Full screen"),
    "vol_uit": ("Venster", "Window"),
}


def T(k):
    v = TX.get(k, (k, k))
    return v[0] if NL else v[1]


# ------------------------------------------------------------------ categorieën
CATEGORIEEN = ["AI", "Games", "Media en creatief", "Tools en kantoor", "Systeem en beveiliging",
               "Web en servers", "Mobiel", "Overig"]
CAT_EN = {"AI": "AI", "Games": "Games", "Media en creatief": "Media & creative", "Tools en kantoor": "Tools & office",
          "Systeem en beveiliging": "System & security", "Web en servers": "Web & servers",
          "Mobiel": "Mobile", "Overig": "Other"}
CAT_ICOON = {"AI": "🤖", "Games": "🎮", "Media en creatief": "🎨", "Tools en kantoor": "🗂", "Systeem en beveiliging": "🛡",
             "Web en servers": "🌐", "Mobiel": "📱", "Overig": "✨"}
# bekende (openbare) Drave-apps -> categorie, voor als de map het niet verraadt
BEKEND = {
    "dravechat": "AI", "dravejavis": "AI", "dravekitt": "AI", "dravemind": "AI",
    "dravedice": "Games", "dravefeest": "Games", "dravegames": "Games", "dravencrawl": "Games",
    "draveereader": "Media en creatief", "dravefoto": "Media en creatief", "dravemedia": "Media en creatief",
    "dravemotion": "Media en creatief", "dravepaint": "Media en creatief", "draveread": "Media en creatief",
    "dravesound": "Media en creatief", "dravestudio": "Media en creatief", "dravewall": "Media en creatief",
    "draveapk": "Mobiel",
    "dravegoednieuws": "Overig", "dravekas": "Overig", "draveradiotv": "Overig",
    "deskbutler": "Systeem en beveiliging", "dravebackup": "Systeem en beveiliging", "draveexplorer": "Systeem en beveiliging",
    "draveguard": "Systeem en beveiliging", "dravepurge": "Systeem en beveiliging", "dravesecam": "Systeem en beveiliging",
    "dravesetup_maker": "Systeem en beveiliging", "draveuninstall": "Systeem en beveiliging", "dravevault": "Systeem en beveiliging",
    "pysetup_maker": "Systeem en beveiliging",
    "draveagenda": "Tools en kantoor", "dravebeurs": "Tools en kantoor", "dravecodex": "Tools en kantoor",
    "dravecontrast": "Tools en kantoor", "draveconvert": "Tools en kantoor", "draveedit": "Tools en kantoor",
    "draveforms": "Tools en kantoor", "dravekookboek": "Tools en kantoor", "draveleon": "Tools en kantoor",
    "dravelink": "Tools en kantoor", "dravenote": "Tools en kantoor", "draveoffice": "Tools en kantoor",
    "dravepack": "Tools en kantoor", "dravepdf": "Tools en kantoor", "dravepoort": "Tools en kantoor",
    "draveschrijf": "Tools en kantoor", "dravesheet": "Tools en kantoor", "draveshopbuddy": "Tools en kantoor",
    "draveshot": "Tools en kantoor", "dravetag": "Tools en kantoor", "dravetranslate": "Tools en kantoor",
    "draveweer": "Tools en kantoor", "dravezoom": "Tools en kantoor",
    "dravenlock": "Web en servers", "draveonion": "Web en servers", "draveserver": "Web en servers",
}
NIET_APP = ("unins", "uninst", "ffmpeg", "ffprobe", "python", "pythonw", "w9xpopen", "qtwebengineprocess",
            "crashpad", "tor", "7z", "adb", "aapt", "zipalign", "notification_helper", "vc_redist", "draveos")
SKIP = {"_internal", "build", ".venv", "venv", ".build-venv", "__pycache__", "node_modules", ".git",
        "site-packages", "cache", "temp", "tmp", "tempy", "test", "tests", "logs", "_kan_weg", "oud", "backup", "backups", "back-ups"}


def cat_naam(c):
    return (c if NL else CAT_EN.get(c, c)).replace("&", "&&")


def kort(naam):
    """Label onder een pictogram: 'DraveShopBuddy' -> 'ShopBuddy' (de volle naam staat in de tooltip)."""
    if naam.lower().startswith("drave") and len(naam) > 5:
        return naam[5:]
    return naam


def zoek_apps(mappen, verborgen):
    """Zoekt .exe-bestanden van apps in de mappen (max. 6 diep). Per naam de nieuwste, liefst uit een dist-map."""
    gevonden = {}
    for root in mappen:
        if not root or not os.path.isdir(root):
            continue
        basis = root.rstrip("\\/").count(os.sep)
        for d, subs, files in os.walk(root):
            diep = d.count(os.sep) - basis
            subs[:] = [s for s in subs if s.lower() not in SKIP and not s.startswith(".")
                       and not s.lower().endswith(("-data", "_data")) and diep < 6]
            for f in files:
                if not f.lower().endswith(".exe"):
                    continue
                stam = f[:-4]
                ls = stam.lower()
                if any(ls.startswith(n) for n in NIET_APP) or ls in {v.lower() for v in verborgen} \
                        or ls.endswith(("_setup", "-setup", " setup")):
                    continue
                p = os.path.join(d, f)
                try:
                    t = os.path.getmtime(p)
                except OSError:
                    continue
                in_dist = (os.sep + "dist") in d.lower() + os.sep
                score = (1 if in_dist else 0, t)
                oud = gevonden.get(ls)
                if oud is None or score > oud["score"]:
                    gevonden[ls] = {"naam": stam, "pad": p, "score": score, "cat": _cat_van(p, root, ls)}
    apps = list(gevonden.values())
    apps.sort(key=lambda a: a["naam"].lower())
    return apps


def _cat_van(pad, root, ls):
    rel = os.path.relpath(pad, root).replace("\\", "/").lower().split("/")
    for c in CATEGORIEEN:
        if c.lower() in rel:
            return c
    if "mobiel" in rel:
        return "Mobiel"
    return BEKEND.get(ls, "Overig")


_ICOON_CACHE = {}


def _grootste(icoon):
    maten = icoon.availableSizes()
    return max((m.width() for m in maten), default=0)


def app_icoon(pad):
    """Mooi groot pictogram: eerst een plaatje uit de assets-map, anders het pictogram uit de .exe zelf
    op 256 px (Windows geeft standaard maar 32 px: dan zie je een piepklein icoontje)."""
    if pad in _ICOON_CACHE:
        return _ICOON_CACHE[pad]
    d = os.path.dirname(pad)
    beste, beste_maat = None, 0
    for kand in (os.path.join(d, "assets", "icon.png"), os.path.join(d, "assets", "icon-256.png"),
                 os.path.join(d, "assets", "logo.png"), os.path.join(d, "assets", "icon.ico"),
                 os.path.join(d, "icon.png"), os.path.join(d, "logo.png"), os.path.join(d, "icon.ico")):
        if os.path.exists(kand):
            i = QIcon(kand)
            if not i.isNull():
                m = _grootste(i) or QPixmap(kand).width()
                if m > beste_maat:
                    beste, beste_maat = i, m
    if beste_maat < 64:
        r = vw.exe_icoon(pad, 256)
        if r:
            data, maat, alpha = r
            fmt = QImage.Format.Format_ARGB32_Premultiplied if alpha else QImage.Format.Format_RGB32
            img = QImage(data, maat, maat, fmt).copy()
            if not img.isNull():
                beste, beste_maat = QIcon(QPixmap.fromImage(img)), maat
    if beste is None:
        beste = QFileIconProvider().icon(QFileInfo(pad))
    elif beste_maat and beste_maat < 64:
        # klein plaatje: netjes opschalen zodat het niet piepklein in de hoek staat
        pm = beste.pixmap(QSize(beste_maat, beste_maat)).scaled(
            64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        beste = QIcon(pm)
    _ICOON_CACHE[pad] = beste
    return beste


# ------------------------------------------------------------------ kleuren
BG = "#16131f"
PANEEL = "#1f1a2c"
KAART = "#2a2340"
RAND = "#4a3d66"
ACCENT = "#7F77DD"
LICHT = "#b59cff"
TEKST = "#efeaff"
SUB = "#b8afd6"
GOUD = "#ffc857"


def stijl(schaal):
    f = lambda px: int(px * schaal)
    return """
* { font-family: 'Segoe UI', Arial; font-size: %(f15)dpx; color: %(t)s; }
QMainWindow { background: %(bg)s; }
QFrame#taakbalk { background: rgba(22,19,31,235); border-top: 2px solid %(r)s; }
QLabel#klok { font-size: %(f16)dpx; font-weight: 700; color: white; }
QLabel#datum { font-size: %(f12)dpx; color: %(s)s; }
QPushButton#taak { background: %(k)s; border: 2px solid %(r)s; border-radius: 8px; padding: 3px 10px;
                   font-size: %(f14)dpx; text-align: left; }
QPushButton#klein { background: transparent; border: 1px solid %(r)s; border-radius: 8px; padding: 3px 10px;
                    font-size: %(f13)dpx; }
QPushButton#klein:hover { border-color: %(l)s; }
QPushButton#taak:checked { background: %(a)s; border-color: %(l)s; color: white; }
QPushButton#taak:hover { border-color: %(l)s; }
QPushButton#start { background: %(a)s; border: none; border-radius: 10px; padding: 4px 14px;
                    font-size: %(f16)dpx; font-weight: 800; color: white; }
QPushButton#start:hover, QPushButton#start:checked { background: %(l)s; color: %(bg)s; }
QFrame#menu { background: rgba(31,26,44,248); border: 2px solid %(l)s; border-radius: 18px; }
QLineEdit { background: %(k)s; border: 2px solid %(r)s; border-radius: 12px; padding: 10px 14px; font-size: %(f17)dpx; }
QLineEdit:focus { border-color: %(l)s; }
QPushButton#cat { background: transparent; border: none; border-radius: 10px; padding: 10px 14px;
                  text-align: left; font-size: %(f17)dpx; font-weight: 600; }
QPushButton#cat:hover { background: %(k)s; }
QPushButton#cat:checked { background: %(a)s; color: white; }
QToolButton#app { background: transparent; border: 2px solid transparent; border-radius: 12px; padding: 6px;
                  font-size: %(f14)dpx; }
QToolButton#app:hover { background: %(k)s; border-color: %(r)s; }
QToolButton#bureau { background: transparent; border: 2px solid transparent; border-radius: 12px; padding: 6px;
                     font-size: %(f14)dpx; color: white; }
QToolButton#bureau:hover { background: rgba(127,119,221,90); border-color: %(l)s; }
QPushButton#onder { background: %(k)s; border: 2px solid %(r)s; border-radius: 12px; padding: 10px 16px;
                    font-size: %(f16)dpx; font-weight: 600; }
QPushButton#onder:hover { border-color: %(l)s; }
QPushButton#uit { background: #8a2c45; border: none; border-radius: 12px; padding: 10px 18px;
                  font-size: %(f16)dpx; font-weight: 700; color: white; }
QPushButton#uit:hover { background: #c23b5c; }
QMdiSubWindow { background: transparent; border: none; }
QFrame#appkader { background: %(p)s; border: 2px solid %(l)s; border-radius: 6px; }
QFrame#titelbalk { background: %(k)s; border: none; border-bottom: 1px solid %(r)s; }
QLabel#titelnaam { font-size: %(f15)dpx; font-weight: 700; color: white; }
QPushButton#tknop { background: transparent; border: none; border-radius: 6px; font-size: %(f17)dpx; color: white; padding: 0; }
QPushButton#tknop:hover { background: %(r)s; }
QPushButton#tsluit { background: transparent; border: none; border-radius: 6px; font-size: %(f17)dpx; color: white; padding: 0; }
QPushButton#tsluit:hover { background: #c23b5c; }
QPushButton { background: %(k)s; border: 2px solid %(r)s; border-radius: 10px; padding: 8px 14px; }
QPushButton:hover { border-color: %(l)s; }
QDialog { background: %(p)s; }
QListWidget, QComboBox { background: %(k)s; border: 2px solid %(r)s; border-radius: 8px; padding: 4px; }
QScrollArea { border: none; background: transparent; }
QWidget#appsvlak { background: transparent; }
QMenu { background: %(p)s; border: 2px solid %(r)s; padding: 6px; }
QMenu::item { padding: 8px 20px; }
QMenu::item:selected { background: %(a)s; }
QCheckBox { spacing: 10px; }
""" % {"bg": BG, "p": PANEEL, "k": KAART, "r": RAND, "a": ACCENT, "l": LICHT, "t": TEKST, "s": SUB,
       "f12": f(12), "f13": f(13), "f14": f(14), "f15": f(15), "f16": f(16), "f17": f(17), "f20": f(20), "f26": f(26)}


def _lees(p, std):
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
            if isinstance(std, dict):
                std = dict(std)
                std.update(d)
                return std
            return d
    except Exception:
        return std


def _schrijf(p, d):
    try:
        with open(p + ".tmp", "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(p + ".tmp", p)
    except Exception as e:
        _log("opslaan: %s" % e)


STANDAARD = {"volledig": True, "mappen": [], "verborgen": [], "bureaublad": [], "achtergrond": "paars",
             "foto": "", "passen": "vullen", "logo": True, "schaal": 1.15}


ACHTERGRONDEN = [("paars", "a_paars"), ("nacht", "a_nacht"), ("bos", "a_bos"), ("zon", "a_zon"),
                 ("grijs", "a_grijs"), ("foto", "a_foto"), ("windows", "a_windows")]
KLEUREN = {"paars": ("#2b2147", "#120f1a", "#7F77DD"), "nacht": ("#14264a", "#070b16", "#5aa6e0"),
           "bos": ("#173a2a", "#07130c", "#5fd38d"), "zon": ("#5a2a3a", "#160a12", "#ff9f6b"),
           "grijs": ("#33333b", "#111114", "#c9c9d6")}
PASSEN = [("vullen", "b_vullen"), ("passend", "b_passend"), ("rekken", "b_rekken"), ("midden", "b_midden")]


def kies_eigen_foto(ouder, instel):
    """Foto kiezen en een kopie in DraveOS-data zetten (blijft werken als het origineel verhuist)."""
    import shutil
    p, _ = QFileDialog.getOpenFileName(ouder, T("i_foto"), os.path.expanduser("~"),
                                       "Foto (*.png *.jpg *.jpeg *.bmp *.webp *.gif)")
    if not p:
        return False
    doel = os.path.join(DATA, "achtergrond" + os.path.splitext(p)[1].lower())
    try:
        for f in os.listdir(DATA):
            if f.startswith("achtergrond.") and os.path.join(DATA, f) != doel:
                os.remove(os.path.join(DATA, f))
        shutil.copy2(p, doel)
    except Exception as e:
        _log("foto kopieren: %s" % e)
        doel = p
    instel["foto"] = doel
    instel["achtergrond"] = "foto"
    return True


# ------------------------------------------------------------------ bureaublad (achtergrond + pictogrammen)
class Bureaublad(QMdiArea):
    def __init__(self, os_):
        super().__init__()
        self.os = os_
        self.logo = QPixmap(_res("assets", "icon.png"))
        self.foto = None
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.iconen = QWidget(self.viewport())
        self.iconen.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.raster = QGridLayout(self.iconen)
        self.raster.setContentsMargins(20, 20, 20, 20)
        self.raster.setSpacing(10)
        self.raster.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.iconen.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.iconen.customContextMenuRequested.connect(lambda p: self.os.bureau_menu(self.iconen.mapToGlobal(p)))
        self.hint = QLabel(T("bureau_hint"), self.viewport())
        self.hint.setStyleSheet("color: rgba(239,234,255,140); font-size: 15px;")
        self.zet_achtergrond()

    def zet_achtergrond(self):
        a = self.os.instel.get("achtergrond", "paars")
        self.foto = None
        pad = self.os.instel.get("foto") if a == "foto" else (vw.windows_achtergrond() if a == "windows" else "")
        if pad and os.path.exists(pad):
            self.foto = QPixmap(pad)
        self.viewport().update()

    def vul_iconen(self, apps):
        while self.raster.count():
            w = self.raster.takeAt(0).widget()
            if w:
                w.deleteLater()
        namen = self.os.instel.get("bureaublad", [])
        per = {a["naam"].lower(): a for a in apps}
        rij = kol = 0
        hoogte = max(1, (self.viewport().height() - 40) // 130)
        n = 0
        for naam in namen:
            a = per.get(naam.lower())
            if not a:
                continue
            b = QToolButton()
            b.setObjectName("bureau")
            b.setIcon(app_icoon(a["pad"]))
            b.setIconSize(QSize(64, 64))
            b.setText(kort(a["naam"]))
            b.setToolTip(a["naam"])
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            b.setFixedSize(118, 118)
            b.clicked.connect(lambda _=False, a=a: self.os.start_app(a))
            b.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            b.customContextMenuRequested.connect(lambda _p, a=a, b=b: self.os.app_menu(a, b))
            self.raster.addWidget(b, rij, kol)
            n += 1
            rij += 1
            if rij >= hoogte:
                rij, kol = 0, kol + 1
        self.hint.setVisible(n == 0)
        self._plaats()

    def _plaats(self):
        self.iconen.setGeometry(self.viewport().rect())
        self.iconen.lower()
        self.hint.adjustSize()
        self.hint.move(24, 24)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._plaats()

    def paintEvent(self, e):
        p = QPainter(self.viewport())
        r = self.viewport().rect()
        a = self.os.instel.get("achtergrond", "paars")
        if self.foto and not self.foto.isNull():
            p.fillRect(r, QColor("#000000"))
            m = self.os.instel.get("passen", "vullen")
            if m == "midden":
                pm = self.foto
            elif m == "rekken":
                pm = self.foto.scaled(r.size(), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
            else:
                modus = Qt.AspectRatioMode.KeepAspectRatio if m == "passend" else Qt.AspectRatioMode.KeepAspectRatioByExpanding
                pm = self.foto.scaled(r.size(), modus, Qt.TransformationMode.SmoothTransformation)
            p.drawPixmap((r.width() - pm.width()) // 2, (r.height() - pm.height()) // 2, pm)
            return
        kleuren = KLEUREN.get(a, KLEUREN["paars"])
        g = QRadialGradient(QPointF(r.width() * 0.55, r.height() * 0.45), max(r.width(), r.height()) * 0.75)
        g.setColorAt(0, QColor(kleuren[0]))
        g.setColorAt(1, QColor(kleuren[1]))
        p.fillRect(r, g)
        if not self.os.instel.get("logo", True):
            return
        if not self.logo.isNull():
            s = int(min(r.width(), r.height()) * 0.34)
            pm = self.logo.scaled(s, s, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            p.setOpacity(0.16)
            p.drawPixmap((r.width() - pm.width()) // 2, int(r.height() * 0.42 - pm.height() / 2), pm)
            p.setOpacity(0.35)
        p.setPen(QColor(kleuren[2]))
        p.setFont(QFont("Segoe UI", max(18, r.height() // 22), QFont.Weight.Black))
        p.drawText(QRectF(0, r.height() * 0.62, r.width(), r.height() * 0.1), Qt.AlignmentFlag.AlignCenter, "DraveOS")


# ------------------------------------------------------------------ app-venster (ingebed)
class TitelBalk(QFrame):
    """Eigen titelbalk boven een app: icoon, naam en grote knoppen  —  ☐  ✕.
    Slepen = venster verplaatsen, dubbelklik = maximaliseren/terug."""

    def __init__(self, venster):
        super().__init__()
        self.v = venster
        self.setObjectName("titelbalk")
        self.setFixedHeight(40)
        h = QHBoxLayout(self)
        h.setContentsMargins(10, 0, 4, 0)
        h.setSpacing(4)
        ico = QLabel()
        ico.setPixmap(app_icoon(venster.app["pad"]).pixmap(24, 24))
        h.addWidget(ico)
        self.naam = QLabel(venster.app["naam"])
        self.naam.setObjectName("titelnaam")
        h.addWidget(self.naam, 1)
        for tekst, tip, f, naam in (("—", "Minimaliseren", venster.minimaliseer, "tknop"),
                                     ("☐", "Maximaliseren", venster.wissel_max, "tknop"),
                                     ("✕", "Sluiten", venster.close, "tsluit")):
            k = QPushButton(tekst)
            k.setObjectName(naam)
            k.setToolTip(tip)
            k.setFixedSize(48, 34)
            k.setCursor(Qt.CursorShape.PointingHandCursor)
            k.clicked.connect(f)
            h.addWidget(k)
        self._van = None

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.v.os.naar_voren(self.v)
            self._van = e.globalPosition().toPoint() - self.v.pos()

    def mouseMoveEvent(self, e):
        if self._van is not None and not self.v.max_aan:
            self.v.move(e.globalPosition().toPoint() - self._van)

    def mouseReleaseEvent(self, e):
        self._van = None

    def mouseDoubleClickEvent(self, e):
        self.v.wissel_max()


class AppVenster(QMdiSubWindow):
    gesloten = pyqtSignal(object)

    def __init__(self, os_, app, proc, hwnd):
        super().__init__()
        self.os, self.app, self.proc, self.hwnd = os_, app, proc, hwnd
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle(app["naam"])
        self.setWindowIcon(app_icoon(app["pad"]))
        self.max_aan, self.oud = False, None
        self.stijlen = vw.kaal_maken(hwnd)
        self.qwin = QWindow.fromWinId(int(hwnd))
        self.houder = QWidget.createWindowContainer(self.qwin)
        self.houder.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        binnen = QFrame()
        binnen.setObjectName("appkader")
        v = QVBoxLayout(binnen)
        v.setContentsMargins(2, 0, 2, 2)
        v.setSpacing(0)
        self.titel = TitelBalk(self)
        v.addWidget(self.titel)
        v.addWidget(self.houder, 1)
        onder = QHBoxLayout()
        onder.setContentsMargins(0, 0, 0, 0)
        onder.addStretch()
        grip = QSizeGrip(binnen)
        grip.setFixedSize(18, 18)
        onder.addWidget(grip)
        v.addLayout(onder)
        self.setWidget(binnen)
        self.vrij = False
        self.sluit_om = None
        self.weg_tel = 0
        self.wacht = QTimer(self)
        self.wacht.timeout.connect(self._controle)
        self.wacht.start(1000)

    def minimaliseer(self):
        self.hide()
        self.os.taak_status()

    def herstel(self):
        self.show()
        self.os.naar_voren(self)

    def wissel_max(self):
        if self.max_aan:
            self.max_aan = False
            if self.oud:
                self.setGeometry(self.oud)
        else:
            self.oud = self.geometry()
            self.max_aan = True
            self.setGeometry(self.os.bureau.viewport().rect())
        self.os.naar_voren(self)

    def _controle(self):
        if not vw.bestaat(self.hwnd):
            self._klaar()
            return
        if self.sluit_om is None:
            # de app verstopte zichzelf (bv. 'sluiten naar systeemvak') terwijl wij hem tonen: dan echt sluiten
            if self.isVisible() and not vw.zichtbaar(self.hwnd):
                self.weg_tel += 1
                if self.weg_tel >= 3:
                    self.stop_hard()
            else:
                self.weg_tel = 0
            return
        # we vroegen de app om te sluiten
        wacht = (datetime.datetime.now() - self.sluit_om).total_seconds()
        pids = vw.proces_familie(self.proc.pid) if self.proc else set()
        if self.proc is not None and self.proc.poll() is not None and not (pids - {self.proc.pid}):
            self._klaar()
            return
        if wacht < 2.5:
            return
        if pids and vw.heeft_dialoog(pids):
            return                       # de app vraagt iets (bv. opslaan): laat de gebruiker antwoorden
        # venster is weg/verborgen (bv. naar het systeemvak) maar het proces draait nog: echt stoppen
        if self.proc is not None:
            vw.stop_proces(self.proc.pid)
        self._klaar()

    def _klaar(self):
        self.wacht.stop()
        self.vrij = True
        self.close()

    def sluit_verzoek(self):
        if self.sluit_om is None:
            self.sluit_om = datetime.datetime.now()
            vw.sluit(self.hwnd)
            self.wacht.start(500)

    def heeft_vraag(self):
        pids = vw.proces_familie(self.proc.pid) if self.proc else set()
        return bool(pids) and vw.heeft_dialoog(pids)

    def stop_hard(self):
        if self.proc is not None:
            vw.stop_proces(self.proc.pid)
        self._klaar()

    def closeEvent(self, e):
        if not self.vrij and vw.bestaat(self.hwnd):
            # eerst netjes vragen (dan kan de app nog opslaan); lukt dat niet, dan stoppen we hem
            self.sluit_verzoek()
            self.hide()
            self.os.taak_status()
            e.ignore()
            return
        self.wacht.stop()
        self.gesloten.emit(self)
        super().closeEvent(e)

    def laat_vrij(self):
        if vw.bestaat(self.hwnd):
            try:
                self.qwin.setParent(None)
            except Exception:
                pass
            vw.vrijlaten(self.hwnd, *self.stijlen)
        self.vrij = True
        self.close()


# ------------------------------------------------------------------ het menu
class Menu(QFrame):
    """Het menu is een eigen pop-upvenster, zodat het altijd BOVEN de ingebedde apps ligt.
    Klik je ernaast, dan gaat het vanzelf dicht (zoals bij Windows)."""

    def __init__(self, os_):
        super().__init__(os_, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.os = os_
        self.dicht_om = 0.0
        self.setObjectName("menu")
        self.cat = None
        v = QVBoxLayout(self)
        v.setContentsMargins(18, 18, 18, 16)
        v.setSpacing(12)
        kop = QHBoxLayout()
        logo = QLabel()
        pm = QPixmap(_res("assets", "icon.png"))
        if not pm.isNull():
            logo.setPixmap(pm.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        kop.addWidget(logo)
        titel = QLabel("<span style='font-size:24px;font-weight:800;color:%s'>DraveOS</span>" % LICHT)
        kop.addWidget(titel)
        kop.addSpacing(10)
        self.zoek = QLineEdit()
        self.zoek.setPlaceholderText(T("zoek"))
        self.zoek.textChanged.connect(self.toon_apps)
        self.zoek.returnPressed.connect(self._start_eerste)
        kop.addWidget(self.zoek, 1)
        v.addLayout(kop)

        mid = QHBoxLayout()
        mid.setSpacing(14)
        self.catv = QVBoxLayout()
        self.catv.setSpacing(4)
        self.catknoppen = {}
        for c in [None] + CATEGORIEEN:
            b = QPushButton(("📋  " + T("alle")) if c is None else "%s  %s" % (CAT_ICOON[c], cat_naam(c)))
            b.setObjectName("cat")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, c=c: self.kies_cat(c))
            self.catv.addWidget(b)
            self.catknoppen[c] = b
        self.catv.addStretch()
        mid.addLayout(self.catv)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.vlak = QWidget()
        self.vlak.setObjectName("appsvlak")
        self.raster = QGridLayout(self.vlak)
        self.raster.setSpacing(6)
        self.raster.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.scroll.setWidget(self.vlak)
        mid.addWidget(self.scroll, 1)
        v.addLayout(mid, 1)

        onder = QHBoxLayout()
        for tekst, f in ((T("instel"), self.os.instellingen), (T("doneer"), self.os.doneer),
                         (T("gids"), self.os.snelgids), (T("over"), self.os.over)):
            b = QPushButton(tekst)
            b.setObjectName("onder")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, f=f: (self.hide(), f()))
            onder.addWidget(b)
        onder.addStretch()
        uit = QPushButton(T("uit"))
        uit.setObjectName("uit")
        uit.setCursor(Qt.CursorShape.PointingHandCursor)
        uit.clicked.connect(lambda: (self.hide(), self.os.afsluiten()))
        onder.addWidget(uit)
        v.addLayout(onder)
        self.hide()

    def kies_cat(self, c):
        self.cat = c
        for k, b in self.catknoppen.items():
            b.setChecked(k == c)
        self.toon_apps()

    def _apps_nu(self):
        q = self.zoek.text().strip().lower()
        apps = self.os.apps
        if q:
            return [a for a in apps if q in a["naam"].lower()]
        if self.cat:
            return [a for a in apps if a["cat"] == self.cat]
        return apps

    def toon_apps(self):
        while self.raster.count():
            w = self.raster.takeAt(0).widget()
            if w:
                w.deleteLater()
        apps = self._apps_nu()
        if not apps:
            lab = QLabel(T("geen_apps") if not self.os.apps else "—")
            lab.setStyleSheet("color: %s; font-size: 17px; padding: 20px;" % SUB)
            self.raster.addWidget(lab, 0, 0)
            return
        kolommen = max(3, (self.scroll.viewport().width() - 10) // 136)
        for i, a in enumerate(apps):
            b = QToolButton()
            b.setObjectName("app")
            b.setIcon(app_icoon(a["pad"]))
            b.setIconSize(QSize(56, 56))
            b.setText(kort(a["naam"]))
            b.setToolTip("%s  ·  %s" % (a["naam"], cat_naam(a["cat"])))
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            b.setFixedSize(128, 112)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, a=a: (self.hide(), self.os.start_app(a)))
            b.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            b.customContextMenuRequested.connect(lambda _p, a=a, b=b: self.os.app_menu(a, b))
            self.raster.addWidget(b, i // kolommen, i % kolommen)

    def _start_eerste(self):
        apps = self._apps_nu()
        if apps:
            self.hide()
            self.os.start_app(apps[0])

    def open(self):
        p = self.os
        b = min(1080, p.width() - 40)
        h = min(760, p.height() - self.os.taakbalk.height() - 40)
        linksboven = p.mapToGlobal(p.rect().topLeft())
        self.setGeometry(linksboven.x() + 8,
                         linksboven.y() + p.height() - self.os.taakbalk.height() - h - 12, b, h)
        self.zoek.clear()
        self.kies_cat(self.cat)
        self.show()
        self.raise_()
        self.zoek.setFocus()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.hide()
            self.os.startknop.setChecked(False)
        else:
            super().keyPressEvent(e)

    def hideEvent(self, e):
        import time
        self.dicht_om = time.monotonic()
        try:
            self.os.startknop.setChecked(False)
        except Exception:
            pass
        super().hideEvent(e)


# ------------------------------------------------------------------ apps zoeken op de achtergrond
class Zoeker(QObject):
    klaar = pyqtSignal(list)

    def start(self, mappen, verborgen):
        def werk():
            try:
                r = zoek_apps(mappen, verborgen)
            except Exception as e:
                _log("zoeken: %s" % e)
                r = []
            self.klaar.emit(r)
        threading.Thread(target=werk, daemon=True).start()


# ------------------------------------------------------------------ hoofdvenster
class DraveOS(QMainWindow):
    def __init__(self):
        super().__init__()
        self.instel = _lees(INSTEL, STANDAARD)
        if not self.instel.get("mappen"):
            # eerste keer: de map waar DraveOS staat en de map daarboven
            self.instel["mappen"] = [os.path.dirname(_base())]
        self.apps, self.vensters, self.taakknoppen = [], [], {}
        self.wachtrij = []
        self.setWindowTitle("DraveOS")
        ico = _res("assets", "icon.ico")
        if os.path.exists(ico):
            self.setWindowIcon(QIcon(ico))
        self.zoeker = Zoeker()
        self.zoeker.klaar.connect(self._apps_klaar)
        self._bouw()
        self.menu = Menu(self)
        QShortcut(QKeySequence("F11"), self, activated=self.wissel_scherm)
        QShortcut(QKeySequence("Ctrl+Esc"), self, activated=self.wissel_menu)
        self.klok = QTimer(self)
        self.klok.timeout.connect(self._tik)
        self.klok.start(1000)
        self._tik()
        # klik je IN een app, dan komt zijn venster vooraan (Qt ziet die klik zelf niet)
        self.focustimer = QTimer(self)
        self.focustimer.timeout.connect(self._volg_focus)
        self.focustimer.start(300)
        self.herlaad_apps()

    def _bouw(self):
        w = QWidget()
        self.setCentralWidget(w)
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        self.bureau = Bureaublad(self)
        self.bureau.subWindowActivated.connect(self._actief)
        v.addWidget(self.bureau, 1)
        self.taakbalk = QFrame()
        self.taakbalk.setObjectName("taakbalk")
        self.taakbalk.setFixedHeight(int(50 * self.instel.get("schaal", 1.15)))
        h = QHBoxLayout(self.taakbalk)
        h.setContentsMargins(6, 3, 10, 3)
        h.setSpacing(6)
        # links: de menuknop (zoals de startknop van Windows)
        self.startknop = QPushButton(" " + T("menu"))
        self.startknop.setObjectName("start")
        self.startknop.setCheckable(True)
        pm = QPixmap(_res("assets", "icon.png"))
        if not pm.isNull():
            self.startknop.setIcon(QIcon(pm))
            self.startknop.setIconSize(QSize(26, 26))
        self.startknop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.startknop.clicked.connect(self.wissel_menu)
        h.addWidget(self.startknop)
        h.addSpacing(8)
        # midden: de open apps
        self.takenv = QHBoxLayout()
        self.takenv.setSpacing(4)
        h.addLayout(self.takenv)
        h.addStretch(1)
        # rechts: volledig scherm + tijd en datum
        self.schermknop = QPushButton()
        self.schermknop.setObjectName("klein")
        self.schermknop.setToolTip("F11")
        self.schermknop.clicked.connect(self.wissel_scherm)
        h.addWidget(self.schermknop)
        h.addSpacing(8)
        tijd = QVBoxLayout()
        tijd.setSpacing(0)
        self.klokl = QLabel()
        self.klokl.setObjectName("klok")
        self.klokl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.datuml = QLabel()
        self.datuml.setObjectName("datum")
        self.datuml.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tijd.addWidget(self.klokl)
        tijd.addWidget(self.datuml)
        h.addLayout(tijd)
        v.addWidget(self.taakbalk)
        self._zet_schermknop()

    # ---------------------------------------------------------- klok / scherm
    def _tik(self):
        nu = datetime.datetime.now()
        self.klokl.setText(nu.strftime("%H:%M"))
        dagen = ["ma", "di", "wo", "do", "vr", "za", "zo"] if NL else ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        maanden = (["jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"] if NL else
                   ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
        self.datuml.setText("%s %d %s %d" % (dagen[nu.weekday()], nu.day, maanden[nu.month - 1], nu.year))

    def wissel_scherm(self):
        if self.isFullScreen():
            self.showNormal()
            self.showMaximized()
        else:
            self.showFullScreen()
        QTimer.singleShot(200, self._zet_schermknop)

    def _zet_schermknop(self):
        self.schermknop.setText("🗗  " + T("vol_uit") if self.isFullScreen() else "⛶  " + T("vol_aan"))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.menu.isVisible():
            self.menu.open()
        QTimer.singleShot(50, lambda: self.bureau.vul_iconen(self.apps))

    # ---------------------------------------------------------- apps
    def herlaad_apps(self):
        self.zoeker.start(list(self.instel.get("mappen", [])), list(self.instel.get("verborgen", [])))

    def _apps_klaar(self, apps):
        self.apps = apps
        self.bureau.vul_iconen(apps)
        if self.menu.isVisible():
            self.menu.toon_apps()

    def wissel_menu(self):
        import time
        if self.menu.isVisible():
            self.menu.hide()
        elif time.monotonic() - self.menu.dicht_om < 0.3:
            # de klik op de menuknop sloot het pop-upmenu al; niet meteen weer openen
            self.startknop.setChecked(False)
        else:
            self.startknop.setChecked(True)
            self.menu.open()

    def start_app(self, a, buiten=False):
        try:
            proc = subprocess.Popen([a["pad"]], cwd=os.path.dirname(a["pad"]))
        except Exception as e:
            _log("start %s: %s" % (a["naam"], e))
            self.melding(T("kon_niet") % a["naam"])
            return
        if buiten:
            return
        self.melding(T("starten") % a["naam"], 4000)
        bekend = {v.hwnd for v in self.vensters}
        self.wachtrij.append({"app": a, "proc": proc, "tot": datetime.datetime.now() + datetime.timedelta(seconds=60),
                              "negeer": bekend, "gezien": None, "sinds": None})
        if not getattr(self, "_zoektimer", None):
            self._zoektimer = QTimer(self)
            self._zoektimer.timeout.connect(self._zoek_vensters)
        if not self._zoektimer.isActive():
            self._zoektimer.start(400)

    def _zoek_vensters(self):
        nu = datetime.datetime.now()
        for w in list(self.wachtrij):
            pids = vw.proces_familie(w["proc"].pid)
            hwnd = vw.hoofdvenster(pids, w["negeer"] | {v.hwnd for v in self.vensters})
            if hwnd:
                # wacht tot het venster ~1 s hetzelfde is (eerst komt soms een opstartschermpje)
                if hwnd != w["gezien"]:
                    w["gezien"], w["sinds"] = hwnd, nu
                elif (nu - w["sinds"]).total_seconds() >= 1.0:
                    self.wachtrij.remove(w)
                    self._inbedden(w["app"], w["proc"], hwnd)
                    continue
            if nu > w["tot"] or (w["proc"].poll() is not None and not pids - {w["proc"].pid}):
                self.wachtrij.remove(w)
                if w["proc"].poll() is None or nu > w["tot"]:
                    self.melding(T("geen_venster") % w["app"]["naam"], 9000)
        if not self.wachtrij:
            self._zoektimer.stop()

    def _inbedden(self, a, proc, hwnd):
        try:
            sub = AppVenster(self, a, proc, hwnd)
        except Exception:
            _log("inbedden %s: %s" % (a["naam"], traceback.format_exc()))
            self.melding(T("kon_niet") % a["naam"])
            return
        sub.gesloten.connect(self._venster_weg)
        self.bureau.addSubWindow(sub)
        b, h = vw.grootte(hwnd)
        vr = self.bureau.viewport().rect()
        b = min(max(b, 700), vr.width() - 40)
        h = min(max(h, 500), vr.height() - 80)
        n = len(self.vensters)
        sub.setGeometry(40 + (n % 6) * 36, 30 + (n % 6) * 30, b, h + 32)
        sub.show()
        self.vensters.append(sub)
        knop = QPushButton("  " + a["naam"])
        knop.setObjectName("taak")
        knop.setIcon(app_icoon(a["pad"]))
        knop.setIconSize(QSize(22, 22))
        knop.setCheckable(True)
        knop.setCursor(Qt.CursorShape.PointingHandCursor)
        knop.clicked.connect(lambda _=False, s=sub: self._taak_klik(s))
        self.takenv.addWidget(knop)
        self.taakknoppen[sub] = knop
        self.naar_voren(sub)

    def _volg_focus(self):
        if not self.vensters:
            return
        f = vw.focus_venster()
        if not f:
            return
        for s in self.vensters:
            if vw.hoort_bij(s.hwnd, f):
                if getattr(self, "_voorste", None) is not s:
                    s.raise_()
                    self._voorste = s
                    self.taak_status()
                return

    def _taak_klik(self, s):
        """Zoals Windows: verborgen -> tevoorschijn; vooraan -> minimaliseren; anders -> naar voren."""
        if s.isHidden():
            s.herstel()
        elif getattr(self, "_voorste", None) is s:
            s.minimaliseer()
        else:
            self.naar_voren(s)

    def naar_voren(self, s):
        if s.isHidden():
            s.show()
        s.raise_()
        self.bureau.setActiveSubWindow(s)
        self._voorste = s
        s.houder.setFocus()
        self.taak_status()

    def taak_status(self):
        voor = getattr(self, "_voorste", None)
        if voor is not None and (voor not in self.vensters or voor.isHidden()):
            zicht = [v for v in self.vensters if not v.isHidden()]
            self._voorste = voor = zicht[-1] if zicht else None
        for k, b in self.taakknoppen.items():
            b.setChecked(k is voor and not k.isHidden())

    def _actief(self, s):
        if s is not None:
            self._voorste = s
        self.taak_status()

    def _venster_weg(self, s):
        if s in self.vensters:
            self.vensters.remove(s)
        b = self.taakknoppen.pop(s, None)
        if b:
            b.setParent(None)
            b.deleteLater()
        if getattr(self, "_voorste", None) is s:
            self._voorste = None
        self.taak_status()

    def app_menu(self, a, knop):
        m = QMenu(self)
        op = a["naam"].lower() in [n.lower() for n in self.instel.get("bureaublad", [])]
        acts = {
            m.addAction("▶  " + a["naam"]): lambda: self.start_app(a),
            m.addAction(T("buiten")): lambda: self.start_app(a, buiten=True),
            m.addAction(T("van_bureaublad") if op else T("op_bureaublad")): lambda: self._bureaublad(a, not op),
            m.addAction(T("map_open")): lambda: os.startfile(os.path.dirname(a["pad"])),
            m.addAction(T("verberg")): lambda: self._verberg(a),
        }
        k = m.exec(knop.mapToGlobal(knop.rect().center()))
        if k in acts:
            if self.menu.isVisible():
                self.menu.hide()
            acts[k]()

    def bureau_menu(self, pos):
        """Rechtsklik op het bureaublad: achtergrond kiezen (zoals bij Windows)."""
        m = QMenu(self)
        sub = m.addMenu(T("b_achter"))
        nu = self.instel.get("achtergrond", "paars")
        acties = {}
        for k, t in ACHTERGRONDEN:
            if k == "foto":
                continue
            a = sub.addAction(("●  " if k == nu else "     ") + T(t))
            acties[a] = ("thema", k)
        sub.addSeparator()
        a = sub.addAction(("●  " if nu == "foto" else "     ") + T("i_foto"))
        acties[a] = ("foto", None)
        sub.addSeparator()
        pn = self.instel.get("passen", "vullen")
        for k, t in PASSEN:
            a = sub.addAction(("●  " if k == pn else "     ") + T(t))
            acties[a] = ("passen", k)
        sub.addSeparator()
        a = sub.addAction(("✔  " if self.instel.get("logo", True) else "     ") + T("b_logo"))
        acties[a] = ("logo", None)
        m.addSeparator()
        a = m.addAction(T("b_instel"))
        acties[a] = ("instel", None)
        k = m.exec(pos)
        if k not in acties:
            return
        soort, waarde = acties[k]
        if soort == "thema":
            self.instel["achtergrond"] = waarde
        elif soort == "foto":
            if not kies_eigen_foto(self, self.instel):
                return
        elif soort == "passen":
            self.instel["passen"] = waarde
        elif soort == "logo":
            self.instel["logo"] = not self.instel.get("logo", True)
        elif soort == "instel":
            self.instellingen()
            return
        _schrijf(INSTEL, self.instel)
        self.bureau.zet_achtergrond()

    def _bureaublad(self, a, aan):
        lijst = [n for n in self.instel.get("bureaublad", []) if n.lower() != a["naam"].lower()]
        if aan:
            lijst.append(a["naam"])
        self.instel["bureaublad"] = lijst
        _schrijf(INSTEL, self.instel)
        self.bureau.vul_iconen(self.apps)

    def _verberg(self, a):
        v = self.instel.setdefault("verborgen", [])
        if a["naam"] not in v:
            v.append(a["naam"])
        _schrijf(INSTEL, self.instel)
        self.apps = [x for x in self.apps if x is not a]
        self.menu.toon_apps()
        self.bureau.vul_iconen(self.apps)

    # ---------------------------------------------------------- meldingen
    def melding(self, tekst, ms=6000):
        lab = getattr(self, "_melding", None)
        if lab is None:
            lab = QLabel(self, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
            lab.setWordWrap(True)
            lab.setStyleSheet("background: %s; border: 2px solid %s; border-radius: 14px; padding: 14px 18px;"
                              "font-size: 17px; color: white;" % (PANEEL, LICHT))
            self._melding = lab
            self._meldtimer = QTimer(self)
            self._meldtimer.setSingleShot(True)
            self._meldtimer.timeout.connect(lab.hide)
        lab.setText(tekst)
        lab.setFixedWidth(min(560, self.width() - 40))
        lab.adjustSize()
        lb = self.mapToGlobal(self.rect().topLeft())
        lab.move(lb.x() + self.width() - lab.width() - 20, lb.y() + self.height() - self.taakbalk.height() - lab.height() - 20)
        lab.show()
        lab.raise_()
        self._meldtimer.start(ms)

    # ---------------------------------------------------------- menu-onderdelen
    def doneer(self):
        webbrowser.open("https://paypal.me/roger076")

    def snelgids(self):
        pdf = _res("DraveOS-Snelgids.pdf")
        if os.path.exists(pdf):
            QDesktopServices.openUrl(QUrl.fromLocalFile(pdf))

    def over(self):
        QMessageBox.about(self, "DraveOS", T("over_tekst") % VERSIE)

    def instellingen(self):
        d = Instellingen(self)
        if d.exec() == QDialog.DialogCode.Accepted:
            _schrijf(INSTEL, self.instel)
            QApplication.instance().setStyleSheet(stijl(self.instel.get("schaal", 1.15)))
            self.bureau.zet_achtergrond()
            self.herlaad_apps()

    def afsluiten(self):
        if self.vensters:
            if QMessageBox.question(self, T("uit_titel"), T("uit_vraag")) != QMessageBox.StandardButton.Yes:
                return
            for s in list(self.vensters):
                s.sluit_verzoek()
            QTimer.singleShot(3500, self._echt_uit)
        else:
            self._echt_uit()

    def _echt_uit(self):
        vragen = [s for s in self.vensters if s.heeft_vraag()]
        if vragen:
            namen = ", ".join(s.app["naam"] for s in vragen)
            for s in vragen:
                s.herstel()
            if QMessageBox.question(self, T("uit_titel"), T("nog_vraag") % namen) != QMessageBox.StandardButton.Yes:
                return                   # niet afsluiten: eerst zelf antwoorden in die app
        for s in list(self.vensters):
            s.stop_hard()
        for w in self.wachtrij:          # apps die nog aan het opstarten waren
            vw.stop_proces(w["proc"].pid)
        self.wachtrij = []
        self._weg = True
        self.close()

    def closeEvent(self, e):
        if self.vensters and not getattr(self, "_weg", False):
            e.ignore()
            self.afsluiten()
            return
        _schrijf(INSTEL, self.instel)
        e.accept()
        QApplication.quit()


# ------------------------------------------------------------------ instellingen
class Instellingen(QDialog):
    def __init__(self, os_):
        super().__init__(os_)
        self.os = os_
        i = os_.instel
        self.setWindowTitle(T("i_titel"))
        self.setMinimumWidth(720)
        v = QVBoxLayout(self)
        v.setSpacing(10)
        self.vol = QCheckBox(T("i_vol_start"))
        self.vol.setChecked(i.get("volledig", True))
        v.addWidget(self.vol)
        rij = QHBoxLayout()
        rij.addWidget(QLabel(T("i_achter")))
        self.achter = QComboBox()
        for k, t in ACHTERGRONDEN:
            self.achter.addItem(T(t), k)
        self.achter.setCurrentIndex(max(0, self.achter.findData(i.get("achtergrond", "paars"))))
        rij.addWidget(self.achter)
        fb = QPushButton(T("i_foto"))
        fb.clicked.connect(self._foto)
        rij.addWidget(fb)
        rij.addStretch()
        v.addLayout(rij)
        rijf = QHBoxLayout()
        rijf.addWidget(QLabel(T("i_passen")))
        self.passen = QComboBox()
        for k, t in PASSEN:
            self.passen.addItem(T(t), k)
        self.passen.setCurrentIndex(max(0, self.passen.findData(i.get("passen", "vullen"))))
        rijf.addWidget(self.passen)
        self.logo = QCheckBox(T("b_logo"))
        self.logo.setChecked(i.get("logo", True))
        rijf.addWidget(self.logo)
        rijf.addStretch()
        v.addLayout(rijf)
        rij2 = QHBoxLayout()
        rij2.addWidget(QLabel(T("i_tekst")))
        self.schaal = QComboBox()
        for s, t in ((1.0, T("normaal")), (1.15, T("groot")), (1.35, T("extra"))):
            self.schaal.addItem(t, s)
        self.schaal.setCurrentIndex(max(0, self.schaal.findData(i.get("schaal", 1.15))))
        rij2.addWidget(self.schaal)
        rij2.addStretch()
        v.addLayout(rij2)
        v.addWidget(QLabel(T("i_mappen")))
        self.mappen = QListWidget()
        self.mappen.addItems(i.get("mappen", []))
        self.mappen.setMaximumHeight(130)
        v.addWidget(self.mappen)
        mk = QHBoxLayout()
        b1 = QPushButton(T("i_map_bij"))
        b1.clicked.connect(self._map_bij)
        b2 = QPushButton(T("i_map_weg"))
        b2.clicked.connect(lambda: self.mappen.takeItem(self.mappen.currentRow()))
        mk.addWidget(b1)
        mk.addWidget(b2)
        mk.addStretch()
        v.addLayout(mk)
        v.addWidget(QLabel(T("i_verborgen")))
        self.verborgen = QListWidget()
        self.verborgen.addItems(i.get("verborgen", []))
        self.verborgen.setMaximumHeight(130)
        self.verborgen.itemDoubleClicked.connect(lambda it: self.verborgen.takeItem(self.verborgen.row(it)))
        v.addWidget(self.verborgen)
        ok = QPushButton(T("i_ok"))
        ok.clicked.connect(self._ok)
        v.addWidget(ok)

    def _foto(self):
        if kies_eigen_foto(self, self.os.instel):
            self.achter.setCurrentIndex(self.achter.findData("foto"))

    def _map_bij(self):
        p = QFileDialog.getExistingDirectory(self, T("i_map_bij"))
        if p:
            self.mappen.addItem(os.path.normpath(p))

    def _ok(self):
        i = self.os.instel
        i["volledig"] = self.vol.isChecked()
        i["achtergrond"] = self.achter.currentData()
        i["passen"] = self.passen.currentData()
        i["logo"] = self.logo.isChecked()
        i["schaal"] = self.schaal.currentData()
        i["mappen"] = [self.mappen.item(k).text() for k in range(self.mappen.count())]
        i["verborgen"] = [self.verborgen.item(k).text() for k in range(self.verborgen.count())]
        self.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP)
    w0 = _lees(INSTEL, STANDAARD)
    app.setStyleSheet(stijl(w0.get("schaal", 1.15)))
    w = DraveOS()
    if w.instel.get("volledig", True):
        w.showFullScreen()
    else:
        w.showMaximized()
    QTimer.singleShot(300, w._zet_schermknop)
    try:
        import drave_update
        drave_update.start(w, APP, VERSIE)
    except Exception:
        pass
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
