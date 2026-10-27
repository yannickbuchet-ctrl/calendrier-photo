# Génère le dossier « exemples » : des photos modèles (paysages dessinés, aucune photo réelle) pour essayer
# l'application sans ses propres photos :
#   python make_exemples.py
# Trois photos par mois, en portrait et en paysage, aux couleurs de la saison. La date est dans le nom du
# fichier (2027-03-10-printemps-paysage.jpg…) : « Remplir automatiquement » les range donc mois par mois.

import math
import os
import random
import sys

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPainterPath
from PySide6.QtWidgets import QApplication

FOLDER = "exemples"
YEAR = 2027
LONG_SIDE, SHORT_SIDE = 1800, 1200

# Couleurs par saison : ciel (haut, bas), soleil, collines (du fond vers le devant), arbres.
SEASONS = {
    "hiver": (("#bfdbfe", "#eff6ff"), "#fef9c3", ("#e2e8f0", "#f1f5f9", "#ffffff"), "#94a3b8"),
    "printemps": (("#3b9be8", "#bde3fb"), "#fcd34d", ("#9fd89a", "#6cc06a", "#4caf50"), "#3f7d3a"),
    "ete": (("#3b9be8", "#cfeafc"), "#fcd34d", ("#a3c94f", "#d6c36a", "#8bbf45"), "#5b7a2a"),
    "canicule": (("#f4a261", "#fde2c4"), "#fde68a", ("#f0b27a", "#df8a4c", "#b85b32"), "#7c3a1d"),
    "automne": (("#93c5fd", "#fef3c7"), "#fbbf24", ("#e9b35f", "#d97706", "#9a4a12"), "#6b2f0e"),
}
MONTH_SEASONS = ["hiver", "hiver", "printemps", "printemps", "ete", "ete",
                 "canicule", "canicule", "automne", "automne", "automne", "hiver"]
# Orientation des trois photos de chaque mois (de quoi remplir toutes les dispositions).
ORIENTATIONS = [("paysage", "portrait", "paysage"), ("portrait", "paysage", "paysage")]


def hill(rng, width, height, base, amplitude):
    """Fonction y(x) d'une ligne de collines : somme de deux ondulations au hasard."""
    waves = [(rng.uniform(0.6, 1.6), rng.uniform(0, 2 * math.pi), rng.uniform(0.5, 1)) for _ in range(2)]

    def y(x):
        t = x / width * 2 * math.pi
        return height * (base - amplitude * sum(a * math.sin(f * t + phase) for f, phase, a in waves) / 2)
    return y


def draw_landscape(width, height, season, seed):
    rng = random.Random(seed)
    (sky_top, sky_bottom), sun, hills, tree = SEASONS[season]
    image = QImage(width, height, QImage.Format.Format_RGB32)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)

    sky = QLinearGradient(0, 0, 0, height)
    sky.setColorAt(0, QColor(sky_top))
    sky.setColorAt(1, QColor(sky_bottom))
    p.setBrush(sky)
    p.drawRect(QRectF(0, 0, width, height))

    radius = min(width, height) * rng.uniform(0.06, 0.09)
    p.setBrush(QColor(sun))
    p.drawEllipse(QPointF(width * rng.uniform(0.15, 0.85), height * rng.uniform(0.12, 0.3)), radius, radius)

    # Trois lignes de collines, de plus en plus basses ; des arbres sur les deux premières.
    for layer, color in enumerate(hills):
        y = hill(rng, width, height, 0.5 + 0.12 * layer, 0.12 - 0.02 * layer)
        path = QPainterPath()
        path.moveTo(0, height)
        for x in range(0, width + 10, 10):
            path.lineTo(x, y(x))
        path.lineTo(width, height)
        path.closeSubpath()
        p.setBrush(QColor(color))
        p.drawPath(path)
        if layer < 2:
            size = min(width, height) * (0.018 + 0.012 * layer)
            p.setBrush(QColor(tree))
            for _ in range(rng.randint(3, 6)):
                x = rng.uniform(0.03, 0.97) * width
                ground = y(x) + size * rng.uniform(0.5, 2)
                p.drawRect(QRectF(x - size * 0.12, ground - size, size * 0.24, size))
                p.drawEllipse(QPointF(x, ground - size * 1.6), size * 0.75, size)
    p.end()
    return image


def main():
    app = QApplication(sys.argv)
    os.makedirs(FOLDER, exist_ok=True)
    count = 0
    for month in range(1, 13):
        season = MONTH_SEASONS[month - 1]
        for index, orientation in enumerate(ORIENTATIONS[month % 2]):
            size = (LONG_SIDE, SHORT_SIDE) if orientation == "paysage" else (SHORT_SIDE, LONG_SIDE)
            image = draw_landscape(*size, season, seed=month * 10 + index)
            name = f"{YEAR}-{month:02d}-{5 + 10 * index:02d}-{season}-{orientation}.jpg"
            image.save(os.path.join(FOLDER, name), "JPEG", 90)
            count += 1
    print(f"{count} photos créées dans le dossier {FOLDER}.")


if __name__ == "__main__":
    main()
