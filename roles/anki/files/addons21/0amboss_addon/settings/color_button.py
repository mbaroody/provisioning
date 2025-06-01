# AMBOSS Anki Add-on
#
# Copyright (C) 2019-2023 AMBOSS MD Inc. <https://www.amboss.com/us>
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


from typing import Optional

from aqt.qt import (
    QColor,
    QColorDialog,
    QIcon,
    QPixmap,
    QPushButton,
    QSize,
    QWidget,
    pyqtSlot,
)


class QColorButton(QPushButton):
    def __init__(self, parent: Optional[QWidget] = None, color: str = "#000000"):
        super().__init__(parent=parent)
        self._set_button_color(color)
        self.clicked.connect(self._choose_color)

    def color(self) -> str:
        """Get current color

        :return: HTML color code
        """
        return self._color

    def set_color(self, color: str):
        """Set current color

        :param color: HTML color code
        """
        self._set_button_color(color)

    @pyqtSlot()
    def _choose_color(self) -> None:
        dialog = QColorDialog(parent=self)
        color = dialog.getColor(QColor(self._color))
        if not color.isValid():
            return
        self._set_button_color(color.name())

    def _set_button_color(self, color: str):
        """Set preview color"""
        pixmap = QPixmap(128, 18)
        qcolor = QColor(0, 0, 0)
        qcolor.setNamedColor(color)
        pixmap.fill(qcolor)
        self.setIcon(QIcon(pixmap))
        self.setIconSize(QSize(128, 18))
        self._color = color
