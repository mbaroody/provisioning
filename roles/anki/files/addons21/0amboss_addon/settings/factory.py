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

from typing import Callable, List, Literal, Optional

from aqt.qt import QWidget

from ..config import AddonConfig
from ..user import UserService
from .dialog import SettingsDialog
from .extensions import SettingsExtension


class SettingsDialogFactory:
    def __init__(self, config: AddonConfig, user_service: UserService):
        self._config = config
        self._user_service = user_service
        self._extensions: List["SettingsExtension"] = []

    def register_extension(self, extension: "SettingsExtension"):
        self._extensions.append(extension)

    def create(self, parent: Optional[QWidget] = None) -> SettingsDialog:
        return SettingsDialog(
            config=self._config,
            logged_in=self._user_service.is_logged_in(),
            article_access=self._user_service.has_article_access(),
            extensions=self._extensions,
            parent=parent,
        )


def create_config_action(
    settings_dialog_factory: SettingsDialogFactory,
    parent: QWidget,
) -> Callable[[], Literal[True]]:
    def config_action():
        settings_dialog = settings_dialog_factory.create(parent)
        settings_dialog.show_modal()
        return True  # return True to prevent Anki from showing the default dialog

    return config_action
