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

import qtawesome as qta  # type: ignore[import]
from aqt.qt import QCursor, QPushButton, QSize, Qt, QWidget

from ..icons import get_amboss_qicon
from ..styles import style_button_primary


class StartSessionButton(QPushButton):
    _stylesheet = (
        style_button_primary
        + """
QPushButton {
    height: 32px;
}
"""
    )

    def __init__(
        self, label: str, night_mode: bool = False, parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.setStyleSheet(self._stylesheet)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setProperty("night_mode", str(night_mode))
        self._label = label
        self._icon_enabled = get_amboss_qicon("logo_mono.svg")
        self._icon_disabled = get_amboss_qicon("logo_mono_disabled.svg")
        self.set_enabled(True)

    def set_enabled(self, enabled: bool) -> None:
        self.setText(self._label)
        self.setIconSize(QSize(16, 16))
        if enabled:
            self.setEnabled(True)
            self.setIcon(self._icon_enabled)
        else:
            self.setEnabled(False)
            self.setIcon(self._icon_disabled)

    def set_loading(self) -> None:
        self.setText("")
        self.setEnabled(False)
        self.setIcon(
            qta.icon(
                "ph.spinner",
                color="white",
                animation=qta.Spin(self, interval=17, step=6),
            ),
        )
        self.setIconSize(QSize(24, 24))

    def setText(self, text: str) -> None:
        # hack: create padding to icon via nbsp
        return super().setText("\u2002" + text)
