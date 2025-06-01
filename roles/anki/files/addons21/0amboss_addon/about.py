# AMBOSS Anki Add-on
#
# Copyright (C) 2019-2020 AMBOSS MD Inc. <https://www.amboss.com/us>
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


from typing import TYPE_CHECKING

from aqt.qt import QDialog, QUrl, QVBoxLayout

from .shared import _
from .web import WebView

if TYPE_CHECKING:
    from aqt.main import AnkiQt


class AboutDialog(QDialog):
    def __init__(
        self,
        main_window: "AnkiQt",
        web_server,
        about_url: str,
        web_view: WebView,
    ):
        super().__init__(parent=main_window)
        self.setObjectName("amboss_about_dialog")
        self._web_server = web_server
        self._about_url = about_url
        self._layout = QVBoxLayout(self)
        self._web_view = web_view
        self._setup()

    def show(self) -> None:
        self._web_view.load(QUrl(self._about_url))
        self.exec()

    def _setup(self) -> None:
        self._layout.addWidget(self._web_view)  # signature broken
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.resize(480, 360)
        self.setWindowTitle(_("AMBOSS - About"))
