# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *


class MonoSpaceLineEdit(QLineEdit):
    font_size = 14
    min_height = 32

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        font = self.font()
        font.setFamilies((
            "Noto Mono",
            "Noto Sans Mono",
            "DejaVu Sans Mono",
            "Droid Sans Mono",
            "Liberation Mono",
            "Courier New",
            "Courier",
            "Lucida",
            "Monaco",
            "Monospace",
        ))
        font.setPixelSize(self.font_size)
        self.setMinimumHeight(self.min_height)
        self.setFont(font)
