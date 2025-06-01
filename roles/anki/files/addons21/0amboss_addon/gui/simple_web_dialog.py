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


from typing import Callable, Optional, Type

from aqt.qt import QDialog, QUrl, QVBoxLayout, QWidget

from ..shared import _
from ..web import LocalWebPage, WebViewFactory


class SimpleWebDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        object_name: str,
        web_view_factory: WebViewFactory,
        web_page_factory: Type[LocalWebPage],
        title: str = _("AMBOSS"),
    ):
        super().__init__(parent=parent)
        self.setObjectName(object_name)
        self.setWindowTitle(title)

        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0, 0, 0, 0)

        self.web_page = web_page_factory()
        self.web_view = web_view_factory.create_webview(
            parent=self, object_name=f"{object_name}_webview"
        )
        self.web_view.setPage(self.web_page)

        dialog_layout.addWidget(self.web_view)

    def set_html(self, html: str):
        self.web_view.setHtml(html)

    def load_url(self, url: QUrl):
        self.web_view.load(url=url)

    def show_blocking(self) -> int:
        """Show as a blocking dialog, returning user choice

        Returns:
            answer: 1 for accepted, 0 for rejected
        """
        return self.exec()

    def show_non_blocking(self, callback: Optional[Callable[[int], None]] = None):
        """Show as a non-blocking dialog, optionally passing return code to callback

        Passed to callback:
            1 for accepted, 0 for rejected
        """
        if callback:
            self.finished.connect(callback)  # type: ignore[arg-type]
        self.show()
