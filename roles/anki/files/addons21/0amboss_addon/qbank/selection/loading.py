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

import json
from typing import Optional

from aqt.qt import QUrl, QVBoxLayout, QWidget, pyqtSlot

from ...theme import ThemeManager
from ...url import url_with_query
from ...web import LocalWebPage, WebView


class LoadingWidget(QWidget):
    def __init__(
        self,
        height: int,
        url: str,
        theme_manager: ThemeManager,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._height = height
        if theme_manager.night_mode:
            url = url_with_query(url, {"night-mode": "true"})
        self._url = url

        page = LocalWebPage()
        self.webview: WebView = WebView(theme_manager=theme_manager, parent=self)
        self.webview.setPage(page)
        self.destroyed.connect(self._cleanup)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.webview)
        self.setLayout(layout)

    def set_text(self, text: str):
        self.webview.eval(f"window.setLoadingText({json.dumps(text)})")

    def show(self) -> None:
        if self.isVisible():
            return
        self.setFixedHeight(self._height)
        self.webview.load(QUrl(self._url))
        return super().show()

    def hide(self):
        super().hide()
        if self.isHidden():
            return
        self.setFixedHeight(0)
        self.webview.load(QUrl("about:blank"))

    @pyqtSlot()
    def _cleanup(self):
        # Webviews in Anki are not always garbage collected properly, so we need to
        # manually clean them up.
        try:
            self.webview.cleanup()  # type: ignore[attr-defined]
        except AttributeError:
            pass
        self.webview = None  # type: ignore[assignment]
