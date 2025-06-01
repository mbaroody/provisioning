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


from typing import TYPE_CHECKING, Optional

from aqt.qt import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QObject,
    QProgressDialog,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
    pyqtSlot,
)
from aqt.utils import showInfo, showWarning, tooltip

if TYPE_CHECKING:
    from aqt.main import AnkiQt

from .notification import UpdateData
from .shared import _
from .update import AddonInstaller, UpdateDownloadWorker


class UpdateNotificationDialog(QDialog):
    def __init__(self, update_data: UpdateData, parent: Optional[QWidget] = None):
        super().__init__(parent=parent)
        self.setObjectName("amboss_update_dialog")
        self._update_data = update_data
        self._setup_ui()
        self.setWindowTitle(_("AMBOSS - Update"))
        self.resize(500, 400)

    def _setup_ui(self):
        self._layout = QVBoxLayout(self)
        title_label = QLabel(_("AMBOSS Add-on Updates Are Available"), self)
        title_label_font = title_label.font()
        title_label_font.setBold(True)
        title_label_font.setPointSizeF(title_label_font.pointSizeF() * 1.5)
        title_label.setFont(title_label_font)
        body_label = QLabel(
            _(
                "A new update of the AMBOSS add-on is available. You can see what’s new"
                " listed below. Would you like to install it now?"
            )
        )
        body_label.setWordWrap(True)
        body_label.setContentsMargins(0, 8, 0, 8)

        self._text_browser = QTextBrowser(self)
        self._text_browser.setOpenExternalLinks(True)
        self._text_browser.setHtml(self._update_data.changelog)

        self._button_box = QDialogButtonBox()
        self._button_box.setStandardButtons(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        ok_button = self._button_box.button(QDialogButtonBox.StandardButton.Ok)
        cancel_button = self._button_box.button(QDialogButtonBox.StandardButton.Cancel)
        ok_button.setText(_("Update now"))
        cancel_button.setText(_("Remind me later"))
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

        self._layout.addWidget(title_label)
        self._layout.addWidget(body_label)
        self._layout.addWidget(self._text_browser)
        self._layout.addWidget(self._button_box)

    def confirm(self):
        return self.exec()


class UpdateProgressDialog(QProgressDialog):
    def __init__(self, minimum=0, maximum=100, *args, **kwargs):
        super().__init__(minimum=minimum, maximum=maximum, *args, **kwargs)
        self.setObjectName("amboss_update_progress_dialog")
        self.setLabelText(_("Downloading update..."))
        self.setCancelButtonText(_("Cancel update"))
        self.resize(200, 100)

    @pyqtSlot(int)
    def update_progress(self, incr: int):
        self.setValue(self.value() + incr)

    @pyqtSlot()
    def cancel(self):
        super().cancel()

    @pyqtSlot()
    def finish(self):
        self.setValue(self.maximum())


class UpdateUIHandler(QObject):
    def __init__(
        self, main_window: "AnkiQt", addon_installer: AddonInstaller, support_uri: str
    ):
        super().__init__()

        # injected
        self._main_window = main_window
        self._addon_installer = addon_installer
        self._support_uri = support_uri

        # state
        self._update_download_worker: Optional[UpdateDownloadWorker] = None
        self._update_progress_dialog: Optional[UpdateProgressDialog] = None

    @pyqtSlot(bool, bool, object)
    def start(
        self, update_available: bool, interactive: bool, update_data: UpdateData
    ) -> None:
        # TODO: when interactive, inform user about potential connection errors
        if not update_available:
            if interactive:
                tooltip(_("You’re currently up-to-date!"))
            return

        notification_dialog = UpdateNotificationDialog(
            update_data, parent=self._main_window
        )

        if not notification_dialog.confirm():
            return

        self.start_download(update_data)

    def start_download(self, update_data: UpdateData):
        # Attach to instance to prevent qt garbage collection
        self._update_download_worker = UpdateDownloadWorker(update_data)
        self._update_progress_dialog = UpdateProgressDialog(
            maximum=update_data.bytes or 100, parent=self._main_window
        )

        self._update_progress_dialog.canceled.connect(self.on_cancel)

        self._update_download_worker.chunk_downloaded.connect(
            self._update_progress_dialog.update_progress
        )
        self._update_download_worker.done.connect(self._update_progress_dialog.finish)
        self._update_download_worker.done.connect(self.on_download_done)
        self._update_download_worker.error.connect(self.on_download_error)

        self._update_download_worker.start()
        self._update_progress_dialog.show()

    @pyqtSlot(Exception)
    def on_download_error(self, exception: Exception):
        intro = _("An error occurred while updating the AMBOSS add-on.")
        title = _("Error:")
        showWarning(
            f"{intro}<br>{title}<br><tt>{exception}</tt><br><br>{self._support_stub()}",
            parent=self._main_window,
            textFormat="rich",
        )

    @pyqtSlot(str)
    def on_download_done(self, path: str):
        result = self._addon_installer.install(path)

        if result.success is False:
            message = _("An error occurred while updating the AMBOSS add-on.")

            if result.message:
                message += "<br><br>" + result.message

            showWarning(
                f"{message}<br><br>{self._support_stub()}",
                parent=self._main_window,
                title=_("AMBOSS - Update"),
                textFormat="rich",
            )
        else:
            intro = _("The AMBOSS add-on was updated successfully.")
            cta = _("Please restart Anki to enable the changes.")
            showInfo(
                f"{intro}<br><br>{cta}",
                parent=self._main_window,
                title=_("AMBOSS - Update"),
                textFormat="rich",
            )

    @pyqtSlot()
    def block(self):
        tooltip(_("Update check is already in progress. Please hold on."))

    @pyqtSlot()
    def on_cancel(self):
        if self._update_download_worker:
            self._update_download_worker.cancel()
        tooltip(_("Update canceled."))

    def _support_stub(self) -> str:
        part1 = _("If the problem persists, please")
        part2 = _("let us know")
        return (
            f"{part1} "
            f"<a href='{self._support_uri}?utm_source=anki&utm_medium=anki_update_error&utm_campaign=anki'>{part2}</a>."
        )
