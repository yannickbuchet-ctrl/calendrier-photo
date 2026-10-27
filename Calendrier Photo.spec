# Construction de l'exécutable :
#   python -m PyInstaller --clean "Calendrier Photo.spec"
# Résultat : dist\Calendrier Photo.exe (un seul fichier, sans console).
#
# Taille réduite :
# - modules Qt superflus retirés (QML, Quick, réseau, OpenGL, PDF de Qt), rendu OpenGL
#   logiciel, SSL, styles et traductions de Qt (sauf qtbase_fr.qm, pour les boutons et fenêtres
#   standard en français). Les plugins d'images JPEG, GIF, WebP et TIFF sont conservés (lecture des photos) ;
# - modules Python inutilisés retirés (json, lui, sert aux projets et reste inclus) ;
# - bytecode sans docstrings ni assertions (optimize=2).
#
# Pas de compression UPX : sur d'autres PC, les antivirus (Windows Defender, Contrôle intelligent des
# applications de Windows 11) bloquent les DLL compressées une fois extraites, et l'application
# s'arrête au lancement (« No module named 'PySide6.QtCore' »).

# -*- mode: python ; coding: utf-8 -*-

EXCLUDED_MODULES = [
    "tkinter", "unittest", "pydoc", "doctest", "xmlrpc", "sqlite3", "lib2to3",
    "ssl", "_ssl", "_hashlib", "hashlib",
    "numpy", "PIL", "pymupdf", "fitz",
    "email", "http", "urllib", "xml", "html.parser", "multiprocessing", "asyncio", "concurrent",
    "socket", "_socket", "select", "selectors", "gzip", "bz2", "_bz2", "lzma", "_lzma", "_zstd",
    "compression", "tarfile", "csv",  # zipfile, lui, est requis par le chargeur de PyInstaller
    "pickle", "subprocess", "difflib", "unicodedata",
    "decimal", "_decimal", "ctypes", "_ctypes",
    "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtOpenGL",
    "PySide6.QtPdf", "PySide6.QtSvg", "PySide6.QtDBus",
]

# Fichiers binaires ou de données à écarter (comparaison sur le chemin, en minuscules).
EXCLUDED_FILES = [
    "opengl32sw.dll", "d3dcompiler", "qt6quick", "qt6qml", "qt6pdf", "qt6network",
    "qt6opengl", "qt6svg", "qt6virtualkeyboard", "libcrypto", "libssl",
    "plugins\\iconengines", "plugins\\tls", "plugins\\networkinformation", "plugins\\generic",
    "plugins\\styles", "plugins\\platforminputcontexts", "qdirect2d", "qminimal", "qoffscreen",
    "translations",
    # Formats d'image inutiles pour des photos (les plugins jpeg, gif, webp, tiff et ico restent).
    "qsvg", "qpdf", "qicns", "qtga", "qwbmp",
]


def keep(entry):
    name = entry[0].lower().replace("/", "\\")
    if name.endswith("qtbase_fr.qm"):  # seule traduction gardée : boutons et fenêtres standard en français
        return True
    return not any(pattern in name for pattern in EXCLUDED_FILES)


a = Analysis(
    ["calendrier.py"],
    # Chargé en interne par PySide6 (shibokensupport) sans que PyInstaller le détecte.
    hiddenimports=["logging"],
    excludes=EXCLUDED_MODULES,
    noarchive=False,
    optimize=2,
)
a.binaries = [b for b in a.binaries if keep(b)]
a.datas = [d for d in a.datas if keep(d)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Calendrier Photo",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon="Calendrier Photo.ico",  # produite par : python make_icon.py
)
