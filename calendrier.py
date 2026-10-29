"""Calendrier Photo : crée un calendrier avec une photo par mois et l'exporte en PDF."""

import calendar
import datetime
import filecmp
import json
import os
import re
import sys
import tempfile

from PySide6.QtCore import (
    QDate, QLibraryInfo, QLocale, QMarginsF, QPointF, QRectF, QSettings, QSize, QStandardPaths, Qt, QTimer,
    QTranslator, Signal,
)
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QIcon,
    QImage,
    QImageIOHandler,
    QImageReader,
    QKeySequence,
    QLinearGradient,
    QPageLayout,
    QPageSize,
    QPainter,
    QPainterPath,
    QPdfWriter,
    QPen,
    QPixmap,
)
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QMenu,
    QScrollArea,
    QSlider,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "Calendrier Photo"
APP_VERSION = "1.2"
APP_DATE = "29 octobre 2026"
APP_AUTHOR = "Claude Code"
APP_AUTHOR_MODEL = "Claude Opus 5.5 (révision claude-opus-5-5)"
APP_DIRECTOR = "Yannick Buchet"

MONTHS = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
]
DAYS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff")
IMAGE_FILTER = "Images (" + " ".join("*" + ext for ext in IMAGE_EXTENSIONS) + ")"

# Formats de page : (libellé, format Qt, paysage)
FORMATS = [
    ("A4 portrait", QPageSize.PageSizeId.A4, False),
    ("A4 paysage", QPageSize.PageSizeId.A4, True),
    ("A3 portrait", QPageSize.PageSizeId.A3, False),
    ("A3 paysage", QPageSize.PageSizeId.A3, True),
]

# Styles de police : (libellé, famille)
FONTS = [
    ("Moderne", "Segoe UI"),
    ("Élégant", "Georgia"),
    ("Manuscrit", "Segoe Script"),
]

EXPORT_DPI = 300

MAX_SLOTS = 4  # photos par page au plus
# Dispositions : nombre de photos -> libellé, et nom de chaque emplacement.
LAYOUT_NAMES = {
    1: "1 photo (paysage)",
    2: "2 photos côte à côte (portrait)",
    3: "3 photos (une grande, deux petites)",
    4: "4 photos (mosaïque)",
}
SLOT_NAMES = {
    1: ["photo"],
    2: ["gauche", "droite"],
    3: ["grande, à gauche", "en haut à droite", "en bas à droite"],
    4: ["en haut à gauche", "en haut à droite", "en bas à gauche", "en bas à droite"],
}

MAX_UNDO = 100
AUTOSAVE_INTERVAL_MS = 60_000
MAX_RECENT = 8

# --- Thème -----------------------------------------------------------------

ACCENT = "#2563eb"
GREEN = "#16a34a"
RED = "#dc2626"
SLATE = "#475569"

ICONS = {
    "photo": ("🖼", ACCENT),
    "add": ("✚", GREEN),
    "remove": ("✖", RED),
    "pdf": ("📑", "#ffffff"),
    "open": ("📂", ACCENT),
    "save": ("💾", ACCENT),
    "new": ("🗋", ACCENT),
    "previous": ("◀", SLATE),
    "next": ("▶", SLATE),
    "print": ("🖶", ACCENT),
    "crop": ("✂", ACCENT),
    "auto": ("✨", "#ffffff"),
    "zoom_in": ("⊕", SLATE),
    "zoom_out": ("⊖", SLATE),
    "reset": ("⟲", SLATE),
    "undo": ("↶", SLATE),
    "redo": ("↷", SLATE),
    "sheet": ("▦", ACCENT),
    "event": ("★", "#db2777"),
    "event_other": ("◆", "#0f766e"),
    "export": ("⇪", ACCENT),
}

APP_STYLE = f"""
* {{ font-family: "Segoe UI"; font-size: 10pt; color: #1e293b; }}
QMainWindow, QDialog {{ background: #f5f7fb; }}

QMenuBar {{ background: #ffffff; border-bottom: 1px solid #e2e8f0; padding: 2px 6px; }}
QMenuBar::item {{ background: transparent; padding: 6px 10px; border-radius: 6px; }}
QMenuBar::item:selected {{ background: #eef2ff; color: #1d4ed8; }}
QMenu {{ background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 6px; }}
QMenu::item {{ padding: 7px 32px 7px 12px; border-radius: 6px; }}
QMenu::item:selected {{ background: #eef2ff; color: #1d4ed8; }}
QMenu::separator {{ height: 1px; background: #e2e8f0; margin: 5px 8px; }}
QMenu::icon {{ padding-left: 8px; }}

QPushButton {{ background: #ffffff; border: 1px solid #d5dce6; border-radius: 8px; padding: 7px 14px; }}
QPushButton:hover {{ background: #f1f5f9; border-color: #b8c2d0; }}
QPushButton:pressed {{ background: #e2e8f0; }}
QPushButton:checked {{ background: #dbeafe; border-color: {ACCENT}; color: #1d4ed8; }}
QPushButton:disabled {{ color: #a0aec0; background: #f8fafc; border-color: #e2e8f0; }}
QPushButton[primary="true"] {{ background: {ACCENT}; color: #ffffff; border-color: {ACCENT}; font-weight: 600; }}
QPushButton[primary="true"]:hover {{ background: #1d4ed8; border-color: #1d4ed8; }}

QLineEdit, QComboBox {{ background: #ffffff; border: 1px solid #d5dce6; border-radius: 8px; padding: 6px 10px; }}
QLineEdit:focus, QComboBox:focus {{ border: 2px solid {ACCENT}; padding: 5px 9px; }}
QComboBox {{ combobox-popup: 0; }}  /* la liste s'ouvre sous le champ, et non par-dessus */
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox::down-arrow {{ image: url("CHEVRON"); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{ background: #ffffff; border: 1px solid #d5dce6; border-radius: 8px; padding: 4px;
                               outline: none; }}
QComboBox QAbstractItemView::item {{ min-height: 30px; padding: 0 10px; border-radius: 6px; color: #1e293b; }}
QComboBox QAbstractItemView::item:hover {{ background: #f1f5f9; }}
QComboBox QAbstractItemView::item:selected {{ background: #dbeafe; color: #1d4ed8; }}
QCheckBox {{ spacing: 8px; }}

QStatusBar {{ background: #ffffff; border-top: 1px solid #e2e8f0; color: {SLATE}; }}
QToolTip {{ background: #1e293b; color: #ffffff; border: none; border-radius: 6px; padding: 6px 8px; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 12px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #c3cbd8; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #94a3b8; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

#panel {{ background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; }}
#panel QLabel {{ background: transparent; }}
#sectionTitle {{ font-size: 12pt; font-weight: 600; }}
#hint {{ color: {SLATE}; }}
#slot {{ background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; }}
#slot[selected="true"] {{ border: 2px solid {ACCENT}; background: #f8fbff; }}
#slot QLabel {{ background: transparent; }}
#slotTitle {{ font-weight: 600; }}
#layoutButton {{ padding: 0; border-radius: 6px; }}
#layoutButton:checked {{ background: #dbeafe; border-color: {ACCENT}; }}
#slots {{ background: transparent; }}
"""


def make_icon(name):
    """Icône dessinée à partir d'un symbole Unicode (aucun fichier image nécessaire)."""
    glyph, color = ICONS[name]
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    font = QFont("Segoe UI Symbol")
    font.setPixelSize(50)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor(color))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, glyph)
    painter.end()
    return QIcon(pixmap)


def app_style():
    """Feuille de style, avec la flèche des listes déroulantes dessinée dans un fichier temporaire."""
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor(SLATE), 2.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.drawPolyline([QPointF(6, 9), QPointF(12, 15), QPointF(18, 9)])
    painter.end()
    path = os.path.join(tempfile.gettempdir(), "calendrier_photo_chevron.png")
    pixmap.save(path)
    return APP_STYLE.replace("CHEVRON", path.replace("\\", "/"))


def color_icon(color):
    """Pastille de couleur pour le bouton de choix de la couleur."""
    pixmap = QPixmap(40, 40)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor("#ffffff"), 3))
    painter.setBrush(color)
    painter.drawEllipse(3, 3, 34, 34)
    painter.end()
    return QIcon(pixmap)


def polish_combo(combo):
    """Liste déroulante moderne : éléments espacés, survol coloré, coins arrondis."""
    # Sans délégué « stylé », la feuille de style ne s'applique pas aux éléments de la liste.
    combo.setItemDelegate(QStyledItemDelegate(combo))
    combo.setMaxVisibleItems(12)
    # Fenêtre de la liste transparente : seuls les coins arrondis dessinés par le style apparaissent.
    popup = combo.view().window()
    popup.setWindowFlags(popup.windowFlags() | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.NoDropShadowWindowHint)
    popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)


APP_ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)


def draw_app_icon(size):
    """Icône du logiciel : page de calendrier à anneaux, avec une photo (soleil et montagnes)
    au-dessus de la grille des jours, sur fond dégradé (couleurs de l'application).

    Dessinée sur une grille de 256 × 256 puis mise à l'échelle : nette à toutes les tailles.
    """
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(size / 256, size / 256)
    p.setPen(Qt.PenStyle.NoPen)

    gradient = QLinearGradient(0, 0, 256, 256)
    gradient.setColorAt(0, QColor(ACCENT))
    gradient.setColorAt(1, QColor("#7c3aed"))
    p.setBrush(gradient)
    p.drawRoundedRect(QRectF(8, 8, 240, 240), 52, 52)

    # Feuille du calendrier.
    sheet = QRectF(44, 50, 168, 170)
    p.setBrush(QColor(15, 23, 42, 50))  # ombre portée
    p.drawRoundedRect(sheet.translated(0, 6), 18, 18)
    p.setBrush(QColor("#ffffff"))
    p.drawRoundedRect(sheet, 18, 18)

    # Photo du mois : ciel, soleil, deux montagnes.
    photo = QRectF(58, 66, 140, 82)
    clip = QPainterPath()
    clip.addRoundedRect(photo, 10, 10)
    p.save()
    p.setClipPath(clip)
    sky = QLinearGradient(0, photo.top(), 0, photo.bottom())
    sky.setColorAt(0, QColor("#7dd3fc"))
    sky.setColorAt(1, QColor("#e0f2fe"))
    p.setBrush(sky)
    p.drawRect(photo)
    p.setBrush(QColor("#fbbf24"))
    p.drawEllipse(QPointF(168, 90), 13, 13)
    back = QPainterPath()
    back.moveTo(104, 148)
    back.lineTo(148, 100)
    back.lineTo(200, 148)
    back.closeSubpath()
    p.setBrush(QColor("#22c55e"))
    p.drawPath(back)
    front = QPainterPath()
    front.moveTo(54, 148)
    front.lineTo(96, 96)
    front.lineTo(140, 148)
    front.closeSubpath()
    p.setBrush(QColor(GREEN))
    p.drawPath(front)
    p.restore()

    # Grille des jours (3 rangées de 5), un jour entouré.
    p.setBrush(QColor("#cbd5e1"))
    for row in range(3):
        for col in range(5):
            x, y = 60 + col * 28, 162 + row * 16
            if (row, col) == (1, 3):
                continue
            p.drawRoundedRect(QRectF(x, y, 20, 9), 3, 3)
    p.setBrush(QColor(RED))
    p.drawEllipse(QRectF(60 + 3 * 28 - 1, 162 + 16 - 5, 22, 19))

    # Anneaux de reliure.
    for x in (92, 164):
        p.setBrush(QColor("#1e293b"))
        p.drawRoundedRect(QRectF(x - 7, 34, 14, 34), 7, 7)
        p.setBrush(QColor("#94a3b8"))
        p.drawRoundedRect(QRectF(x - 3, 38, 6, 22), 3, 3)
    p.end()
    return image


def app_icon():
    icon = QIcon()
    for size in APP_ICON_SIZES:
        icon.addPixmap(QPixmap.fromImage(draw_app_icon(size)))
    return icon


def set_primary(button):
    button.setProperty("primary", True)
    button.style().unpolish(button)
    button.style().polish(button)


def repolish(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)


# --- Jours fériés ----------------------------------------------------------

def easter(year):
    """Date de Pâques (calendrier grégorien, algorithme de Meeus/Jones/Butcher)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return datetime.date(year, month, day + 1)


def french_holidays(year):
    """Jours fériés en France métropolitaine : {date: nom}."""
    paques = easter(year)
    day = datetime.timedelta(days=1)
    return {
        datetime.date(year, 1, 1): "Jour de l'an",
        paques + day: "Lundi de Pâques",
        datetime.date(year, 5, 1): "Fête du Travail",
        datetime.date(year, 5, 8): "Victoire 1945",
        paques + 39 * day: "Ascension",
        paques + 50 * day: "Lundi de Pentecôte",
        datetime.date(year, 7, 14): "Fête nationale",
        datetime.date(year, 8, 15): "Assomption",
        datetime.date(year, 11, 1): "Toussaint",
        datetime.date(year, 11, 11): "Armistice",
        datetime.date(year, 12, 25): "Noël",
    }


# --- Vacances scolaires ----------------------------------------------------

# Dates officielles du ministère de l'Éducation nationale (jeu de données « fr-en-calendrier-scolaire »,
# data.education.gouv.fr, extrait le 21 octobre 2026), France métropolitaine, calendrier des élèves.
# (premier jour de vacances, jour de la reprise des cours, zones, nom). Les dates sont publiées
# jusqu'à l'été 2028 : la rentrée 2028 n'étant pas connue, l'été 2028 est arrêté au 31 août.
SCHOOL_HOLIDAYS = [
    ("2023-10-21", "2023-11-06", "ABC", "Toussaint"),
    ("2023-12-23", "2024-01-08", "ABC", "Noël"),
    ("2024-02-10", "2024-02-26", "C", "Hiver"),
    ("2024-02-17", "2024-03-04", "A", "Hiver"),
    ("2024-02-24", "2024-03-11", "B", "Hiver"),
    ("2024-04-06", "2024-04-22", "C", "Printemps"),
    ("2024-04-13", "2024-04-29", "A", "Printemps"),
    ("2024-04-20", "2024-05-06", "B", "Printemps"),
    ("2024-05-09", "2024-05-13", "ABC", "Pont de l'Ascension"),
    ("2024-07-06", "2024-09-02", "ABC", "Été"),
    ("2024-10-19", "2024-11-04", "ABC", "Toussaint"),
    ("2024-12-21", "2025-01-06", "ABC", "Noël"),
    ("2025-02-08", "2025-02-24", "B", "Hiver"),
    ("2025-02-15", "2025-03-03", "C", "Hiver"),
    ("2025-02-22", "2025-03-10", "A", "Hiver"),
    ("2025-04-05", "2025-04-22", "B", "Printemps"),
    ("2025-04-12", "2025-04-28", "C", "Printemps"),
    ("2025-04-19", "2025-05-05", "A", "Printemps"),
    ("2025-05-29", "2025-06-02", "ABC", "Pont de l'Ascension"),
    ("2025-07-05", "2025-09-01", "ABC", "Été"),
    ("2025-10-18", "2025-11-03", "ABC", "Toussaint"),
    ("2025-12-20", "2026-01-05", "ABC", "Noël"),
    ("2026-02-07", "2026-02-23", "A", "Hiver"),
    ("2026-02-14", "2026-03-02", "B", "Hiver"),
    ("2026-02-21", "2026-03-09", "C", "Hiver"),
    ("2026-04-04", "2026-04-20", "A", "Printemps"),
    ("2026-04-11", "2026-04-27", "B", "Printemps"),
    ("2026-04-18", "2026-05-04", "C", "Printemps"),
    ("2026-05-14", "2026-05-18", "ABC", "Pont de l'Ascension"),
    ("2026-07-04", "2026-09-01", "ABC", "Été"),
    ("2026-10-17", "2026-11-02", "ABC", "Toussaint"),
    ("2026-12-19", "2027-01-04", "ABC", "Noël"),
    ("2027-02-06", "2027-02-22", "C", "Hiver"),
    ("2027-02-13", "2027-03-01", "A", "Hiver"),
    ("2027-02-20", "2027-03-08", "B", "Hiver"),
    ("2027-04-03", "2027-04-19", "C", "Printemps"),
    ("2027-04-10", "2027-04-26", "A", "Printemps"),
    ("2027-04-17", "2027-05-03", "B", "Printemps"),
    ("2027-05-07", "2027-05-08", "ABC", "Pont de l'Ascension"),
    ("2027-07-03", "2027-09-02", "ABC", "Été"),
    ("2027-10-23", "2027-11-08", "ABC", "Toussaint"),
    ("2027-12-18", "2028-01-03", "ABC", "Noël"),
    ("2028-02-05", "2028-02-21", "B", "Hiver"),
    ("2028-02-12", "2028-02-28", "C", "Hiver"),
    ("2028-02-19", "2028-03-06", "A", "Hiver"),
    ("2028-04-08", "2028-04-24", "B", "Printemps"),
    ("2028-04-15", "2028-05-02", "C", "Printemps"),
    ("2028-04-22", "2028-05-09", "A", "Printemps"),
    ("2028-05-25", "2028-05-29", "ABC", "Pont de l'Ascension"),
    ("2028-07-04", "2028-09-01", "ABC", "Été"),
]
SCHOOL_DATA_START = datetime.date(2023, 9, 1)
SCHOOL_DATA_END = datetime.date(2028, 9, 1)  # dates inconnues à partir de ce jour

# Choix proposés : (libellé, zones affichées)
SCHOOL_ZONE_CHOICES = [("Aucune", ""), ("Zone A", "A"), ("Zone B", "B"), ("Zone C", "C"), ("Zones A, B et C", "ABC")]
ZONE_COLORS = {"A": QColor("#f59e0b"), "B": QColor("#10b981"), "C": QColor("#8b5cf6")}


def _school_days():
    """{date: {zone: nom des vacances}} pour tous les jours de vacances connus."""
    days = {}
    for start, end, zones, name in SCHOOL_HOLIDAYS:
        day, end = datetime.date.fromisoformat(start), datetime.date.fromisoformat(end)
        while day < end:
            for zone in zones:
                days.setdefault(day, {})[zone] = name
            day += datetime.timedelta(days=1)
    return days


SCHOOL_DAYS = _school_days()


# --- Anniversaires et événements ------------------------------------------

# Un événement : {"day", "month", "year" (ou None), "text", "kind"}.
# kind : "birthday" (chaque année, âge affiché si l'année de naissance est connue),
#        "yearly" (chaque année), "once" (une seule fois, à la date exacte).
EVENT_KINDS = [("birthday", "Anniversaire"), ("yearly", "Chaque année"), ("once", "Une seule fois")]
EVENT_KIND_LABELS = dict(EVENT_KINDS)
EVENT_COLORS = {"birthday": QColor("#db2777"), "yearly": QColor("#0f766e"), "once": QColor("#0f766e")}


def clean_event(data):
    """Événement valide (date existante, texte non vide) à partir de données lues, ou None."""
    try:
        day, month = int(data["day"]), int(data["month"])
        year = int(data["year"]) if data.get("year") not in (None, "") else None
        text = str(data.get("text", "")).strip()
        kind = data.get("kind") if data.get("kind") in EVENT_KIND_LABELS else ("once" if year else "yearly")
        if kind == "once" and year is None:
            return None
        datetime.date(year or 2000, month, day)  # 2000 : année bissextile, le 29 février est accepté
    except (KeyError, TypeError, ValueError):
        return None
    if not text:
        return None
    return {"day": day, "month": month, "year": year, "text": text, "kind": kind}


def event_date_text(event):
    year = f"/{event['year']}" if event["year"] else ""
    return f"{event['day']:02d}/{event['month']:02d}{year}"


def events_on(events, date):
    """Textes à afficher le jour date : [(texte, type)].

    Un anniversaire du 29 février est fêté le 28 les années non bissextiles ; l'âge n'est affiché
    que si l'année de naissance est connue (et rien n'est affiché avant la naissance).
    """
    shown = []
    leap = calendar.isleap(date.year)
    for event in events:
        day, month, year, kind = event["day"], event["month"], event["year"], event["kind"]
        if kind == "once":
            if (year, month, day) != (date.year, date.month, date.day):
                continue
            shown.append((event["text"], kind))
            continue
        if month == 2 and day == 29 and not leap:
            day = 28
        if (month, day) != (date.month, date.day) or (year and date.year < year):
            continue
        text = event["text"]
        if kind == "birthday" and year and date.year > year:
            age = date.year - year
            text += f" ({age} an{'s' if age > 1 else ''})"
        shown.append((text, kind))
    return shown


def _csv_field(value):
    value = str(value)
    if any(ch in value for ch in ';"\n'):
        value = '"' + value.replace('"', '""') + '"'
    return value


def _csv_rows(text):
    """Lignes d'un fichier CSV (séparateur « ; », « , » ou tabulation, guillemets gérés)."""
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    separator = max(";,\t", key=lines[0].count)
    rows = []
    for line in lines:
        fields, field, quoted, i = [], "", False, 0
        while i < len(line):
            ch = line[i]
            if quoted:
                if ch == '"' and line[i + 1:i + 2] == '"':
                    field += '"'
                    i += 1
                elif ch == '"':
                    quoted = False
                else:
                    field += ch
            elif ch == '"':
                quoted = True
            elif ch == separator:
                fields.append(field)
                field = ""
            else:
                field += ch
            i += 1
        fields.append(field)
        rows.append([f.strip() for f in fields])
    return rows


def export_events_csv(events, path):
    """Écrit les événements dans un fichier CSV lisible par Excel : Date;Type;Description."""
    lines = ["Date;Type;Description"]
    for event in sorted(events, key=lambda e: (e["month"], e["day"], e["text"])):
        lines.append(";".join(_csv_field(v) for v in (event_date_text(event), EVENT_KIND_LABELS[event["kind"]],
                                                      event["text"])))
    with open(path, "w", encoding="utf-8-sig", newline="\r\n") as f:  # BOM : accents corrects dans Excel
        f.write("\n".join(lines) + "\n")


def import_events_csv(path):
    """Lit un fichier CSV d'événements. Renvoie (événements valides, nombre de lignes ignorées)."""
    with open(path, encoding="utf-8-sig") as f:
        rows = _csv_rows(f.read())
    if rows and rows[0] and rows[0][0].lower().startswith("date"):
        rows = rows[1:]  # ligne d'en-tête
    events, ignored = [], 0
    for row in rows:
        if len(row) < 2:
            ignored += 1
            continue
        date_text, kind_text = row[0], row[1] if len(row) >= 3 else ""
        text = row[2] if len(row) >= 3 else row[1]
        parts = re.split(r"[/.\-]", date_text)
        kind = kind_text.lower()
        kind = ("birthday" if kind.startswith("anniv") else "yearly" if kind.startswith(("chaque", "annuel"))
                else "once" if kind.startswith(("une", "unique")) else None)
        event = None
        if len(parts) in (2, 3):
            year = parts[2] if len(parts) == 3 else None
            event = clean_event({"day": parts[0], "month": parts[1], "year": year, "text": text, "kind": kind})
        if event is None:
            ignored += 1
        else:
            events.append(event)
    return events, ignored


# --- Images ----------------------------------------------------------------

class ImageCache:
    """Charge les photos (orientation de l'appareil respectée) à la taille utile, avec cache."""

    STEPS = (256, 512, 1024, 2048, 4096)

    def __init__(self):
        self.images = {}

    def get(self, path, longest_side):
        # Arrondi au palier supérieur : quelques tailles en cache au lieu d'une par redimensionnement.
        target = next((s for s in self.STEPS if s >= longest_side), 0)
        key = (path, target)
        if key not in self.images:
            reader = QImageReader(path)
            reader.setAutoTransform(True)  # photos de téléphone : rotation EXIF appliquée
            size = reader.size()
            if target and size.isValid() and max(size.width(), size.height()) > target:
                scale = target / max(size.width(), size.height())
                reader.setScaledSize(QSize(round(size.width() * scale), round(size.height() * scale)))
            image = reader.read()
            self.images[key] = image if not image.isNull() else None
        return self.images[key]

    def forget(self, path):
        for key in [k for k in self.images if k[0] == path]:
            del self.images[key]


def _parse_exif_date(value):
    try:
        return datetime.datetime.strptime(value[:19], "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None


def _tiff_dates(tiff):
    """(prise de vue, dernière modification) d'un bloc EXIF (format TIFF) ; chaque date peut être None."""
    order = "little" if tiff[:2] == b"II" else "big"

    def u16(offset):
        return int.from_bytes(tiff[offset:offset + 2], order)

    def u32(offset):
        return int.from_bytes(tiff[offset:offset + 4], order)

    def tags(ifd):
        """{étiquette: (nombre, valeur ou position)} d'un répertoire EXIF."""
        return {u16(ifd + 2 + 12 * k): (u32(ifd + 2 + 12 * k + 4), u32(ifd + 2 + 12 * k + 8))
                for k in range(u16(ifd))}

    def text(entry):
        count, offset = entry
        return tiff[offset:offset + count].rstrip(b"\0").decode("ascii", "ignore")

    main_tags = tags(u32(4))
    taken = None
    if 0x8769 in main_tags:  # sous-répertoire EXIF : DateTimeOriginal
        exif_tags = tags(main_tags[0x8769][1])
        if 0x9003 in exif_tags:
            taken = _parse_exif_date(text(exif_tags[0x9003]))
    modified = _parse_exif_date(text(main_tags[0x0132])) if 0x0132 in main_tags else None
    return taken, modified


def exif_dates(path):
    """(prise de vue, dernière modification) d'une photo JPEG d'après ses métadonnées EXIF."""
    try:
        with open(path, "rb") as f:
            data = f.read(256 * 1024)
        if data[:2] != b"\xff\xd8":
            return None, None
        i = 2
        while i + 4 <= len(data) and data[i] == 0xFF:
            marker, length = data[i + 1], int.from_bytes(data[i + 2:i + 4], "big")
            if marker == 0xE1 and data[i + 4:i + 10] == b"Exif\0\0":
                return _tiff_dates(data[i + 10:i + 2 + length])
            if marker in (0xDA, 0xD9):  # début de l'image : plus de métadonnées
                break
            i += 2 + length
    except Exception:
        pass
    return None, None


FILENAME_DATE = re.compile(r"(?<!\d)((?:19|20)\d{2})[-_.]?(0[1-9]|1[0-2])[-_.]?(0[1-9]|[12]\d|3[01])(?!\d)")


def photo_date(path):
    """(date, provenance) d'une photo, de la source la plus fiable à la moins fiable.

    1. date de prise de vue (EXIF) et date dans le nom du fichier (IMG-20250807-…, 2025-08-07…) :
       la plus ancienne des deux, car un logiciel de retouche réécrit parfois la date de prise de vue ;
    2. date de modification EXIF ; 3. date du fichier.
    """
    taken, modified = exif_dates(path)
    named = None
    match = FILENAME_DATE.search(os.path.basename(path))
    if match:
        try:
            named = datetime.datetime(*map(int, match.groups()))
        except ValueError:
            pass
    if taken is not None and (named is None or taken.date() <= named.date()):
        return taken, "exif"
    if named is not None:
        return named, "nom"
    if modified is not None:
        return modified, "exif"
    return datetime.datetime.fromtimestamp(os.path.getmtime(path)), "fichier"


def same_photo(a, b):
    """Vrai si deux chemins désignent la même photo : même fichier, ou copie identique sous un autre nom."""
    if os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b)):
        return True
    try:
        # Tailles d'abord (rapide) ; contenu comparé octet par octet seulement si elles sont égales.
        return os.path.getsize(a) == os.path.getsize(b) and filecmp.cmp(a, b, shallow=False)
    except OSError:
        return False


def is_portrait(path):
    """Vrai si la photo, une fois remise dans le bon sens, est plus haute que large."""
    reader = QImageReader(path)
    size = reader.size()
    if not size.isValid():
        return False
    width, height = size.width(), size.height()
    if reader.transformation() & QImageIOHandler.Transformation.TransformationRotate90:
        width, height = height, width
    return height > width


# Coûts de la répartition automatique (plus c'est bas, mieux c'est).
PLAN_MISMATCH = 1.0  # photo dans un cadre de l'autre format (portrait dans un cadre en largeur…)
PLAN_SIZE = 0.2  # × (nombre de photos de la page)² : préfère des pages équilibrées
PLAN_EMPTY_MONTH = 3.0  # mois laissé sans photo


def _group_cost(portraits, slot_portraits):
    """Coût d'une page : écarts de format (meilleure attribution des cadres) et taille de la page.

    slot_portraits : pour chaque cadre, True (en hauteur), False (en largeur) ou None (sans contrainte).
    """
    size = len(portraits)
    portrait_count = sum(portraits)
    wanted_portraits = sum(1 for wants in slot_portraits if wants is True)
    wanted_landscapes = sum(1 for wants in slot_portraits if wants is False)
    mismatches = max(0, wanted_portraits - portrait_count) + max(0, wanted_landscapes - (size - portrait_count))
    return PLAN_MISMATCH * mismatches + PLAN_SIZE * size * size


def _assign_slots(group, slot_portraits):
    """Ordre des photos d'une page : chaque cadre en hauteur reçoit un portrait, chaque cadre en largeur
    un paysage, quand c'est possible ; les cadres sans contrainte prennent les photos restantes dans
    l'ordre chronologique."""
    remaining = list(group)  # (chemin, portrait ?) dans l'ordre chronologique
    ordered = [None] * len(slot_portraits)
    for slot, wants in enumerate(slot_portraits):
        if wants is None:
            continue
        match = next((photo for photo in remaining if photo[1] == wants), remaining[0])
        remaining.remove(match)
        ordered[slot] = match[0]
    for slot, wants in enumerate(slot_portraits):
        if wants is None:
            ordered[slot] = remaining.pop(0)[0]
    return ordered


def plan_months(paths, months=12, slot_aspects=None):
    """Répartit des photos sur les mois en utilisant le plus de photos possible (jusqu'à MAX_SLOTS par page).

    Les photos restent dans l'ordre chronologique d'un mois à l'autre. Le découpage (combien de photos
    sur chaque page) est celui qui, dans l'ordre : remplit le plus de mois, met les portraits dans
    des cadres en hauteur et les paysages dans des cadres en largeur, et équilibre les pages.
    slot_aspects : {nombre de photos: [largeur / hauteur de chaque cadre]} pour le format de page choisi.
    Renvoie (groupes retenus, photos écartées, infos) ; chaque groupe contient 1 à 4 photos.
    """
    if slot_aspects is None:
        slot_aspects = {k: [1.5] * k for k in range(1, MAX_SLOTS + 1)}
    slot_portraits = {k: [aspect < 1 for aspect in aspects] for k, aspects in slot_aspects.items()}
    # Disposition 3 : le grand cadre de gauche reçoit toujours un portrait, les deux de droite n'importe quoi.
    slot_portraits[3] = [True, None, None]
    infos = sorted((photo_date(p) + (p, is_portrait(p)) for p in paths), key=lambda info: info[0])
    photos = [(path, portrait) for _date, _source, path, portrait in infos]
    capacity = months * MAX_SLOTS
    if len(photos) > capacity:
        # Trop de photos : on en garde autant que de places, réparties sur toute la période.
        keep = sorted({round(i * (len(photos) - 1) / (capacity - 1)) for i in range(capacity)})
        photos = [photos[i] for i in keep]
    n = len(photos)
    if n == 0:
        return [], list(paths), infos

    # best[i][g] : coût minimal pour placer les i premières photos sur g pages (et la taille de la dernière).
    inf = float("inf")
    best = [[(inf, 0)] * (months + 1) for _ in range(n + 1)]
    best[0][0] = (0.0, 0)
    for i in range(1, n + 1):
        for g in range(1, min(months, i) + 1):
            for size in range(1, min(MAX_SLOTS, i) + 1):
                previous = best[i - size][g - 1][0]
                if previous == inf:
                    continue
                group = [portrait for _path, portrait in photos[i - size:i]]
                if size == 3 and not any(group):
                    continue  # pas de page à 3 photos sans portrait pour le grand cadre de gauche
                slots = slot_portraits[size]
                if size == 1 and group[0] and single_portrait_layout(slot_portraits) == 2:
                    slots = [True]  # portrait seul : cadre en hauteur de la disposition 2 (voir plus bas)
                cost = previous + _group_cost(group, slots)
                if cost < best[i][g][0]:
                    best[i][g] = (cost, size)
    pages = min(range(1, min(months, n) + 1),
                key=lambda g: best[n][g][0] + PLAN_EMPTY_MONTH * (months - g))
    sizes = []
    i, g = n, pages
    while i:
        size = best[i][g][1]
        sizes.append(size)
        i, g = i - size, g - 1
    groups, start = [], 0
    for size in reversed(sizes):
        group = _assign_slots(photos[start:start + size], slot_portraits[size])
        if size == 1 and photos[start][1] and single_portrait_layout(slot_portraits) == 2:
            group = [group[0], None]  # disposition 2 : portrait à gauche, cadre de droite laissé vide
        groups.append(group)
        start += size
    used = {p for group in groups for p in group if p}
    return groups, [p for p in paths if p not in used], infos


def single_portrait_layout(slot_portraits):
    """Disposition d'une page à un seul portrait : la 1 si son cadre est en hauteur (page au format
    paysage), sinon la 2, dont le cadre de gauche est en hauteur (celui de droite reste vide)."""
    return 1 if slot_portraits[1][0] else 2


MAX_ZOOM = 5.0


def cover_source_rect(image, target, crop=None):
    """Partie de l'image qui remplit la cible sans déformation.

    crop = {"zoom": ≥ 1, "x": centre horizontal, "y": centre vertical} (centre en fraction de l'image) ;
    sans recadrage, c'est la partie centrale. La zone reste toujours à l'intérieur de l'image.
    """
    crop = crop or {}
    zoom = max(1.0, crop.get("zoom", 1.0))
    scale = max(target.width() / image.width(), target.height() / image.height()) * zoom
    w, h = target.width() / scale, target.height() / scale
    x = crop.get("x", 0.5) * image.width() - w / 2
    y = crop.get("y", 0.5) * image.height() - h / 2
    x = min(max(x, 0.0), image.width() - w)
    y = min(max(y, 0.0), image.height() - h)
    return QRectF(x, y, w, h)


# Cadres remplis par défaut (photo recadrée au centre plutôt que réduite) : (disposition, emplacement).
# Disposition 3 : les deux petits cadres de droite, presque carrés, où une photo entière paraîtrait minuscule.
FILLED_BY_DEFAULT = {(3, 1), (3, 2)}
WHOLE_CROP = {"whole": True}  # recadrage « Photo entière » choisi explicitement avec l'outil ✂


def slot_whole(count, slot):
    """Vrai si l'emplacement affiche par défaut la photo entière (sans recadrage choisi)."""
    return (count, slot) not in FILLED_BY_DEFAULT


def draw_in_frame(painter, rect, image, crop, whole, radius):
    """Dessine une photo dans son cadre, coins arrondis.

    whole (photo entière) et pas de recadrage choisi, ou « Photo entière » choisie avec l'outil :
    la photo est réduite et centrée, rien n'est coupé. Sinon : elle remplit le cadre (recadrage
    choisi avec l'outil, ou partie centrale).
    """
    if crop is not None and crop.get("whole"):
        whole, crop = True, None
    if whole and crop is None:
        scale = min(rect.width() / image.width(), rect.height() / image.height())
        w, h = image.width() * scale, image.height() * scale
        target = QRectF(rect.center().x() - w / 2, rect.center().y() - h / 2, w, h)
        source = QRectF(image.rect())
    else:
        target, source = rect, cover_source_rect(image, rect, crop)
    clip = QPainterPath()
    clip.addRoundedRect(target, radius, radius)
    painter.save()
    painter.setClipPath(clip)
    painter.drawImage(target, image, source)
    painter.restore()


def split_frame(rect, count, gap=None):
    """Cadres des photos d'une zone, séparés d'un petit écart, selon la disposition :

    1 : un seul cadre ; 2 : deux cadres côte à côte ; 3 : un grand cadre à gauche et deux petits
    superposés à droite ; 4 : mosaïque de 2 × 2. Ordre : de gauche à droite, puis de haut en bas.
    """
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    if gap is None:
        gap = min(w, h) * 0.03
    if count == 1:
        return [QRectF(rect)]
    half_w, half_h = (w - gap) / 2, (h - gap) / 2
    if count == 2:
        return [QRectF(x, y, half_w, h), QRectF(x + half_w + gap, y, half_w, h)]
    if count == 3:
        big = (w - gap) * 0.6
        small = w - gap - big
        return [QRectF(x, y, big, h),
                QRectF(x + big + gap, y, small, half_h), QRectF(x + big + gap, y + half_h + gap, small, half_h)]
    return [QRectF(x, y, half_w, half_h), QRectF(x + half_w + gap, y, half_w, half_h),
            QRectF(x, y + half_h + gap, half_w, half_h), QRectF(x + half_w + gap, y + half_h + gap, half_w, half_h)]


def padded(values):
    """Liste des photos (ou des recadrages) d'une page, complétée à MAX_SLOTS emplacements."""
    return (list(values or []) + [None] * MAX_SLOTS)[:MAX_SLOTS]


# --- Rendu d'une page ------------------------------------------------------

class Settings:
    def __init__(self):
        today = datetime.date.today()
        self.title = "Mon calendrier"
        self.year = today.year + 1 if today.month >= 9 else today.year
        self.format_index = 0
        self.font_index = 0
        self.accent = QColor("#2563eb")
        self.cover = True
        self.holidays = True
        self.weekends = True
        # Photos toujours entières (rien n'est coupé), sauf celles recadrées une à une avec l'outil ✂.
        self.whole_photos = True
        self.school_zone = ""  # vacances scolaires affichées : "", "A", "B", "C" ou "ABC"
        self.week_numbers = False
        self.events = []  # anniversaires et événements (voir clean_event)
        self.show_events = True

    @property
    def landscape(self):
        return FORMATS[self.format_index][2]

    @property
    def font_family(self):
        return FONTS[self.font_index][1]

    def pages(self):
        """Liste des pages : ("cover", None) puis ("month", (année, mois)) de janvier à décembre."""
        pages = [("cover", None)] if self.cover else []
        pages += [("month", (self.year, month)) for month in range(1, 13)]
        return pages

    def to_dict(self):
        return {
            "title": self.title, "year": self.year,
            "format": self.format_index, "font": self.font_index, "accent": self.accent.name(),
            "cover": self.cover, "holidays": self.holidays, "weekends": self.weekends,
            "whole_photos": self.whole_photos, "school_zone": self.school_zone, "week_numbers": self.week_numbers,
            "events": self.events, "show_events": self.show_events,
        }

    def load_dict(self, data):
        self.title = data.get("title", self.title)
        self.year = int(data.get("year", self.year))
        self.format_index = int(data.get("format", self.format_index))
        self.font_index = int(data.get("font", self.font_index))
        self.accent = QColor(data.get("accent", self.accent.name()))
        self.cover = bool(data.get("cover", self.cover))
        self.holidays = bool(data.get("holidays", self.holidays))
        self.weekends = bool(data.get("weekends", self.weekends))
        zone = data.get("school_zone", self.school_zone)
        self.school_zone = zone if zone in {z for _label, z in SCHOOL_ZONE_CHOICES} else ""
        self.week_numbers = bool(data.get("week_numbers", self.week_numbers))
        events = data.get("events", [])
        self.events = [e for e in map(clean_event, events if isinstance(events, list) else []) if e]
        self.show_events = bool(data.get("show_events", self.show_events))


class CalendarRenderer:
    """Dessine les pages du calendrier ; le même code sert à l'aperçu et au PDF."""

    TEXT = QColor("#1e293b")
    MUTED = QColor("#64748b")
    CELL = QColor("#f3f5f8")

    def __init__(self, settings, photos, layouts, crops, cache):
        self.settings = settings
        # Clé de page : "cover" ou numéro de mois dans le calendrier (0 à 11).
        self.photos = photos  # clé -> [photo 1, …, photo 4] (chemins ou None)
        self.layouts = layouts  # clé -> nombre de photos de la page (1 à 4, voir split_frame)
        self.crops = crops  # clé -> [recadrage 1, …, recadrage 4] (voir cover_source_rect, ou None)
        self.cache = cache
        # Impression et PDF : les cadres sans photo ne sont pas dessinés (l'aperçu, lui, les montre).
        self.hide_empty = False

    def page_key(self, page_index):
        if self.settings.cover:
            return "cover" if page_index == 0 else page_index - 1
        return page_index

    def page_photos(self, key):
        """Photos affichées sur une page, selon sa disposition."""
        return padded(self.photos.get(key))[: self.layouts.get(key, 1)]

    def page_crops(self, key):
        return padded(self.crops.get(key))[: self.layouts.get(key, 1)]

    def _areas(self, kind, w, h):
        """Zone des photos et zone du texte (calendrier ou titre) d'une page."""
        s = self.settings
        if kind == "cover":
            m = min(w, h) * 0.06
            photo = QRectF(m, m, w - 2 * m, h * (0.62 if s.landscape else 0.68))
            return photo, QRectF(m, photo.bottom() + m * 0.5, w - 2 * m, h - photo.bottom() - m * 1.5)
        m = min(w, h) * 0.05
        if s.landscape:
            photo = QRectF(m, m, w * 0.56 - m, h - 2 * m)
            return photo, QRectF(photo.right() + m, m, w - photo.right() - 2 * m, h - 2 * m)
        photo = QRectF(m, m, w - 2 * m, h * 0.5)
        return photo, QRectF(m, photo.bottom() + m * 0.8, w - 2 * m, h - photo.bottom() - m * 1.8)

    def photo_frames(self, page_index, w, h):
        """Cadres des photos d'une page de taille w × h."""
        kind, _ = self.settings.pages()[page_index]
        return split_frame(self._areas(kind, w, h)[0], self.layouts.get(self.page_key(page_index), 1))

    def page_ratio(self):
        """Hauteur / largeur de la page."""
        size = QPageSize(FORMATS[self.settings.format_index][1]).size(QPageSize.Unit.Millimeter)
        w, h = size.width(), size.height()
        return w / h if self.settings.landscape else h / w

    def font(self, pixels, bold=False):
        font = QFont(self.settings.font_family)
        font.setPixelSize(max(1, round(pixels)))
        font.setBold(bold)
        return font

    def render(self, painter, page_index, w, h):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.fillRect(QRectF(0, 0, w, h), Qt.GlobalColor.white)
        kind, value = self.settings.pages()[page_index]
        key = self.page_key(page_index)
        _, text_area = self._areas(kind, w, h)
        radius = min(w, h) * 0.015
        count = self.layouts.get(key, 1)
        for slot, (frame, path, crop) in enumerate(zip(self.photo_frames(page_index, w, h), self.page_photos(key),
                                                       self.page_crops(key))):
            self._draw_photo(painter, frame, path, radius, crop, self.settings.whole_photos and slot_whole(count, slot))
        if kind == "cover":
            self._render_cover_text(painter, text_area, w)
        else:
            self._draw_month_grid(painter, text_area, *value)
        painter.restore()

    def _draw_photo(self, painter, rect, path, radius, crop=None, whole=True):
        zoom = (crop or {}).get("zoom", 1.0)
        image = self.cache.get(path, max(rect.width(), rect.height()) * 1.5 * zoom) if path else None
        if image is not None:
            draw_in_frame(painter, rect, image, crop, whole, radius)
            return
        if self.hide_empty:
            return
        clip = QPainterPath()
        clip.addRoundedRect(rect, radius, radius)
        painter.save()
        painter.setClipPath(clip)
        painter.fillRect(rect, QColor("#eef1f5"))
        painter.setPen(self.MUTED)
        painter.setFont(self.font(min(rect.width(), rect.height()) * 0.07))
        message = "Photo introuvable" if path else "Aucune photo"
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, message)
        painter.restore()

    def _render_cover_text(self, painter, area, w):
        s = self.settings
        painter.setPen(self.TEXT)
        painter.setFont(self.font(min(area.height() * 0.32, w * 0.07), bold=True))
        painter.drawText(QRectF(area.x(), area.y(), area.width(), area.height() * 0.55),
                         Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom, s.title)
        painter.setPen(s.accent)
        painter.setFont(self.font(min(area.height() * 0.26, w * 0.06)))
        first, last = s.pages()[-12][1], s.pages()[-1][1]
        years = str(first[0]) if first[0] == last[0] else f"{first[0]} – {last[0]}"
        painter.drawText(QRectF(area.x(), area.y() + area.height() * 0.58, area.width(), area.height() * 0.42),
                         Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, years)

    def _draw_month_grid(self, painter, cal, year, month):
        s = self.settings
        accent = s.accent
        holidays = french_holidays(year) if s.holidays else {}

        # En-tête : nom du mois et année.
        hh = min(cal.height() * 0.15, cal.width() * 0.13)
        header = QRectF(cal.x(), cal.y(), cal.width(), hh)
        painter.setPen(accent)
        painter.setFont(self.font(hh * 0.62, bold=True))
        painter.drawText(header, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, MONTHS[month - 1])
        painter.setPen(self.MUTED)
        painter.setFont(self.font(hh * 0.42))
        painter.drawText(header, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, str(year))
        painter.setPen(QPen(accent, max(1.0, hh * 0.03)))
        painter.drawLine(header.bottomLeft(), header.bottomRight())

        # Légende des vacances scolaires, sous la grille.
        bottom = cal.bottom()
        if s.school_zone:
            legend_h = hh * 0.42
            bottom -= legend_h
            self._draw_school_legend(painter, QRectF(cal.x(), bottom, cal.width(), legend_h), year, month)

        # Colonne des numéros de semaine, à gauche de la grille.
        weeks = calendar.Calendar(firstweekday=0).monthdayscalendar(year, month)
        week_w = cal.width() * 0.065 if s.week_numbers else 0
        left = cal.x() + week_w
        cw = (cal.width() - week_w) / 7

        # Noms des jours.
        dh = hh * 0.45
        top = header.bottom() + hh * 0.2
        painter.setFont(self.font(dh * 0.6, bold=True))
        for col, name in enumerate(DAYS):
            painter.setPen(accent if s.weekends and col >= 5 else self.MUTED)
            painter.drawText(QRectF(left + col * cw, top, cw, dh), Qt.AlignmentFlag.AlignCenter, name)
        if week_w:
            painter.setPen(self.MUTED)
            painter.setFont(self.font(dh * 0.48))
            painter.drawText(QRectF(cal.x(), top, week_w, dh), Qt.AlignmentFlag.AlignCenter, "Sem.")

        # Grille des jours.
        grid_top = top + dh + hh * 0.1
        ch = (bottom - grid_top) / len(weeks)
        pad = min(cw, ch) * 0.045
        number_px = min(ch * 0.34, cw * 0.3)
        label_px = min(ch * 0.19, cw * 0.14)
        for row, week in enumerate(weeks):
            if week_w:  # numéro de semaine ISO (la semaine commence le lundi)
                first = next(day for day in week if day)
                number = datetime.date(year, month, first).isocalendar()[1]
                painter.setPen(self.MUTED)
                painter.setFont(self.font(min(number_px * 0.62, week_w * 0.5)))
                painter.drawText(QRectF(cal.x(), grid_top + row * ch, week_w, ch), Qt.AlignmentFlag.AlignCenter,
                                 str(number))
            for col, day in enumerate(week):
                if not day:
                    continue
                date = datetime.date(year, month, day)
                holiday = holidays.get(date)
                weekend = s.weekends and col >= 5
                cell = QRectF(left + col * cw + pad, grid_top + row * ch + pad, cw - 2 * pad, ch - 2 * pad)

                background = QColor(self.CELL)
                if holiday:
                    background = QColor(accent)
                    background.setAlpha(45)
                elif weekend:
                    background = QColor(accent)
                    background.setAlpha(18)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(background)
                painter.drawRoundedRect(cell, pad * 2, pad * 2)

                inner = cell.adjusted(pad * 2.5, pad * 1.5, -pad * 2, -pad * 1.5)
                painter.setPen(accent if holiday or (weekend and col == 6) else self.TEXT)
                painter.setFont(self.font(number_px, bold=bool(holiday or weekend)))
                painter.drawText(inner, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, str(day))
                labels = [(holiday, accent)] if holiday else []
                if s.show_events:  # anniversaires d'abord, puis les autres événements
                    day_events = sorted(events_on(s.events, date), key=lambda e: e[1] != "birthday")
                    labels += [(text, EVENT_COLORS[kind]) for text, kind in day_events]
                if labels:
                    # Place du bandeau des vacances, seulement les jours où il est dessiné.
                    vacation = any(zone in SCHOOL_DAYS.get(date, {}) for zone in s.school_zone)
                    band = cell.height() * 0.12 + pad if vacation else 0
                    number_w = painter.fontMetrics().horizontalAdvance(str(day))
                    self._draw_cell_labels(painter, inner.adjusted(0, number_px * 1.25, 0, -band),
                                           inner.adjusted(number_w + pad * 2.5, pad * 0.5, 0, -band), labels, label_px)
                if s.school_zone:
                    self._draw_school_band(painter, cell, date, pad)

    def _draw_cell_labels(self, painter, below, beside, labels, px):
        """Textes d'un jour (jour férié, anniversaires, événements), les uns sous les autres.

        Les textes ne sont jamais raccourcis : ils passent à la ligne. Ils vont sous le numéro du jour
        si tout y tient en réduisant peu la police (jusqu'à 70 %) ; sinon à droite du numéro, sur toute
        la hauteur de la case, en réduisant la police jusqu'à la moitié de sa taille.
        """
        flags = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap

        def layout(area, smallest):
            """(taille de police, rectangles des textes, écart) qui tient dans area, ou None."""
            size = px
            while area.width() > 0 and area.height() > 0:
                painter.setFont(self.font(size))
                boxes = [painter.boundingRect(QRectF(area.left(), 0, area.width(), 100000), flags, text)
                         for text, _color in labels]
                gap = size * 0.15
                height = sum(box.height() for box in boxes) + gap * (len(labels) - 1)
                if height <= area.height() and all(box.width() <= area.width() + 0.5 for box in boxes):
                    return size, boxes, gap
                if size <= smallest:
                    return None
                size = max(smallest, size * 0.9)
            return None

        area, result = below, layout(below, px * 0.7)
        if result is None:
            area, result = beside, layout(beside, px * 0.5)
        if result is None:  # case minuscule : plus petite taille, ce qui dépasse n'est pas dessiné
            area = beside
            painter.setFont(self.font(px * 0.5))
            gap = px * 0.5 * 0.15
            result = (px * 0.5, [painter.boundingRect(QRectF(area.left(), 0, area.width(), 100000), flags, text)
                                 for text, _color in labels], gap)
        size, boxes, gap = result
        painter.save()
        painter.setClipRect(area)
        painter.setFont(self.font(size))
        y = area.top()
        for (text, color), box in zip(labels, boxes):
            painter.setPen(color)
            painter.drawText(QRectF(area.left(), y, area.width(), box.height()), flags, text)
            y += box.height() + gap
        painter.restore()

    def _draw_school_band(self, painter, cell, date, pad):
        """Bandeau en bas de la case d'un jour de vacances scolaires : une couleur par zone.

        Avec les trois zones, le bandeau est partagé en trois (A, B, C de gauche à droite).
        """
        on_holiday = SCHOOL_DAYS.get(date, {})
        zones = self.settings.school_zone
        if not any(zone in on_holiday for zone in zones):
            return
        band_h = max(1.0, cell.height() * 0.12)
        band = QRectF(cell.x() + pad * 2, cell.bottom() - band_h - pad * 1.5, cell.width() - pad * 4, band_h)
        part = band.width() / len(zones)
        painter.setPen(Qt.PenStyle.NoPen)
        for i, zone in enumerate(zones):
            if zone in on_holiday:
                painter.setBrush(ZONE_COLORS[zone])
                painter.drawRoundedRect(QRectF(band.x() + i * part, band.y(), part, band_h), band_h / 2, band_h / 2)

    def _draw_school_legend(self, painter, area, year, month):
        """« Vacances scolaires : ▬ zone A », ou un avertissement si les dates du mois ne sont pas publiées."""
        zones = self.settings.school_zone
        px = area.height() * 0.5
        painter.setFont(self.font(px))
        metrics_font = painter.fontMetrics()
        x = area.x()
        y = area.center().y()
        month_start = datetime.date(year, month, 1)
        month_end = datetime.date(year + month // 12, month % 12 + 1, 1)
        if month_start >= SCHOOL_DATA_END or month_end <= SCHOOL_DATA_START:
            painter.setPen(self.MUTED)
            painter.drawText(area, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                             "Vacances scolaires : dates pas encore publiées pour ce mois")
            return
        painter.setPen(self.MUTED)
        text = "Vacances scolaires :"
        painter.drawText(QRectF(x, area.y(), area.width(), area.height()),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
        x += metrics_font.horizontalAdvance(text) + px * 0.6
        for zone in zones:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(ZONE_COLORS[zone])
            painter.drawRoundedRect(QRectF(x, y - px * 0.18, px * 1.4, px * 0.36), px * 0.18, px * 0.18)
            x += px * 1.4 + px * 0.35
            painter.setPen(self.MUTED)
            label = f"zone {zone}"
            painter.drawText(QRectF(x, area.y(), area.width(), area.height()),
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)
            x += metrics_font.horizontalAdvance(label) + px * 0.9


# --- Interface -------------------------------------------------------------

class PreviewWidget(QWidget):
    """Aperçu de la page sélectionnée, à l'échelle de la fenêtre, ou planche de toutes les pages."""

    SHEET_GAP = 14
    SHEET_LABEL = 20  # hauteur du nom de la page sous chaque miniature

    def __init__(self, window):
        super().__init__()
        self.window = window
        self.sheet = False  # vue d'ensemble : toutes les pages en miniature
        self._sheet_cache = None  # (clé, image) : la planche n'est redessinée que si elle change
        self.setMinimumSize(320, 320)
        self.setMouseTracking(True)

    def set_sheet(self, sheet):
        self.sheet = sheet
        self.setToolTip("")
        self.update()

    def _sheet_rects(self, renderer):
        """Rectangles des miniatures de la planche : la disposition qui donne les plus grandes pages."""
        count = len(self.window.settings.pages())
        ratio = renderer.page_ratio()
        avail = QRectF(self.rect()).adjusted(16, 16, -16, -16)
        gap, label = self.SHEET_GAP, self.SHEET_LABEL
        best = None
        for cols in range(1, count + 1):
            rows = -(-count // cols)
            w = min((avail.width() - gap * (cols - 1)) / cols,
                    ((avail.height() - gap * (rows - 1)) / rows - label) / ratio)
            if best is None or w > best[0]:
                best = (w, cols, rows)
        w, cols, rows = best
        w = max(w, 1.0)
        h = w * ratio
        total_w = cols * w + (cols - 1) * gap
        total_h = rows * (h + label) + (rows - 1) * gap
        x0 = avail.x() + (avail.width() - total_w) / 2
        y0 = avail.y() + (avail.height() - total_h) / 2
        return [QRectF(x0 + (i % cols) * (w + gap), y0 + (i // cols) * (h + label + gap), w, h)
                for i in range(count)]

    def _sheet_index_at(self, pos):
        for i, rect in enumerate(self._sheet_rects(self.window.renderer())):
            if rect.adjusted(0, 0, 0, self.SHEET_LABEL).contains(pos):
                return i
        return None

    def _paint_sheet(self, painter):
        renderer = self.window.renderer()
        key = (self.window._state(), self.width(), self.height(), self.window.current)
        if self._sheet_cache is None or self._sheet_cache[0] != key:
            dpr = self.devicePixelRatioF()
            image = QImage(round(self.width() * dpr), round(self.height() * dpr),
                           QImage.Format.Format_ARGB32_Premultiplied)
            image.setDevicePixelRatio(dpr)
            image.fill(Qt.GlobalColor.transparent)
            p = QPainter(image)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            label_font = QFont("Segoe UI")
            label_font.setPixelSize(12)
            for i, rect in enumerate(self._sheet_rects(renderer)):
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(15, 23, 42, 14))
                for k in range(4, 0, -1):
                    p.drawRoundedRect(rect.translated(0, 2).adjusted(-k, -k, k, k), k, k)
                p.save()
                p.translate(rect.topLeft())
                renderer.render(p, i, rect.width(), rect.height())
                p.restore()
                if i == self.window.current:
                    p.setPen(QPen(QColor(ACCENT), 3))
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.drawRect(rect.adjusted(-2, -2, 2, 2))
                p.setFont(label_font)
                p.setPen(QColor(ACCENT) if i == self.window.current else QColor(SLATE))
                p.drawText(QRectF(rect.x(), rect.bottom() + 2, rect.width(), self.SHEET_LABEL),
                           Qt.AlignmentFlag.AlignCenter, self.window._page_title(i))
            p.end()
            self._sheet_cache = (key, image)
        painter.drawImage(0, 0, self._sheet_cache[1])

    def _page_rect(self, renderer):
        ratio = renderer.page_ratio()
        avail = QRectF(self.rect()).adjusted(16, 16, -16, -16)
        w = min(avail.width(), avail.height() / ratio)
        h = w * ratio
        return QRectF(avail.x() + (avail.width() - w) / 2, avail.y() + (avail.height() - h) / 2, w, h)

    def _slot_at(self, pos):
        """Emplacement de photo sous la souris (0 ou 1), ou None."""
        renderer = self.window.renderer()
        page = self._page_rect(renderer)
        local = pos - page.topLeft()
        for slot, frame in enumerate(renderer.photo_frames(self.window.current, page.width(), page.height())):
            if frame.contains(local):
                return slot
        return None

    def mouseMoveEvent(self, event):
        if self.sheet:
            index = self._sheet_index_at(event.position())
            self.setCursor(Qt.CursorShape.PointingHandCursor if index is not None else Qt.CursorShape.ArrowCursor)
            self.setToolTip(f"{self.window._page_title(index)} : cliquez pour l'afficher en grand"
                            if index is not None else "")
            return
        over = self._slot_at(event.position()) is not None
        self.setCursor(Qt.CursorShape.PointingHandCursor if over else Qt.CursorShape.ArrowCursor)
        self.setToolTip("Double-cliquez pour recadrer la photo" if over else "")

    def mousePressEvent(self, event):
        if self.sheet and event.button() == Qt.MouseButton.LeftButton:
            index = self._sheet_index_at(event.position())
            if index is not None:
                self.window.open_from_sheet(index)

    def mouseDoubleClickEvent(self, event):
        if self.sheet:
            return
        slot = self._slot_at(event.position())
        if slot is not None:
            self.window.crop_photo(self.window.current, slot)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.sheet:
            self._paint_sheet(painter)
            return
        renderer = self.window.renderer()
        page = self._page_rect(renderer)
        w, h = page.width(), page.height()

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(15, 23, 42, 9))
        for i in range(10, 0, -1):
            painter.drawRoundedRect(page.translated(0, 4).adjusted(-i, -i, i, i), i, i)

        painter.translate(page.topLeft())
        renderer.render(painter, self.window.current, w, h)


class CropView(QWidget):
    """Zone de recadrage : la photo glisse sous un cadre fixe ; la molette zoome sous la souris.

    Les parties de la photo hors du cadre restent visibles, assombries.
    """

    changed = Signal()

    def __init__(self, image, aspect, crop):
        super().__init__()
        self.image = image
        self.aspect = aspect  # largeur / hauteur du cadre sur la page
        self.zoom = crop.get("zoom", 1.0) if crop else 1.0
        self.cx = crop.get("x", 0.5) if crop else 0.5
        self.cy = crop.get("y", 0.5) if crop else 0.5
        self.drag_start = None
        self.setMinimumSize(480, 360)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def crop(self):
        return {"zoom": round(self.zoom, 4), "x": round(self.cx, 4), "y": round(self.cy, 4)}

    def frame(self):
        avail = QRectF(self.rect()).adjusted(48, 48, -48, -48)
        w = min(avail.width(), avail.height() * self.aspect)
        h = w / self.aspect
        return QRectF(avail.center().x() - w / 2, avail.center().y() - h / 2, w, h)

    def _source(self):
        return cover_source_rect(self.image, self.frame(), self.crop())

    def _set(self, zoom=None, cx=None, cy=None):
        """Applique un changement, puis ramène le centre dans les limites de l'image."""
        if zoom is not None:
            self.zoom = min(MAX_ZOOM, max(1.0, zoom))
        if cx is not None:
            self.cx, self.cy = cx, cy
        source = self._source()
        self.cx = source.center().x() / self.image.width()
        self.cy = source.center().y() / self.image.height()
        self.update()
        self.changed.emit()

    def set_zoom(self, zoom, anchor=None):
        """Zoome en gardant fixe le point de la photo sous anchor (centre du cadre par défaut)."""
        frame = self.frame()
        anchor = anchor if anchor is not None else frame.center()
        before = self._source()
        scale = frame.width() / before.width()
        point = before.topLeft() + (anchor - frame.topLeft()) / scale  # point de l'image sous anchor
        self.zoom = min(MAX_ZOOM, max(1.0, zoom))
        after = cover_source_rect(self.image, frame, {"zoom": self.zoom})
        new_scale = frame.width() / after.width()
        top_left = point - (anchor - frame.topLeft()) / new_scale
        self._set(cx=(top_left.x() + after.width() / 2) / self.image.width(),
                  cy=(top_left.y() + after.height() / 2) / self.image.height())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.fillRect(self.rect(), QColor("#1e293b"))

        frame = self.frame()
        source = self._source()
        scale = frame.width() / source.width()
        target = QRectF(frame.x() - source.x() * scale, frame.y() - source.y() * scale,
                        self.image.width() * scale, self.image.height() * scale)
        painter.drawImage(target, self.image)

        # Assombrit ce qui sera coupé.
        outside = QPainterPath()
        outside.addRect(QRectF(self.rect()))
        inside = QPainterPath()
        inside.addRect(frame)
        painter.fillPath(outside.subtracted(inside), QColor(15, 23, 42, 170))

        # Cadre et repères des tiers.
        painter.setPen(QPen(QColor(255, 255, 255, 90), 1))
        for i in (1, 2):
            x = frame.x() + frame.width() * i / 3
            y = frame.y() + frame.height() * i / 3
            painter.drawLine(QPointF(x, frame.top()), QPointF(x, frame.bottom()))
            painter.drawLine(QPointF(frame.left(), y), QPointF(frame.right(), y))
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(frame)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start = (event.position(), self.cx, self.cy)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if self.drag_start is None:
            return
        start, cx, cy = self.drag_start
        scale = self.frame().width() / self._source().width()
        delta = event.position() - start
        # La photo suit la souris : le centre de la zone visible part dans l'autre sens.
        self._set(cx=cx - delta.x() / scale / self.image.width(), cy=cy - delta.y() / scale / self.image.height())

    def mouseReleaseEvent(self, event):
        self.drag_start = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def wheelEvent(self, event):
        steps = event.angleDelta().y() / 120
        if steps:
            self.set_zoom(self.zoom * 1.12 ** steps, event.position())


class CropDialog(QDialog):
    """Recadrage d'une photo : déplacement de la zone visible et zoom."""

    def __init__(self, image, aspect, crop, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Recadrer — {title}")
        self.resize(980, 760)

        self.view = CropView(image, aspect, crop)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(100, round(MAX_ZOOM * 100))
        self.slider.setValue(round(self.view.zoom * 100))
        self.slider.valueChanged.connect(lambda value: self.view.set_zoom(value / 100))
        self.zoom_label = QLabel()
        self.zoom_label.setMinimumWidth(48)
        self.view.changed.connect(self._sync)

        zoom_out = QPushButton(make_icon("zoom_out"), "")
        zoom_out.setToolTip("Dézoomer")
        zoom_out.clicked.connect(lambda: self.view.set_zoom(self.view.zoom / 1.2))
        zoom_in = QPushButton(make_icon("zoom_in"), "")
        zoom_in.setToolTip("Zoomer")
        zoom_in.clicked.connect(lambda: self.view.set_zoom(self.view.zoom * 1.2))
        reset = QPushButton(make_icon("reset"), "Réinitialiser")
        reset.setToolTip("Revenir au cadrage centré, sans zoom")
        reset.clicked.connect(lambda: self.view._set(zoom=1.0, cx=0.5, cy=0.5))

        controls = QHBoxLayout()
        controls.addWidget(zoom_out)
        controls.addWidget(self.slider, 1)
        controls.addWidget(zoom_in)
        controls.addWidget(self.zoom_label)
        controls.addSpacing(12)
        controls.addWidget(reset)

        hint = QLabel("Faites glisser la photo pour choisir la partie visible. "
                      "Molette ou curseur pour zoomer et dézoomer.")
        hint.setObjectName("hint")

        self.whole = False  # vrai si l'utilisateur choisit « Photo entière » (aucun recadrage)
        whole_button = QPushButton(make_icon("photo"), "Photo entière")
        whole_button.setToolTip("Annuler le recadrage : la photo est affichée en entier, sans être coupée")
        whole_button.clicked.connect(self._choose_whole)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.addButton(whole_button, QDialogButtonBox.ButtonRole.ResetRole)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Appliquer")
        set_primary(buttons.button(QDialogButtonBox.StandardButton.Ok))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.view, 1)
        layout.addWidget(hint)
        layout.addLayout(controls)
        layout.addWidget(buttons)
        self._sync()

    def _sync(self):
        self.slider.blockSignals(True)
        self.slider.setValue(round(self.view.zoom * 100))
        self.slider.blockSignals(False)
        self.zoom_label.setText(f"{round(self.view.zoom * 100)} %")

    def _choose_whole(self):
        self.whole = True
        self.accept()

    def crop(self):
        """Recadrage choisi, ou WHOLE_CROP pour « Photo entière » (même dans un cadre rempli par défaut)."""
        return dict(WHOLE_CROP) if self.whole else self.view.crop()


class EventsDialog(QDialog):
    """Liste des anniversaires et événements : ajout, modification, suppression, import et export CSV."""

    def __init__(self, events, year, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Anniversaires et événements")
        self.resize(820, 560)
        self.events = [dict(e) for e in events]
        self.year = year
        self.last_dir = getattr(parent, "last_dir", "")

        self.list = QListWidget()
        self.list.currentRowChanged.connect(self._load_selected)

        # Formulaire de l'événement sélectionné (ou du nouvel événement).
        self.date_edit = QDateEdit(QDate(year, 1, 1))
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        self.kind_combo = QComboBox()
        self.kind_combo.addItems([label for _kind, label in EVENT_KINDS])
        self.kind_combo.currentIndexChanged.connect(self._update_form)
        self.text_edit = QLineEdit()
        self.text_edit.setPlaceholderText("Ex. : Léa, Mariage de Paul et Zoé, Fête des voisins…")
        self.text_edit.returnPressed.connect(self._add_or_update)
        self.no_year_box = QCheckBox("Année de naissance inconnue (pas d'âge affiché)")
        self.hint = QLabel()
        self.hint.setObjectName("hint")
        self.hint.setWordWrap(True)

        form = QFormLayout()
        form.setSpacing(10)
        form.addRow("Type", self.kind_combo)
        form.addRow("Date", self.date_edit)
        form.addRow("", self.no_year_box)
        form.addRow("Texte", self.text_edit)

        self.add_button = QPushButton(make_icon("add"), "Ajouter")
        set_primary(self.add_button)
        self.add_button.clicked.connect(self._add_or_update)
        new_button = QPushButton("Nouveau")
        new_button.setToolTip("Vider le formulaire pour saisir un autre événement")
        new_button.clicked.connect(self._new)
        self.delete_button = QPushButton(make_icon("remove"), "Supprimer")
        self.delete_button.clicked.connect(self._delete)
        form_buttons = QHBoxLayout()
        form_buttons.addWidget(self.add_button)
        form_buttons.addWidget(new_button)
        form_buttons.addWidget(self.delete_button)

        import_button = QPushButton(make_icon("open"), "Importer…")
        import_button.setToolTip("Ajouter les événements d'un fichier CSV (exporté depuis ce logiciel ou "
                                 "écrit dans Excel : Date;Type;Description)")
        import_button.clicked.connect(self._import)
        export_button = QPushButton(make_icon("export"), "Exporter…")
        export_button.setToolTip("Enregistrer la liste dans un fichier CSV (ouvrable avec Excel), "
                                 "pour la réutiliser dans un autre calendrier")
        export_button.clicked.connect(self._export)
        file_buttons = QHBoxLayout()
        file_buttons.addWidget(import_button)
        file_buttons.addWidget(export_button)

        side = QVBoxLayout()
        side.addLayout(form)
        side.addWidget(self.hint)
        side.addLayout(form_buttons)
        side.addStretch()
        side.addLayout(file_buttons)

        center = QHBoxLayout()
        center.addWidget(self.list, 3)
        center.addSpacing(12)
        center.addLayout(side, 2)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Appliquer")
        set_primary(buttons.button(QDialogButtonBox.StandardButton.Ok))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        intro = QLabel("Les anniversaires et événements s'affichent dans les cases des jours du calendrier "
                       "(en rose les anniversaires, en vert les autres événements).")
        intro.setObjectName("hint")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        layout.addLayout(center, 1)
        layout.addWidget(buttons)
        self._refresh_list()
        self._new()

    def _kind(self):
        return EVENT_KINDS[self.kind_combo.currentIndex()][0]

    def _update_form(self):
        kind = self._kind()
        self.no_year_box.setVisible(kind == "birthday")
        self.hint.setText({
            "birthday": "Chaque année. Indiquez la date de naissance : l'âge est affiché, par exemple « Léa (9 ans) ».",
            "yearly": "Chaque année à la même date (l'année saisie n'est pas utilisée).",
            "once": "Une seule fois, à la date exacte.",
        }[kind])

    def _refresh_list(self, select=None):
        self.events.sort(key=lambda e: (e["month"], e["day"], e["text"].lower()))
        self.list.blockSignals(True)
        self.list.clear()
        for event in self.events:
            label = f"{event_date_text(event)}   {event['text']}   ·   {EVENT_KIND_LABELS[event['kind']]}"
            item = QListWidgetItem(make_icon("event" if event["kind"] == "birthday" else "event_other"), label)
            self.list.addItem(item)
        self.list.blockSignals(False)
        if select is not None and select in self.events:
            self.list.setCurrentRow(self.events.index(select))
        self.delete_button.setEnabled(self.list.currentRow() >= 0)

    def _load_selected(self, row):
        if row < 0:
            return
        event = self.events[row]
        self.kind_combo.setCurrentIndex([k for k, _l in EVENT_KINDS].index(event["kind"]))
        year = event["year"] or self.year
        if not QDate.isValid(year, event["month"], event["day"]):
            year = 2028  # 29 février sans année, une année non bissextile : année bissextile pour l'afficher
        self.date_edit.setDate(QDate(year, event["month"], event["day"]))
        self.no_year_box.setChecked(event["kind"] == "birthday" and not event["year"])
        self.text_edit.setText(event["text"])
        self.add_button.setText("Enregistrer la modification")
        self.delete_button.setEnabled(True)

    def _new(self):
        self.list.setCurrentRow(-1)
        self.list.clearSelection()
        self.text_edit.clear()
        self.no_year_box.setChecked(False)
        self.add_button.setText("Ajouter")
        self.delete_button.setEnabled(False)
        self._update_form()
        self.text_edit.setFocus()

    def _add_or_update(self):
        date = self.date_edit.date()
        kind = self._kind()
        keep_year = kind == "once" or (kind == "birthday" and not self.no_year_box.isChecked())
        event = clean_event({"day": date.day(), "month": date.month(), "year": date.year() if keep_year else None,
                             "text": self.text_edit.text(), "kind": kind})
        if event is None:
            self.text_edit.setFocus()
            return
        row = self.list.currentRow()
        if row >= 0:
            self.events[row] = event
        else:
            self.events.append(event)
        self._refresh_list(select=event if row >= 0 else None)
        if row < 0:
            self._new()  # prêt pour l'événement suivant

    def _delete(self):
        row = self.list.currentRow()
        if row >= 0:
            del self.events[row]
            self._refresh_list()
            self._new()

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importer des anniversaires et événements", self.last_dir,
                                              "Fichiers CSV (*.csv);;Tous les fichiers (*)")
        if not path:
            return
        try:
            imported, ignored = import_events_csv(path)
        except (OSError, UnicodeDecodeError) as exc:
            QMessageBox.critical(self, "Erreur", f"Impossible de lire le fichier :\n{exc}")
            return
        new = [e for e in imported if e not in self.events]
        self.events += new
        self._refresh_list()
        message = f"{len(new)} événement(s) ajouté(s)."
        if len(imported) > len(new):
            message += f"\n{len(imported) - len(new)} déjà dans la liste (non dupliqué(s))."
        if ignored:
            message += f"\n{ignored} ligne(s) illisible(s) ignorée(s) (date au format jj/mm ou jj/mm/aaaa attendue)."
        QMessageBox.information(self, "Import terminé", message)

    def _export(self):
        if not self.events:
            QMessageBox.information(self, "Rien à exporter", "La liste est vide.")
            return
        default = os.path.join(self.last_dir, "Anniversaires et événements.csv")
        path, _ = QFileDialog.getSaveFileName(self, "Exporter les anniversaires et événements", default,
                                              "Fichiers CSV (*.csv)")
        if not path:
            return
        try:
            export_events_csv(self.events, path)
        except OSError as exc:
            QMessageBox.critical(self, "Erreur", f"Impossible d'écrire le fichier :\n{exc}")
            return
        QMessageBox.information(self, "Export terminé",
                                f"{len(self.events)} événement(s) exporté(s) dans :\n{path}\n\n"
                                "Le fichier s'ouvre avec Excel et peut être réimporté dans un autre calendrier.")


def layout_icon(count):
    """Pictogramme d'une disposition : les cadres des photos, comme sur la page."""
    pixmap = QPixmap(48, 48)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(SLATE))
    area = QRectF(4, 12, 40, 26) if count == 1 else QRectF(4, 6, 40, 36)
    for frame in split_frame(area, count, 4):
        painter.drawRoundedRect(frame, 3, 3)
    painter.end()
    return QIcon(pixmap)


class SlotCard(QFrame):
    """Vignette d'une page (couverture ou mois) : disposition, choix des photos, clic pour l'aperçu."""

    selected = Signal(int)
    choose = Signal(int, int)  # page, emplacement (0 à 3)
    crop = Signal(int, int)  # page, emplacement
    cleared = Signal(int)
    dropped = Signal(int, int, list)  # page, emplacement visé, chemins
    layout_changed = Signal(int, int)  # page, nombre de photos

    THUMB = QSize(176, 112)
    GAP = 4  # écart entre les photos sur la vignette

    def __init__(self, index):
        super().__init__()
        self.index = index
        self.count = 1
        self.setObjectName("slot")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.title = QLabel()
        self.title.setObjectName("slotTitle")
        title_row = QHBoxLayout()
        title_row.setSpacing(4)
        title_row.addWidget(self.title, 1)
        # Disposition de la page : un bouton (pictogramme de la disposition actuelle) qui ouvre la liste.
        self.layout_button = QPushButton()
        self.layout_button.setToolTip("Disposition de la page : nombre et arrangement des photos")
        self.layout_button.setIconSize(QSize(20, 20))
        self.layout_button.setFixedSize(36, 26)
        self.layout_button.setObjectName("layoutButton")
        self.layout_button.clicked.connect(self._layout_menu)
        title_row.addWidget(self.layout_button)

        self.thumb = QLabel()
        self.thumb.setFixedSize(self.THUMB)
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb.setToolTip("Double-clic : recadrer la photo")

        self.choose_buttons = []
        buttons = QHBoxLayout()
        buttons.setSpacing(6)
        for slot in (0, 1):
            button = QPushButton()
            button.setStyleSheet("padding: 7px 4px;")  # trois boutons doivent tenir sous la vignette
            button.clicked.connect(lambda _=False, s=slot: self._choose_clicked(s))
            buttons.addWidget(button, 1)
            self.choose_buttons.append(button)
        self.clear_button = QPushButton(make_icon("remove"), "")
        self.clear_button.setToolTip("Retirer les photos de cette page")
        self.clear_button.setFixedWidth(38)
        self.clear_button.clicked.connect(lambda: self.cleared.emit(self.index))
        buttons.addWidget(self.clear_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)
        layout.addLayout(title_row)
        layout.addWidget(self.thumb)
        layout.addLayout(buttons)

    def _layout_menu(self):
        menu = QMenu(self)
        for count, text in LAYOUT_NAMES.items():
            action = menu.addAction(layout_icon(count), text)
            action.setCheckable(True)
            action.setChecked(count == self.count)
            action.triggered.connect(lambda _=False, c=count: self.layout_changed.emit(self.index, c))
        menu.exec(self.layout_button.mapToGlobal(self.layout_button.rect().bottomLeft()))

    def _choose_clicked(self, slot):
        if self.count <= 2:
            self.choose.emit(self.index, slot)
            return
        # 3 ou 4 photos : le bouton « Photos… » propose chaque emplacement.
        menu = QMenu(self)
        for i, name in enumerate(SLOT_NAMES[self.count]):
            menu.addAction(f"Photo {name}…", lambda s=i: self.choose.emit(self.index, s))
        button = self.choose_buttons[0]
        menu.exec(button.mapToGlobal(button.rect().bottomLeft()))

    def set_content(self, title, images, count, crops, whole):
        """images : vignettes des photos (None si absente) ; count : nombre de photos (1 à 4) ;
        crops : recadrages ; whole : photos affichées entières (sinon elles remplissent le cadre)."""
        self.count = count
        self.title.setText(title)
        self.layout_button.setIcon(layout_icon(count))

        first, second = self.choose_buttons
        if count == 1:
            first.setIcon(make_icon("photo"))
            first.setText("Choisir…")
            first.setToolTip("Choisir la photo de cette page (ou glissez-déposez une image ici)")
            second.hide()
        elif count == 2:
            first.setIcon(QIcon())
            first.setText("Gauche…")
            first.setToolTip("Choisir la photo de gauche")
            second.setText("Droite…")
            second.setToolTip("Choisir la photo de droite")
            second.show()
        else:
            first.setIcon(make_icon("photo"))
            first.setText("Photos…")
            first.setToolTip("Choisir une des photos de cette page (ou glissez-déposez des images sur la vignette)")
            second.hide()

        pixmap = QPixmap(self.THUMB)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        font = QFont("Segoe UI")
        font.setPixelSize(12)
        painter.setFont(font)
        for slot, (rect, image, crop) in enumerate(zip(self._frames(), images, crops)):
            if image is not None:
                draw_in_frame(painter, rect, image, crop, whole and slot_whole(count, slot), 8)
                continue
            clip = QPainterPath()
            clip.addRoundedRect(rect, 8, 8)
            painter.save()
            painter.setClipPath(clip)
            painter.fillRect(rect, QColor("#eef1f5"))
            painter.setPen(QColor("#94a3b8"))
            if count == 1:
                text = "Cliquez sur « Choisir… »\nou déposez une photo"
            elif rect.height() > 60:
                text = "Déposez\nune photo"
            else:
                text = "+"  # petit cadre (3 ou 4 photos)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
            painter.restore()
        painter.end()
        self.thumb.setPixmap(pixmap)
        self.clear_button.setEnabled(any(image is not None for image in images))

    def _frames(self):
        """Cadres des photos sur la vignette."""
        return split_frame(QRectF(0, 0, self.THUMB.width(), self.THUMB.height()), self.count, self.GAP)

    def _slot_at(self, pos):
        """Emplacement sous la position donnée (en coordonnées de la carte) : le cadre le plus proche."""
        local = QPointF(pos) - QPointF(self.thumb.geometry().topLeft())
        frames = self._frames()
        for slot, frame in enumerate(frames):
            if frame.contains(local):
                return slot
        distances = [(frame.center() - local).manhattanLength() for frame in frames]
        return distances.index(min(distances))

    def set_selected(self, selected):
        self.setProperty("selected", selected)
        repolish(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.index)

    def mouseDoubleClickEvent(self, event):
        # Photo présente : recadrage ; emplacement vide : choix d'une photo.
        self.crop.emit(self.index, self._slot_at(event.position()))

    @staticmethod
    def _image_paths(event):
        return [
            url.toLocalFile() for url in event.mimeData().urls()
            if url.isLocalFile() and url.toLocalFile().lower().endswith(IMAGE_EXTENSIONS)
        ]

    def dragEnterEvent(self, event):
        if self._image_paths(event):
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = self._image_paths(event)
        if paths:
            event.acceptProposedAction()
            self.dropped.emit(self.index, self._slot_at(event.position()), paths)


class CalendarWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1440, 900)
        self.settings = Settings()
        self.cache = ImageCache()
        self.photos = {}  # "cover" ou 0..11 -> [photo 1, …, photo 4] (chemins ou None)
        self.layouts = {}  # "cover" ou 0..11 -> nombre de photos de la page (1 à 4)
        self.crops = {}  # "cover" ou 0..11 -> [recadrage 1, …, recadrage 4] ({"zoom", "x", "y"} ou None)
        self.current = 0  # page affichée dans l'aperçu
        self.project_path = None
        self.cards = []
        self.last_dir = os.path.dirname(os.path.abspath(__file__))
        # Annuler / rétablir : états successifs du projet (texte JSON, voir _state).
        self.undo_stack = []
        self.redo_stack = []
        self._last_state = None  # état affiché ; chaque changement empile l'état précédent
        self._typing = False  # frappe du titre en cours : une seule étape d'annulation pour tout le mot
        self.preferences = QSettings(APP_NAME, APP_NAME)  # projets récents (registre de Windows)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        layout.addWidget(self._settings_panel())
        layout.addWidget(self._slots_panel(), 0)
        layout.addWidget(self._preview_panel(), 1)
        self.setCentralWidget(central)

        self._create_menu()
        self.statusBar().showMessage(
            "Astuce : glissez des photos sur les vignettes, double-cliquez sur une photo pour la recadrer. "
            "Export PDF : menu Fichier (Ctrl+E).")
        for combo in self.findChildren(QComboBox):
            polish_combo(combo)
        self.saved_state = self._state()  # état de la dernière sauvegarde (ici : calendrier vierge)
        self.refresh()

        # Sauvegarde automatique : copie de secours régulière, proposée au prochain lancement
        # si le logiciel s'est fermé sans que le projet soit sauvegardé.
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(AUTOSAVE_INTERVAL_MS)
        self.autosave_timer.timeout.connect(self.autosave)
        self.autosave_timer.start()

    # --- Construction de l'interface ------------------------------------

    def _panel(self, title):
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(12)
        label = QLabel(title)
        label.setObjectName("sectionTitle")
        layout.addWidget(label)
        return panel, layout

    def _settings_panel(self):
        panel, outer = self._panel("Réglages")
        panel.setFixedWidth(322)  # 300 + la barre de défilement
        # Réglages compacts : ils tiennent sans défiler sur un écran de 1080 pixels de haut. Sur un écran
        # plus petit, ils défilent dans le panneau (sinon Qt écraserait les champs les uns sur les autres).
        content = QWidget()
        content.setObjectName("slots")  # fond transparent
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(8)
        s = self.settings

        project_row = QHBoxLayout()
        project_row.setSpacing(6)
        import_button = QPushButton(make_icon("open"), "Importer…")
        import_button.setToolTip("Reprendre un projet de calendrier sauvegardé (Ctrl+O)")
        import_button.clicked.connect(self.open_project)
        save_button = QPushButton(make_icon("save"), "Sauvegarder")
        save_button.setToolTip("Sauvegarder le projet en cours pour le reprendre plus tard (Ctrl+S) :\n"
                               "réglages, photos, dispositions et recadrages")
        save_button.clicked.connect(self.save_project)
        project_row.addWidget(import_button)
        project_row.addWidget(save_button)
        layout.addLayout(project_row)

        self.title_edit = QLineEdit(s.title)
        self.title_edit.textChanged.connect(self._on_settings_changed)
        self.year_combo = QComboBox()
        self.year_combo.addItems([str(y) for y in range(datetime.date.today().year - 2, datetime.date.today().year + 11)])
        self._set_year(s.year)
        self.year_combo.currentIndexChanged.connect(self._on_settings_changed)
        self.format_combo = QComboBox()
        self.format_combo.addItems([f[0] for f in FORMATS])
        self.format_combo.currentIndexChanged.connect(self._on_settings_changed)
        self.font_combo = QComboBox()
        self.font_combo.addItems([f[0] for f in FONTS])
        self.font_combo.currentIndexChanged.connect(self._on_settings_changed)
        self.color_button = QPushButton()
        self.color_button.setIconSize(QSize(20, 20))
        self.color_button.setStyleSheet("text-align: left;")
        self.color_button.setToolTip("Couleur des titres, des week-ends et des jours fériés")
        self.color_button.clicked.connect(self.choose_color)

        form = QFormLayout()
        form.setSpacing(7)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.addRow("Titre", self.title_edit)
        form.addRow("Année", self.year_combo)
        form.addRow("Format", self.format_combo)
        form.addRow("Police", self.font_combo)
        form.addRow("Couleur", self.color_button)
        self.zone_combo = QComboBox()
        self.zone_combo.addItems([label for label, _zone in SCHOOL_ZONE_CHOICES])
        self.zone_combo.setToolTip(
            "Vacances scolaires (France métropolitaine) : un bandeau de couleur en bas des jours de vacances.\n"
            "Dates officielles de l'Éducation nationale, publiées jusqu'à l'été 2028."
        )
        self.zone_combo.setCurrentIndex(self._zone_index(s.school_zone))
        self.zone_combo.currentIndexChanged.connect(self._on_settings_changed)
        form.addRow("Vacances", self.zone_combo)
        layout.addLayout(form)

        # Cases sur deux colonnes (libellés courts, texte complet au survol).
        self.cover_box = QCheckBox("Couverture")
        self.holidays_box = QCheckBox("Jours fériés")
        self.weekends_box = QCheckBox("Week-ends colorés")
        self.week_numbers_box = QCheckBox("N° de semaine")
        boxes = QGridLayout()
        boxes.setHorizontalSpacing(8)
        boxes.setVerticalSpacing(6)
        for n, (box, value, tooltip) in enumerate((
            (self.cover_box, s.cover, "Page de couverture avec le titre et l'année"),
            (self.holidays_box, s.holidays, "Jours fériés (France métropolitaine)"),
            (self.weekends_box, s.weekends, "Samedis et dimanches en couleur"),
            (self.week_numbers_box, s.week_numbers, "Numéros de semaine à gauche de la grille"),
        )):
            box.setChecked(value)
            box.setToolTip(tooltip)
            box.toggled.connect(self._on_settings_changed)
            boxes.addWidget(box, n // 2, n % 2)
        layout.addSpacing(2)
        layout.addLayout(boxes)

        # Anniversaires et événements : affichage (case) et liste (bouton).
        self.events_box = QCheckBox("Anniversaires")
        self.events_box.setToolTip("Afficher les anniversaires et événements dans les cases des jours")
        self.events_box.setChecked(s.show_events)
        self.events_box.toggled.connect(self._on_settings_changed)
        self.events_button = QPushButton(make_icon("event"), "Gérer…")
        self.events_button.setToolTip("Ajouter, modifier, importer ou exporter les anniversaires et événements")
        self.events_button.clicked.connect(self.edit_events)
        events_row = QHBoxLayout()
        events_row.addWidget(self.events_box, 1)
        events_row.addWidget(self.events_button)
        layout.addLayout(events_row)

        layout.addSpacing(4)
        auto_button = QPushButton(make_icon("auto"), "Remplir automatiquement…")
        auto_button.setToolTip(
            "Sélectionnez toutes les photos des mois : elles sont classées de la plus ancienne à la plus récente,\n"
            "et la disposition de chaque page (1 à 4 photos) est choisie pour les utiliser toutes,\n"
            "en plaçant portraits et paysages dans les cadres de leur format. La couverture n'est pas modifiée."
        )
        set_primary(auto_button)
        auto_button.clicked.connect(self.auto_fill)
        layout.addWidget(auto_button)

        fill_button = QPushButton(make_icon("add"), "Ajouter des photos…")
        fill_button.setToolTip("Sélectionnez plusieurs photos : elles remplissent les mois vides dans l'ordre\n"
                               "(la couverture n'est pas modifiée)")
        fill_button.clicked.connect(self.add_photos)
        layout.addWidget(fill_button)

        layout.addStretch()  # l'astuce d'utilisation est affichée dans la barre d'état au démarrage

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Sélecteur limité au fond de la zone : un style sans sélecteur s'appliquerait aussi aux
        # boutons et cases qu'elle contient (bouton principal sans fond, cases sans cadre).
        scroll.viewport().setStyleSheet("#qt_scrollarea_viewport { background: transparent; }")
        outer.addWidget(scroll, 1)

        # L'export PDF se fait par le menu Fichier (Ctrl+E).
        print_button = QPushButton(make_icon("print"), "Imprimer…")
        print_button.setMinimumHeight(40)
        print_button.setToolTip("Imprimer le calendrier (Ctrl+P) ; export PDF : menu Fichier (Ctrl+E)")
        print_button.clicked.connect(self.print_calendar)
        outer.addWidget(print_button)
        return panel

    def _slots_panel(self):
        panel, layout = self._panel("Photos")
        self.slots_grid = QGridLayout()
        self.slots_grid.setSpacing(12)
        holder = QWidget()
        holder.setObjectName("slots")
        holder_layout = QVBoxLayout(holder)
        holder_layout.setContentsMargins(0, 0, 6, 0)
        holder_layout.addLayout(self.slots_grid)
        holder_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(holder)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Sélecteur limité au fond de la zone : sans lui, le style s'appliquerait aussi aux menus des
        # vignettes (liste des dispositions affichée en noir).
        scroll.viewport().setStyleSheet("#qt_scrollarea_viewport { background: transparent; }")
        layout.addWidget(scroll)
        panel.setFixedWidth(2 * (SlotCard.THUMB.width() + 26) + 12 + 36 + 18)
        return panel

    def _preview_panel(self):
        panel, layout = self._panel("Aperçu")
        self.preview = PreviewWidget(self)
        layout.addWidget(self.preview, 1)

        previous_button = QPushButton(make_icon("previous"), "")
        previous_button.setToolTip("Page précédente (Page préc.)")
        previous_button.clicked.connect(lambda: self.select_page(self.current - 1))
        next_button = QPushButton(make_icon("next"), "")
        next_button.setToolTip("Page suivante (Page suiv.)")
        next_button.clicked.connect(lambda: self.select_page(self.current + 1))
        self.page_label = QLabel()
        self.page_label.setObjectName("hint")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.crop_button = QPushButton(make_icon("crop"), "Recadrer…")
        self.crop_button.setToolTip("Recadrer la photo de cette page (ou double-cliquez sur la photo)")
        self.crop_button.clicked.connect(self._crop_from_button)
        self.sheet_button = QPushButton(make_icon("sheet"), "Vue d'ensemble")
        self.sheet_button.setCheckable(True)
        self.sheet_button.setToolTip("Voir toutes les pages en miniature (Ctrl+T) ; cliquez sur une page "
                                     "pour l'afficher en grand")
        self.sheet_button.toggled.connect(self.set_sheet)
        nav = QHBoxLayout()
        nav.addStretch()
        nav.addWidget(previous_button)
        nav.addWidget(self.page_label)
        nav.addWidget(next_button)
        nav.addSpacing(16)
        nav.addWidget(self.crop_button)
        nav.addWidget(self.sheet_button)
        nav.addStretch()
        self.page_label.setMinimumWidth(180)
        layout.addLayout(nav)
        return panel

    def _create_menu(self):
        file_menu = self.menuBar().addMenu("&Fichier")
        for spec in (
            ("new", "&Nouveau calendrier", QKeySequence.StandardKey.New, self.new_project),
            ("open", "&Importer un projet…", QKeySequence.StandardKey.Open, self.open_project),
            ("save", "&Sauvegarder le projet", QKeySequence.StandardKey.Save, self.save_project),
            ("save", "Sauvegarder le projet s&ous…", QKeySequence.StandardKey.SaveAs, self.save_project_as),
            None,
            ("photo", "&Remplir automatiquement…", "Ctrl+Shift+I", self.auto_fill),
            ("add", "&Ajouter des photos…", "Ctrl+I", self.add_photos),
            ("pdf", "E&xporter en PDF…", "Ctrl+E", self.export_pdf),
            ("print", "&Imprimer…", QKeySequence.StandardKey.Print, self.print_calendar),
            None,
        ):
            if spec is None:
                file_menu.addSeparator()
                continue
            icon, text, shortcut, slot = spec
            action = QAction(make_icon(icon) if icon != "pdf" else QIcon(), text, self)
            action.setShortcut(shortcut)
            action.triggered.connect(lambda _=False, s=slot: s())
            file_menu.addAction(action)
            if slot == self.open_project:
                self.recent_menu = file_menu.addMenu("Projets &récents")
                self.recent_menu.aboutToShow.connect(self._fill_recent_menu)
        quit_action = QAction("&Quitter", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        edit_menu = self.menuBar().addMenu("&Édition")
        self.undo_action = QAction(make_icon("undo"), "&Annuler", self)
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.undo_action.triggered.connect(self.undo)
        edit_menu.addAction(self.undo_action)
        self.redo_action = QAction(make_icon("redo"), "&Rétablir", self)
        self.redo_action.setShortcuts([QKeySequence("Ctrl+Y"), QKeySequence("Ctrl+Shift+Z")])
        self.redo_action.triggered.connect(self.redo)
        edit_menu.addAction(self.redo_action)

        view_menu = self.menuBar().addMenu("&Affichage")
        self.sheet_action = QAction(make_icon("sheet"), "&Vue d'ensemble (toutes les pages)", self)
        self.sheet_action.setShortcut("Ctrl+T")
        self.sheet_action.setCheckable(True)
        self.sheet_action.toggled.connect(self.set_sheet)
        view_menu.addAction(self.sheet_action)

        help_menu = self.menuBar().addMenu("&Aide")
        about_action = QAction(f"À &propos de {APP_NAME}…", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        for key, step in ((Qt.Key.Key_PageUp, -1), (Qt.Key.Key_PageDown, 1)):
            action = QAction(self)
            action.setShortcut(key)
            action.triggered.connect(lambda _=False, s=step: self.select_page(self.current + s))
            self.addAction(action)

    def show_about(self):
        QMessageBox.about(
            self,
            f"À propos de {APP_NAME}",
            f"<h2 style='color:{ACCENT}; margin-bottom:0;'>{APP_NAME}</h2>"
            f"<p style='margin-top:4px;'><b>Version {APP_VERSION}</b> — {APP_DATE}</p>"
            "<p>Création de calendriers photo : une à quatre photos par mois, remplissage automatique "
            "par date et par format, recadrage, jours fériés, vacances scolaires, numéros de semaine, "
            "couverture, vue d'ensemble, annulation, sauvegarde automatique, export PDF et impression.</p>"
            f"<p>Application écrite par <b>{APP_AUTHOR}</b><br>"
            f"<span style='color:{SLATE};'>Modèle : {APP_AUTHOR_MODEL}</span><br>"
            f"sous le commandement de <b>{APP_DIRECTOR}</b>.</p>",
        )

    # --- État ------------------------------------------------------------

    def renderer(self):
        return CalendarRenderer(self.settings, self.photos, self.layouts, self.crops, self.cache)

    def _page_key(self, index):
        """Clé de la photo d'une page : "cover" ou numéro du mois dans le calendrier."""
        return "cover" if self.settings.cover and index == 0 else index - (1 if self.settings.cover else 0)

    def _page_title(self, index):
        kind, value = self.settings.pages()[index]
        if kind == "cover":
            return "Couverture"
        year, month = value
        return f"{MONTHS[month - 1]} {year}"

    def _slot_title(self, index, slot):
        """Nom d'un emplacement de photo : « Mars 2027 », ou « Mars 2027 (en haut à droite) »."""
        count = self.layouts.get(self._page_key(index), 1)
        title = self._page_title(index)
        return f"{title} ({SLOT_NAMES[count][slot]})" if count > 1 else title

    @staticmethod
    def _zone_index(zone):
        return next(i for i, (_label, z) in enumerate(SCHOOL_ZONE_CHOICES) if z == zone)

    def _on_settings_changed(self):
        s = self.settings
        s.title = self.title_edit.text()
        s.year = int(self.year_combo.currentText())
        s.format_index = self.format_combo.currentIndex()
        s.font_index = self.font_combo.currentIndex()
        s.cover = self.cover_box.isChecked()
        s.holidays = self.holidays_box.isChecked()
        s.weekends = self.weekends_box.isChecked()
        s.school_zone = SCHOOL_ZONE_CHOICES[self.zone_combo.currentIndex()][1]
        s.week_numbers = self.week_numbers_box.isChecked()
        s.show_events = self.events_box.isChecked()
        self.refresh()

    def edit_events(self):
        dialog = EventsDialog(self.settings.events, self.settings.year, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.settings.events = dialog.events
            if dialog.events and not self.settings.show_events:
                self.events_box.setChecked(True)  # appelle _on_settings_changed, donc refresh
            else:
                self.refresh()
            count = len(dialog.events)
            self.statusBar().showMessage(f"{count} anniversaire(s) et événement(s) dans le calendrier.", 5000)

    def _set_year(self, year):
        """Sélectionne l'année dans la liste (en l'ajoutant si un projet ancien l'exige)."""
        if self.year_combo.findText(str(year)) < 0:
            years = sorted({int(self.year_combo.itemText(i)) for i in range(self.year_combo.count())} | {year})
            self.year_combo.clear()
            self.year_combo.addItems([str(y) for y in years])
        self.year_combo.setCurrentText(str(year))

    def _sync_widgets(self):
        """Recopie les réglages dans les champs (après ouverture d'un projet)."""
        s = self.settings
        widgets = (self.title_edit, self.year_combo, self.format_combo, self.font_combo,
                   self.cover_box, self.holidays_box, self.weekends_box,
                   self.zone_combo, self.week_numbers_box, self.events_box)
        for widget in widgets:
            widget.blockSignals(True)
        self.title_edit.setText(s.title)
        self._set_year(s.year)
        self.format_combo.setCurrentIndex(s.format_index)
        self.font_combo.setCurrentIndex(s.font_index)
        self.cover_box.setChecked(s.cover)
        self.holidays_box.setChecked(s.holidays)
        self.weekends_box.setChecked(s.weekends)
        self.zone_combo.setCurrentIndex(self._zone_index(s.school_zone))
        self.week_numbers_box.setChecked(s.week_numbers)
        self.events_box.setChecked(s.show_events)
        for widget in widgets:
            widget.blockSignals(False)

    def refresh(self):
        """Met à jour vignettes, couleur et aperçu après un changement."""
        self.color_button.setText(self.settings.accent.name().upper())
        self.color_button.setIcon(color_icon(self.settings.accent))

        count = len(self.settings.pages())
        while len(self.cards) < count:
            card = SlotCard(len(self.cards))
            card.selected.connect(self.select_page)
            card.choose.connect(self.choose_photo)
            card.cleared.connect(self.clear_photo)
            card.dropped.connect(self.drop_photos)
            card.layout_changed.connect(self.set_layout)
            card.crop.connect(self.crop_photo)
            self.cards.append(card)
        renderer = self.renderer()
        for i, card in enumerate(self.cards):
            self.slots_grid.removeWidget(card)
            card.setVisible(i < count)
            if i < count:
                self.slots_grid.addWidget(card, i // 2, i % 2)
                key = self._page_key(i)
                images = [self.cache.get(p, 256) if p else None for p in renderer.page_photos(key)]
                card.set_content(self._page_title(i), images, self.layouts.get(key, 1), renderer.page_crops(key),
                                 self.settings.whole_photos)

        self.current = min(self.current, count - 1)
        for i, card in enumerate(self.cards):
            card.set_selected(i == self.current)
        self.page_label.setText(f"{self._page_title(self.current)}  ·  page {self.current + 1} sur {count}")
        self.crop_button.setEnabled(any(renderer.page_photos(self._page_key(self.current))))
        self.preview.update()
        self._record_state()
        self._update_title()  # astérisque si des changements ne sont pas sauvegardés

    def select_page(self, index):
        count = len(self.settings.pages())
        self.current = max(0, min(count - 1, index))
        self.refresh()

    # --- Vue d'ensemble ------------------------------------------------------

    def set_sheet(self, sheet):
        """Bascule entre l'aperçu d'une page et la planche de toutes les pages."""
        for widget in (self.sheet_button, self.sheet_action):
            widget.blockSignals(True)
            widget.setChecked(sheet)
            widget.blockSignals(False)
        self.preview.set_sheet(sheet)

    def open_from_sheet(self, index):
        self.set_sheet(False)
        self.select_page(index)

    # --- Annuler / rétablir ----------------------------------------------

    @staticmethod
    def _title_only_change(before, after):
        """Vrai si seul le titre diffère entre deux états (frappe en cours dans le champ Titre)."""
        before, after = json.loads(before), json.loads(after)
        before["settings"].pop("title", None)
        after["settings"].pop("title", None)
        return before == after

    def _record_state(self):
        """Empile l'état précédent si le projet a changé depuis le dernier affichage."""
        state = self._state()
        if self._last_state is not None and state != self._last_state:
            typing = self._title_only_change(self._last_state, state)
            if not (typing and self._typing):  # les lettres d'un même titre forment une seule étape
                self.undo_stack.append(self._last_state)
                del self.undo_stack[:-MAX_UNDO]
            self._typing = typing
            self.redo_stack.clear()
        self._last_state = state
        self.undo_action.setEnabled(bool(self.undo_stack))
        self.redo_action.setEnabled(bool(self.redo_stack))

    def _reset_history(self):
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._last_state = None
        self._typing = False

    def _apply_state(self, state):
        self.settings, self.photos, self.layouts, self.crops = self._parse_project(json.loads(state))
        self._last_state = state
        self._typing = False
        self._sync_widgets()
        self.refresh()

    def undo(self):
        if not self.undo_stack:
            return
        self.redo_stack.append(self._last_state)
        self._apply_state(self.undo_stack.pop())
        self.statusBar().showMessage("Modification annulée (Ctrl+Y pour la rétablir).", 3000)

    def redo(self):
        if not self.redo_stack:
            return
        self.undo_stack.append(self._last_state)
        self._apply_state(self.redo_stack.pop())
        self.statusBar().showMessage("Modification rétablie.", 3000)

    # --- Photos ----------------------------------------------------------

    def _get_photo(self, index, slot):
        return padded(self.photos.get(self._page_key(index)))[slot]

    def _set_photo(self, index, slot, path):
        key = self._page_key(index)
        paths = self.photos[key] = padded(self.photos.get(key))
        if paths[slot] != (path or None):
            self._set_crop(index, slot, None)  # nouvelle photo : cadrage par défaut
        paths[slot] = path or None
        if not any(paths):
            del self.photos[key]

    def _set_crop(self, index, slot, crop):
        key = self._page_key(index)
        crops = self.crops[key] = padded(self.crops.get(key))
        crops[slot] = crop
        if not any(crops):
            del self.crops[key]

    def crop_photo(self, index, slot):
        """Ouvre l'outil de recadrage (ou le choix d'une photo si l'emplacement est vide)."""
        path = self._get_photo(index, slot)
        if path is None:
            self.choose_photo(index, slot)
            return
        image = self.cache.get(path, 2048)
        if image is None:
            QMessageBox.warning(self, "Photo introuvable", f"Impossible de lire la photo :\n{path}")
            return
        renderer = self.renderer()
        frame = renderer.photo_frames(index, 1000, 1000 * renderer.page_ratio())[slot]
        crops = padded(self.crops.get(self._page_key(index)))
        dialog = CropDialog(image, frame.width() / frame.height(), crops[slot], self._slot_title(index, slot), self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._set_crop(index, slot, dialog.crop())
            self.current = index
            self.refresh()

    def _crop_from_button(self):
        index = self.current
        filled = [slot for slot, path in enumerate(self.renderer().page_photos(self._page_key(index))) if path]
        if len(filled) == 1:
            self.crop_photo(index, filled[0])
            return
        names = SLOT_NAMES[self.layouts.get(self._page_key(index), 1)]
        menu = QMenu(self)
        for slot in filled:
            menu.addAction(f"Photo {names[slot]}", lambda s=slot: self.crop_photo(index, s))
        menu.exec(self.crop_button.mapToGlobal(self.crop_button.rect().bottomLeft()))

    def _positions(self):
        """Emplacements de photo de toutes les pages, dans l'ordre : (page, emplacement)."""
        return [
            (i, slot)
            for i in range(len(self.settings.pages()))
            for slot in range(self.layouts.get(self._page_key(i), 1))
        ]

    def _fill(self, positions, paths):
        for (index, slot), path in zip(positions, paths):
            self._set_photo(index, slot, path)

    def _check_duplicates(self, paths, replaced=()):
        """Prévient si des photos à importer sont déjà dans le calendrier (ou en double dans la sélection).

        replaced : emplacements (page, emplacement) qui vont être remplacés, donc non comptés.
        Renvoie les photos à importer (toutes, ou sans les doublons), ou None si l'utilisateur annule.
        """
        replaced = set(replaced)
        used = [(i, slot, path) for i, slot in self._positions()
                if (i, slot) not in replaced and (path := self._get_photo(i, slot))]
        duplicates = []  # (photo, où elle est déjà)
        accepted = []
        for path in paths:
            where = next((self._slot_title(i, slot) for i, slot, other in used if same_photo(path, other)), None)
            if where is None and any(same_photo(path, other) for other in accepted):
                where = "déjà dans cette sélection"
            if where is None:
                accepted.append(path)
            else:
                duplicates.append((path, where))
        if not duplicates:
            return list(paths)

        lines = "\n".join(f"• {os.path.basename(path)} — {where}" for path, where in duplicates[:12])
        if len(duplicates) > 12:
            lines += f"\n• … et {len(duplicates) - 12} autre(s)"
        single = len(paths) == 1
        box = QMessageBox(QMessageBox.Icon.Warning, "Photo déjà utilisée",
                          ("Cette photo est déjà dans le calendrier :" if single else
                           f"{len(duplicates)} photo(s) sur {len(paths)} sont déjà dans le calendrier :")
                          + f"\n\n{lines}\n\n(Une copie identique sous un autre nom compte aussi.)", parent=self)
        skip = None if single else box.addButton("Ignorer ces photos", QMessageBox.ButtonRole.AcceptRole)
        use = box.addButton("Utiliser quand même", QMessageBox.ButtonRole.YesRole)
        cancel = box.addButton("Annuler", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(skip or cancel)
        box.setEscapeButton(cancel)
        box.exec()
        clicked = box.clickedButton()
        if clicked is use:
            return list(paths)
        if skip is not None and clicked is skip:
            return accepted
        return None

    def set_layout(self, index, count):
        self.layouts[self._page_key(index)] = count
        self.current = index
        self.refresh()

    def choose_photo(self, index, slot):
        title = self._slot_title(index, slot)
        path, _ = QFileDialog.getOpenFileName(self, f"Photo : {title}", self.last_dir, IMAGE_FILTER)
        if path:
            self.last_dir = os.path.dirname(path)
            if not self._check_duplicates([path], replaced=[(index, slot)]):
                return
            self._set_photo(index, slot, path)
            self.current = index
            self.refresh()

    def clear_photo(self, index):
        self.photos.pop(self._page_key(index), None)
        self.crops.pop(self._page_key(index), None)
        self.current = index
        self.refresh()

    def drop_photos(self, index, slot, paths):
        """Une photo déposée va à l'emplacement visé ; plusieurs remplissent les suivants."""
        positions = self._positions()
        targets = positions[positions.index((index, slot)):]
        paths = self._check_duplicates(paths, replaced=targets[:len(paths)])
        if not paths:
            return
        self._fill(targets, paths)
        self.current = index
        self.refresh()

    def add_photos(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Ajouter des photos", self.last_dir, IMAGE_FILTER)
        if not paths:
            return
        self.last_dir = os.path.dirname(paths[0])
        # Les mois seulement : la couverture se choisit à part (vignette « Couverture »).
        positions = [p for p in self._positions() if self._page_key(p[0]) != "cover"]
        empty = [p for p in positions if self._get_photo(*p) is None]
        order = empty + [p for p in positions if p not in empty]  # puis remplacement dans l'ordre
        paths = self._check_duplicates(paths, replaced=order[:len(paths)])
        if not paths:
            return
        self._fill(order, paths)
        message = f"{min(len(paths), len(positions))} photo(s) placée(s)."
        if len(paths) > len(positions):
            message += f" {len(paths) - len(positions)} photo(s) en trop ignorée(s)."
        self.statusBar().showMessage(message, 6000)
        self.refresh()

    def auto_fill(self):
        """Place toutes les photos sélectionnées sur les mois, par date et selon leur format."""
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Photos à répartir sur les mois (la couverture n'est pas modifiée)", self.last_dir, IMAGE_FILTER
        )
        if not paths:
            return
        self.last_dir = os.path.dirname(paths[0])
        month_keys = [self._page_key(i) for i in range(len(self.settings.pages())) if self._page_key(i) != "cover"]
        if any(key in self.photos for key in month_keys):
            answer = QMessageBox.question(
                self, "Remplacer les photos des mois ?",
                "Des mois ont déjà des photos. Elles seront remplacées (la couverture est conservée).\n\nContinuer ?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        # Les photos des mois sont remplacées : seule la couverture peut déjà contenir une photo importée.
        month_positions = [p for p in self._positions() if self._page_key(p[0]) != "cover"]
        paths = self._check_duplicates(paths, replaced=month_positions)
        if not paths:
            return

        # Forme des cadres de chaque disposition, pour le format de page choisi (portrait ou paysage).
        renderer = self.renderer()
        area = renderer._areas("month", 1000, 1000 * renderer.page_ratio())[0]
        slot_aspects = {k: [f.width() / f.height() for f in split_frame(area, k)] for k in LAYOUT_NAMES}
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            groups, skipped, infos = plan_months(paths, len(month_keys), slot_aspects)
        finally:
            QApplication.restoreOverrideCursor()

        for key in month_keys:
            self.photos.pop(key, None)
            self.crops.pop(key, None)
            self.layouts.pop(key, None)
        for key, group in zip(month_keys, groups):
            self.photos[key] = padded(group)
            self.layouts[key] = len(group)
        self.current = 1 if self.settings.cover else 0
        self.refresh()

        first, last = infos[0][0], infos[-1][0]
        message = (f"{len(paths) - len(skipped)} photo(s) réparties sur {len(groups)} mois, "
                   f"de la plus ancienne ({first:%d/%m/%Y}) à la plus récente ({last:%d/%m/%Y}).")
        details = []
        counts = [len(group) for group in groups]
        layouts = ", ".join(f"{counts.count(k)} page(s) en disposition {k}" for k in LAYOUT_NAMES if counts.count(k))
        details.append(f"Dispositions choisies pour utiliser le plus de photos possible : {layouts}. "
                       "Chaque page reste modifiable depuis sa vignette.")
        alone = sum(1 for group in groups if len(group) == 2 and group[1] is None)
        if alone:
            details.append(f"{alone} portrait(s) seul(s) sur leur page : placé(s) à gauche de la disposition 2, "
                           "le cadre de droite reste libre pour une autre photo.")
        if skipped:
            details.append(f"{len(skipped)} photo(s) non utilisée(s) : il y a plus de photos que de places "
                           f"({len(month_keys)} mois, {MAX_SLOTS} photos au plus par page). "
                           "Les photos retenues couvrent toute la période.")
        if len(groups) < len(month_keys):
            details.append(f"{len(month_keys) - len(groups)} mois restent sans photo.")
        from_file = sum(1 for _d, source, *_ in infos if source == "fichier")
        if from_file:
            details.append(f"{from_file} photo(s) sans date de prise de vue : "
                           "c'est la date de modification du fichier qui a servi au classement.")
        self.statusBar().showMessage(message, 10000)
        QMessageBox.information(self, "Remplissage automatique", "\n\n".join([message] + details))

    def choose_color(self):
        color = QColorDialog.getColor(self.settings.accent, self, "Couleur du calendrier")
        if color.isValid():
            self.settings.accent = color
            self.refresh()

    # --- Projet ----------------------------------------------------------

    # Un projet (.calendrier.json) contient les réglages, les photos choisies (chemins), les dispositions
    # et les recadrages : tout ce qu'il faut pour reprendre le calendrier plus tard.

    def _project_data(self):
        return {
            "settings": self.settings.to_dict(),
            "photos": {str(k): v for k, v in self.photos.items()},
            "layouts": {str(k): v for k, v in self.layouts.items()},
            "crops": {str(k): v for k, v in self.crops.items()},
        }

    def _state(self):
        return json.dumps(self._project_data(), sort_keys=True)

    def is_modified(self):
        return self._state() != self.saved_state

    def _mark_saved(self):
        self.saved_state = self._state()
        self._update_title()

    def _update_title(self):
        name = os.path.basename(self.project_path) if self.project_path else "Nouveau calendrier"
        self.setWindowTitle(f"{APP_NAME} — {name}{' *' if self.is_modified() else ''}")

    def maybe_save(self):
        """Propose d'enregistrer les changements. Renvoie False si l'utilisateur annule."""
        if not self.is_modified():
            return True
        box = QMessageBox(
            QMessageBox.Icon.Question, "Projet non enregistré",
            "Le calendrier a été modifié depuis la dernière sauvegarde.\n"
            "Voulez-vous sauvegarder le projet pour pouvoir le reprendre plus tard ?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            self,
        )
        # Libellés explicites (la traduction de Qt dit « Ne pas tenir compte » pour Discard).
        for button, text in ((QMessageBox.StandardButton.Save, "Sauvegarder"),
                             (QMessageBox.StandardButton.Discard, "Ne pas sauvegarder"),
                             (QMessageBox.StandardButton.Cancel, "Annuler")):
            box.button(button).setText(text)
        set_primary(box.button(QMessageBox.StandardButton.Save))
        box.setDefaultButton(QMessageBox.StandardButton.Save)
        box.exec()
        answer = box.standardButton(box.clickedButton())
        if answer == QMessageBox.StandardButton.Save:
            return self.save_project()
        if answer == QMessageBox.StandardButton.Discard:
            self._remove_autosave()  # changements abandonnés : rien à récupérer au prochain lancement
            return True
        return False

    def closeEvent(self, event):
        if self.maybe_save():
            self._remove_autosave()
            event.accept()
        else:
            event.ignore()

    def new_project(self):
        if not self.maybe_save():
            return
        self.settings = Settings()
        self.photos = {}
        self.layouts = {}
        self.crops = {}
        self.project_path = None
        self.current = 0
        self._reset_history()
        self._sync_widgets()
        self.refresh()
        self._mark_saved()

    @staticmethod
    def _parse_project(data, base=None):
        """Réglages, photos, dispositions et recadrages d'un projet lu (fichier ou historique d'annulation).

        base : dossier du projet, pour retrouver une photo déplacée avec lui (chemin relatif au projet).
        """
        settings = Settings()
        settings.load_dict(data.get("settings", {}))

        def page_key(key):
            return "cover" if key == "cover" else int(key)

        relative = data.get("photos_relative", {})
        photos = {}
        for key, value in data.get("photos", {}).items():
            # Anciens projets : une seule photo par page (un chemin au lieu d'une liste).
            paths = padded([value] if isinstance(value, str) else value)
            if base is not None:
                for slot, rel in enumerate(padded(relative.get(key))):
                    if paths[slot] and not os.path.exists(paths[slot]) and rel:
                        candidate = os.path.normpath(os.path.join(base, rel))
                        if os.path.exists(candidate):
                            paths[slot] = candidate
            photos[page_key(key)] = paths
        layouts = {page_key(key): min(MAX_SLOTS, max(1, int(value))) for key, value in data.get("layouts", {}).items()}
        crops = {page_key(key): padded(value) for key, value in data.get("crops", {}).items()}
        return settings, photos, layouts, crops

    def open_project(self, path=None):
        if not self.maybe_save():
            return
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Importer un projet de calendrier", self.last_dir,
                                                  "Projet de calendrier (*.calendrier.json *.json)")
        if not path:
            return
        base = os.path.dirname(path)
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            settings, photos, layouts, crops = self._parse_project(data, base)
        except Exception as exc:
            QMessageBox.critical(self, "Erreur", f"Impossible d'importer le projet :\n{exc}")
            return
        self.settings, self.photos, self.layouts, self.crops = settings, photos, layouts, crops
        self.project_path = path
        self.last_dir = base
        self.current = 0
        self._reset_history()
        self._sync_widgets()
        self.refresh()
        self._mark_saved()
        self._add_recent(path)
        self.statusBar().showMessage(f"Projet importé : {os.path.basename(path)}", 5000)
        missing = [p for paths in self.photos.values() for p in paths if p and not os.path.exists(p)]
        if missing:
            QMessageBox.warning(self, "Photos introuvables",
                                f"{len(missing)} photo(s) du projet sont introuvables (déplacées ou supprimées).\n\n"
                                + "\n".join(f"• {p}" for p in missing[:10]))

    def save_project(self):
        if self.project_path is None:
            return self.save_project_as()
        data = self._project_data()
        base = os.path.dirname(self.project_path)

        def relative(path):
            try:
                return os.path.relpath(path, base) if path else None
            except ValueError:  # photo sur un autre lecteur
                return None

        data["photos_relative"] = {key: [relative(p) for p in paths] for key, paths in data["photos"].items()}
        try:
            with open(self.project_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            QMessageBox.critical(self, "Erreur", f"Impossible de sauvegarder le projet :\n{exc}")
            return False
        self.last_dir = base
        self._mark_saved()
        self._add_recent(self.project_path)
        self._remove_autosave()
        self.statusBar().showMessage(f"Projet sauvegardé : {self.project_path}", 5000)
        return True

    def save_project_as(self):
        default = self.project_path or os.path.join(self.last_dir, f"Calendrier {self.settings.year}.calendrier.json")
        path, _ = QFileDialog.getSaveFileName(self, "Sauvegarder le projet", default,
                                              "Projet de calendrier (*.calendrier.json)")
        if not path:
            return False
        self.project_path = path
        return self.save_project()

    # --- Projets récents ---------------------------------------------------

    def _recent(self):
        value = self.preferences.value("recent", [])
        if isinstance(value, str):  # QSettings rend une chaîne seule pour une liste d'un élément
            value = [value]
        return [p for p in (value or []) if isinstance(p, str)]

    def _set_recent(self, paths):
        self.preferences.setValue("recent", paths[:MAX_RECENT])

    def _add_recent(self, path):
        path = os.path.normpath(path)
        self._set_recent([path] + [p for p in self._recent() if os.path.normcase(p) != os.path.normcase(path)])

    def _fill_recent_menu(self):
        self.recent_menu.clear()
        recent = self._recent()
        if not recent:
            empty = self.recent_menu.addAction("Aucun projet récent")
            empty.setEnabled(False)
            return
        for i, path in enumerate(recent):
            action = self.recent_menu.addAction(f"&{i + 1}  {os.path.basename(path)}")
            action.setToolTip(path)
            action.setStatusTip(path)
            action.triggered.connect(lambda _=False, p=path: self._open_recent(p))
        self.recent_menu.addSeparator()
        self.recent_menu.addAction("Effacer la liste", lambda: self._set_recent([]))

    def _open_recent(self, path):
        if not os.path.exists(path):
            QMessageBox.warning(self, "Projet introuvable",
                                f"Ce projet n'existe plus (déplacé ou supprimé) :\n{path}\n\n"
                                "Il est retiré de la liste des projets récents.")
            self._set_recent([p for p in self._recent() if p != path])
            return
        self.open_project(path)

    # --- Sauvegarde automatique ----------------------------------------------

    @staticmethod
    def _autosave_path():
        folder = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        return os.path.join(folder, "sauvegarde automatique.calendrier.json")

    def autosave(self):
        """Copie de secours du projet non sauvegardé (le fichier du projet lui-même n'est pas touché)."""
        if not self.is_modified():
            return
        path = self._autosave_path()
        data = {"project": self._project_data(), "project_path": self.project_path,
                "saved_at": datetime.datetime.now().isoformat(timespec="seconds")}
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path + ".tmp", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            os.replace(path + ".tmp", path)
        except OSError:
            return  # disque plein ou dossier protégé : on réessaiera à la prochaine échéance
        self.statusBar().showMessage(f"Sauvegarde automatique ({datetime.datetime.now():%H:%M}).", 3000)

    def _remove_autosave(self):
        try:
            os.remove(self._autosave_path())
        except OSError:
            pass

    def check_recovery(self):
        """Au lancement : propose de récupérer un calendrier qui n'avait pas été sauvegardé."""
        path = self._autosave_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            settings, photos, layouts, crops = self._parse_project(data["project"])
            saved_at = datetime.datetime.fromisoformat(data["saved_at"])
        except Exception:
            self._remove_autosave()  # copie illisible : inutile de la proposer
            return
        project_path = data.get("project_path")
        name = os.path.basename(project_path) if project_path else "Nouveau calendrier"
        box = QMessageBox(QMessageBox.Icon.Question, "Calendrier non sauvegardé",
                          f"Le logiciel s'est fermé avant que le calendrier « {name} » soit sauvegardé.\n\n"
                          f"Une copie de secours du {saved_at:%d/%m/%Y à %H:%M} a été retrouvée. "
                          "Voulez-vous la récupérer ?", parent=self)
        recover = box.addButton("Récupérer", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Ignorer", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(recover)
        box.exec()
        if box.clickedButton() is not recover:
            self._remove_autosave()
            return
        self.settings, self.photos, self.layouts, self.crops = settings, photos, layouts, crops
        self.project_path = project_path
        self.current = 0
        self._reset_history()
        self._sync_widgets()
        self.saved_state = None  # récupéré mais pas encore sauvegardé : le projet est « modifié »
        self.refresh()
        self.statusBar().showMessage("Calendrier récupéré : pensez à le sauvegarder (Ctrl+S).", 10000)

    # --- Export ----------------------------------------------------------

    def _confirm_missing(self, action):
        """Signale les pages sans aucune photo ; renvoie False si l'utilisateur renonce.

        Un cadre vide sur une page qui a d'autres photos n'est pas signalé : il n'est simplement
        pas imprimé (portrait seul à gauche de la disposition 2, par exemple).
        """
        pages = range(len(self.settings.pages()))
        empty = [i for i in pages if not any(self.renderer().page_photos(self._page_key(i)))]
        if not empty:
            return True
        answer = QMessageBox.question(
            self, "Pages sans photo",
            "Ces pages n'ont aucune photo :\n• " + "\n• ".join(self._page_title(i) for i in empty)
            + f"\n\nLes cadres vides ne sont pas imprimés : ces pages n'auront que leur calendrier.\n\n{action} quand même ?",
        )
        return answer == QMessageBox.StandardButton.Yes

    def print_calendar(self):
        if not self._confirm_missing("Imprimer"):
            return
        _label, page_id, landscape = FORMATS[self.settings.format_index]
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setDocName(self.settings.title)
        printer.setPageSize(QPageSize(page_id))
        printer.setPageOrientation(QPageLayout.Orientation.Landscape if landscape else QPageLayout.Orientation.Portrait)
        count = len(self.settings.pages())
        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle("Imprimer le calendrier")
        dialog.setMinMax(1, count)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if printer.printRange() == QPrinter.PrintRange.PageRange:
            indices = range(printer.fromPage() - 1, min(printer.toPage(), count))
        else:
            indices = range(count)
        if print_pages(self.settings, self.photos, self.layouts, self.crops, self.cache, printer, indices, self):
            self.statusBar().showMessage(f"{len(indices)} page(s) envoyée(s) à l'imprimante.", 6000)

    def export_pdf(self):
        if not self._confirm_missing("Exporter"):
            return

        default = os.path.join(self.last_dir, f"Calendrier {self.settings.year}.pdf")
        path, _ = QFileDialog.getSaveFileName(self, "Exporter en PDF", default, "Fichiers PDF (*.pdf)")
        if not path:
            return
        if not export_pdf(self.settings, self.photos, self.layouts, self.crops, self.cache, path, self):
            return
        self.statusBar().showMessage(f"PDF créé : {path}", 8000)
        answer = QMessageBox.question(self, "Export terminé", f"Le calendrier a été créé :\n{path}\n\nL'ouvrir maintenant ?")
        if answer == QMessageBox.StandardButton.Yes:
            os.startfile(path)


def export_pdf(settings, photos, layouts, crops, cache, path, parent=None):
    """Écrit le calendrier dans un PDF (300 dpi). Renvoie False si annulé ou en échec."""
    label, page_id, landscape = FORMATS[settings.format_index]
    writer = QPdfWriter(path)
    writer.setCreator(APP_NAME)
    writer.setTitle(settings.title)
    writer.setResolution(EXPORT_DPI)
    writer.setPageSize(QPageSize(page_id))
    writer.setPageOrientation(QPageLayout.Orientation.Landscape if landscape else QPageLayout.Orientation.Portrait)
    writer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)

    renderer = CalendarRenderer(settings, photos, layouts, crops, cache)
    renderer.hide_empty = True
    count = len(settings.pages())
    progress = None
    if parent is not None:
        progress = QProgressDialog("Création du PDF…", "Annuler", 0, count, parent)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)

    painter = QPainter(writer)
    cancelled = False
    try:
        for i in range(count):
            if i:
                writer.newPage()
            renderer.render(painter, i, writer.width(), writer.height())
            if progress is not None:
                progress.setValue(i + 1)
                QApplication.processEvents()
                if progress.wasCanceled():
                    cancelled = True
                    break
    finally:
        painter.end()
        # Les photos à pleine résolution ne servent qu'à l'export : on libère la mémoire.
        for key in [k for k in cache.images if k[1] > 1024]:
            del cache.images[key]
    if cancelled:
        os.remove(path)
        return False
    return True


def print_pages(settings, photos, layouts, crops, cache, printer, indices, parent=None):
    """Imprime des pages du calendrier. Renvoie False si annulé ou en échec.

    Chaque page est dessinée à 300 dpi (comme le PDF), puis réduite si besoin pour tenir dans la zone
    imprimable de la feuille (les imprimantes ne savent pas imprimer jusqu'au bord), et centrée.
    """
    renderer = CalendarRenderer(settings, photos, layouts, crops, cache)
    renderer.hide_empty = True
    size = QPageSize(FORMATS[settings.format_index][1]).size(QPageSize.Unit.Millimeter)
    w_mm, h_mm = (size.height(), size.width()) if settings.landscape else (size.width(), size.height())
    w, h = w_mm / 25.4 * EXPORT_DPI, h_mm / 25.4 * EXPORT_DPI  # page du calendrier, en points à 300 dpi
    area = printer.pageRect(QPrinter.Unit.DevicePixel)
    scale = min(area.width() / w, area.height() / h)
    offset = QPointF((area.width() - w * scale) / 2, (area.height() - h * scale) / 2)

    painter = QPainter()
    if not painter.begin(printer):
        if parent is not None:
            QMessageBox.critical(parent, "Erreur", "Impossible de démarrer l'impression.")
        return False
    progress = None
    if parent is not None:
        progress = QProgressDialog("Impression…", "Annuler", 0, len(indices), parent)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
    cancelled = False
    try:
        for n, index in enumerate(indices):
            if n:
                printer.newPage()
            painter.save()
            painter.translate(offset)
            painter.scale(scale, scale)
            renderer.render(painter, index, w, h)
            painter.restore()
            if progress is not None:
                progress.setValue(n + 1)
                QApplication.processEvents()
                if progress.wasCanceled():
                    cancelled = True
                    printer.abort()
                    break
    finally:
        painter.end()
        for key in [k for k in cache.images if k[1] > 1024]:
            del cache.images[key]
    return not cancelled


def install_french_translation(app):
    """Textes standard de Qt en français : boutons Oui / Non / Enregistrer…, choix de la couleur,
    menu contextuel des champs de saisie. Sans le fichier de traduction, Qt reste en anglais."""
    import PySide6
    translator = QTranslator(app)
    folders = (os.path.join(os.path.dirname(PySide6.__file__), "translations"),
               QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath))
    if any(translator.load("qtbase_fr", folder) for folder in folders):
        app.installTranslator(translator)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setStyleSheet(app_style())
    app.setWindowIcon(app_icon())
    install_french_translation(app)
    QLocale.setDefault(QLocale(QLocale.Language.French, QLocale.Country.France))  # calendrier de saisie des dates
    window = CalendarWindow()
    window.showMaximized()  # occupe tout l'écran, barre de titre et barre des tâches conservées
    QTimer.singleShot(0, window.check_recovery)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
