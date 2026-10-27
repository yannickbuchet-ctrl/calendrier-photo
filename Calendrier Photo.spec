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


# Informations de version de l'exécutable (Propriétés → Détails) : nom, version, éditeur, copyright.
# Un exécutable qui en est dépourvu est plus souvent signalé par les antivirus. Nom et version sont lus dans
# le programme (APP_NAME, APP_VERSION) : il n'y a qu'un endroit à mettre à jour.
import os
import re

with open("calendrier.py", encoding="utf-8") as source:
    CONSTANTS = dict(re.findall(r'^(APP_\w+) = "([^"]*)"', source.read(), re.M))
NAME, VERSION = CONSTANTS["APP_NAME"], CONSTANTS["APP_VERSION"]
NUMBERS = tuple((list(map(int, re.findall(r"\d+", VERSION))) + [0, 0, 0, 0])[:4])
VERSION_FILE = os.path.join("build", "version_info.txt")
os.makedirs("build", exist_ok=True)
with open(VERSION_FILE, "w", encoding="utf-8") as fichier:
    fichier.write(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={NUMBERS}, prodvers={NUMBERS}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040C04B0', [
      StringStruct('CompanyName', 'Yannick Buchet'),
      StringStruct('FileDescription', '{NAME} — calendrier personnalisé avec vos photos'),
      StringStruct('FileVersion', '{VERSION}'),
      StringStruct('InternalName', '{NAME}'),
      StringStruct('LegalCopyright', '© 2026 Yannick Buchet — licence MIT'),
      StringStruct('OriginalFilename', '{NAME}.exe'),
      StringStruct('ProductName', '{NAME}'),
      StringStruct('ProductVersion', '{VERSION}')])]),
    VarFileInfo([VarStruct('Translation', [0x040C, 1200])])
  ]
)
""")


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

OPTIONS = dict(name="Calendrier Photo", debug=False, strip=False, upx=False, console=False,
               icon="Calendrier Photo.ico",  # produite par : python make_icon.py
               version=VERSION_FILE)

if os.environ.get("CONSTRUCTION") == "dossier":
    # Version en dossier, pour l'installateur (installer\Calendrier Photo.iss) : dist\Calendrier Photo\.
    # Rien n'est extrait au lancement, ce qui évite aussi les alertes des antivirus.
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, **OPTIONS)
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="Calendrier Photo")
else:
    # Un seul fichier, portable : dist\Calendrier Photo.exe.
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], **OPTIONS)
