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


import os
import tempfile
from hashlib import sha1
from typing import TYPE_CHECKING, Iterator, NamedTuple, Optional
from urllib.parse import urlparse
from zipfile import ZipFile

import requests
from aqt.qt import QThread, pyqtSignal
from packaging.version import parse as parse_version
from requests.exceptions import HTTPError
from send2trash import send2trash  # type: ignore[import]

from .anki.updates import suppress_ankiweb_updates
from .hooks import profile_did_open
from .notification import NotificationService, UpdateData
from .shared import _, safe_print

if TYPE_CHECKING:
    from aqt.addons import AddonManager


class UpdateDownloadClient:
    def __init__(self, url: str, path: str):
        self._url = url
        self._path = path

    def download_chunk(self, chunk_size: int) -> Iterator[int]:
        with requests.get(self._url, stream=True) as result:
            result.raise_for_status()
            with open(self._path, "wb") as file:
                for chunk in result.iter_content(chunk_size=chunk_size):
                    if chunk:
                        file.write(chunk)
                        yield chunk_size

    def get_path(self) -> str:
        return self._path


class UpdateDownloadClientFactory:
    @staticmethod
    def create(update_data: UpdateData) -> UpdateDownloadClient:
        url = update_data.url
        url_obj = urlparse(url)
        file_name = os.path.basename(url_obj.path)
        save_path = os.path.join(tempfile.gettempdir(), file_name)
        return UpdateDownloadClient(url, save_path)


class SHA1Hasher:
    @staticmethod
    def hash(path: str) -> str:
        block_size = 65536
        hasher = sha1()
        with open(path, "rb") as source:
            block = source.read(block_size)
            while len(block) > 0:
                hasher.update(block)
                block = source.read(block_size)
        return hasher.hexdigest()


class UpdateDownloadWorker(QThread):
    chunk_downloaded = pyqtSignal(int)  # byte chunk downloaded
    done = pyqtSignal(str)  # path to file
    error = pyqtSignal(object)  # exception
    canceled = pyqtSignal()

    def __init__(self, update_data: UpdateData, chunk_size: int = 10000):
        super().__init__()

        # injected
        self._update_data = update_data
        self._chunk_size = chunk_size

        # state
        self._canceled: bool = False

    def run(self):
        downloader = UpdateDownloadClientFactory.create(self._update_data)

        try:
            for chunk_length in downloader.download_chunk(self._chunk_size):
                if self._canceled:
                    self.canceled.emit()
                    return
                self.chunk_downloaded.emit(chunk_length)
        except (HTTPError, ConnectionError) as e:
            self.error.emit(e)

        actual_sha1 = SHA1Hasher.hash(downloader.get_path())
        if self._update_data.sha1 and self._update_data.sha1 != actual_sha1:
            self.error.emit(
                Exception(
                    _(
                        "Expected downloaded file to match hash '{}', got '{}' instead"
                    ).format(self._update_data.sha1, actual_sha1)
                )
            )

        self.done.emit(downloader.get_path())

    def cancel(self):
        self._canceled = True


class UpdateNotificationService(QThread):
    # update_available: bool, interactive: bool, update_data: UpdateData
    result = pyqtSignal(bool, bool, object)
    blocked = pyqtSignal()

    def __init__(self, notification_service: NotificationService, version: str):
        super().__init__()
        self._notification_service = notification_service
        self._version = version
        self._interactive = False

    def deferred_run(self):
        profile_did_open.append(self.start)

    def start(self, *args, interactive=False, **kwargs):
        if self.isRunning():
            self.blocked.emit()
            return
        self._interactive = interactive
        super().start(*args, **kwargs)

    def run(self):
        update_data = self._notification_service.update_notification().min

        self.result.emit(
            self._update_available(update_data), self._interactive, update_data
        )

    def _update_available(self, update_data: UpdateData) -> bool:
        return parse_version(update_data.version) > parse_version(self._version)


class InstallationResult(NamedTuple):
    success: bool
    message: Optional[str] = None


class AddonInstaller:
    def __init__(self, addon_manager: "AddonManager", overwrite_enabled: bool = False):
        self._addon_manager = addon_manager
        self._overwrite_enabled = overwrite_enabled

    def install(self, addon_file_path: str) -> InstallationResult:
        if not self._overwrite_enabled:
            return InstallationResult(
                success=False,
                message=_("AMBOSS cannot be updated as overwriting is disabled."),
            )

        current_package_name = self._addon_manager.addonFromModule(__name__)

        try:
            new_package_name = self._read_package_name(addon_file_path)
        except Exception as e:
            return InstallationResult(
                success=False,
                message=_(
                    "AMBOSS cannot be updated as there seems to be an"
                    " issue with the downloaded update file:<br><br>"
                )
                + str(e),
            )

        config_backup: Optional[dict] = None

        if new_package_name != current_package_name:
            config_backup = self._addon_manager.getConfig(current_package_name)

            deleted_ok = self._delete_addon(current_package_name)

            if not deleted_ok:
                return InstallationResult(
                    success=False,
                    message=_(
                        "AMBOSS cannot be updated as there's a conflicting"
                        " old duplicate."
                    )
                    + " "
                    + _("Please check your file permissions."),
                )

        raw_result = self._addon_manager.install(addon_file_path)

        install_ok = self._installation_result(raw_result=raw_result)

        if install_ok:
            if config_backup is not None:
                # Restore config on package name migration
                self._addon_manager.writeConfig(new_package_name, config_backup)

            # Workaround: Re-enable add-on if disabled due to faulty conflict management
            if hasattr(self._addon_manager, "addon_meta"):  # >= 2.1.20
                addon_meta = self._addon_manager.addon_meta(new_package_name)
                addon_meta.enabled = True
                self._addon_manager.write_addon_meta(addon_meta)
            else:
                addon_meta_dict = self._addon_manager.addonMeta(new_package_name)
                addon_meta_dict["disabled"] = False
                self._addon_manager.writeAddonMeta(new_package_name, addon_meta_dict)

        return InstallationResult(success=install_ok)

    def _installation_result(self, raw_result) -> bool:
        class_name = raw_result.__class__.__name__
        if class_name in ["tuple", "AddonInstallationResult"]:
            # TODO: can we fix this ignore?
            return raw_result[0]  # type: ignore[index]
        if class_name == "InstallOk":
            return True
        return False  # class_name == "InstallError"

    def _delete_addon(self, package_name: str) -> bool:
        self._addon_manager.backupUserFiles(package_name)
        try:
            send2trash(self._addon_manager.addonsFolder(package_name))
            return True
        except OSError:
            self._addon_manager.restoreUserFiles(package_name)
        return False

    def _read_package_name(self, addon_file_path: str) -> str:
        with ZipFile(addon_file_path) as zfile:
            manifest = self._addon_manager.readManifestFile(zfile)
        package_name = manifest["package"]
        if not package_name:
            raise ValueError("Invalid add-on package name.")
        return package_name


class AnkiWebUpdateHandler:
    @staticmethod
    def disable_updates(addon_path: str):
        try:
            suppress_ankiweb_updates(addon_path)
        except Exception as e:
            safe_print(f"Could not disable AnkiWeb updates: {e}")
