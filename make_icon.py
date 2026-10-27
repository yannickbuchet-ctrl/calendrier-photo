# Génère « Calendrier Photo.ico » (icône de l'exécutable) à partir du dessin de calendrier.py :
#   python make_icon.py
# À relancer seulement si le dessin de l'icône change.

import struct
import sys

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtWidgets import QApplication

from calendrier import APP_ICON_SIZES, APP_NAME, draw_app_icon


def png_bytes(image):
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(data)


def main():
    app = QApplication(sys.argv)
    images = [png_bytes(draw_app_icon(size)) for size in APP_ICON_SIZES]

    # Fichier ICO : en-tête, une entrée par taille, puis les images au format PNG.
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = len(header) + 16 * len(images)
    entries, payload = b"", b""
    for size, png in zip(APP_ICON_SIZES, images):
        entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(png), offset + len(payload))
        payload += png
    path = f"{APP_NAME}.ico"
    with open(path, "wb") as f:
        f.write(header + entries + payload)
    print(f"{path} créé.")


if __name__ == "__main__":
    main()
