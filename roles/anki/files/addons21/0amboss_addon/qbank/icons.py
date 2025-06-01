# AMBOSS Anki Add-on
#
# Copyright (C) 2019-2022 AMBOSS MD Inc. <https://www.amboss.com/us>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version, with the additions
# listed at the end of the license file that accompanied this program.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from pathlib import Path
from typing import List

from aqt.qt import QIcon, QPainter, QPixmap, Qt


def get_amboss_pixmap(filename: str) -> QPixmap:
    logo_path = Path(__file__).parent / "assets" / filename
    return QPixmap(str(logo_path))


def get_amboss_qicon(filename: str) -> QIcon:
    pixmap = get_amboss_pixmap(filename)
    return QIcon(pixmap)


def get_composite_pixmap(pixmaps: List[QPixmap], spacing: int) -> QPixmap:
    """Concatenate multiple pixmaps to a composite image"""
    width = spacing * len(pixmaps) - 1 + sum(p.width() for p in pixmaps)
    height = max(p.height() for p in pixmaps)
    container = QPixmap(width, height)
    container.fill(Qt.GlobalColor.transparent)
    painter = QPainter(container)
    x = 0
    for pixmap in pixmaps:
        pixmap_width = pixmap.width()
        painter.drawPixmap(x, 0, pixmap_width, pixmap.height(), pixmap)
        x += pixmap_width + spacing
    return container
