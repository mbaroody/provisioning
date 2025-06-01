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

from abc import ABC, abstractmethod
from collections import UserDict
from enum import Enum
from typing import TYPE_CHECKING

from aqt.qt import QObject, pyqtSignal

from .profile import ProfileAdapter

if TYPE_CHECKING:
    from aqt.addons import AddonManager


class SettingNameEnum(Enum):
    """Enum for setting names. Assumed to be in sync with config.json config keys"""

    pass


class HotkeySettingName(SettingNameEnum):
    """
    The values of this enum are assumed to be kept in sync with:
    - config.json
    - signal names in hotkeys.py
    """

    OPEN_NEXT_POPUP = "hotkeyOpenNextPopup"
    OPEN_PREVIOUS_POPUP = "hotkeyOpenPreviousPopup"
    CLOSE_POPUP = "hotkeyClosePopup"
    TOGGLE_SIDE_PANEL = "hotkeyToggleSidePanel"


class DisplaySettingName(SettingNameEnum):
    """
    The values of this enum are assumed to be kept in sync with:
    - config.json
    """

    ENABLE_GENERAL = "enablePopupDefinitions"
    ENABLE_QUESTION = "enablePopupDefinitonsOnQuestions"
    ENABLE_ARTICLE_VIEWER = "enableArticleViewer"


class ColorSettingName(SettingNameEnum):

    """
    The values of this enum are assumed to be kept in sync with:
    - config.json
    """

    HIGHLIGHTS = "styleColorHighlights"


class ConfigError(Exception):
    pass


class ConfigSignals(QObject):
    saved = pyqtSignal()
    changed = pyqtSignal(object)  # dictionary of changed config values


class ConfigProvider(ABC):
    @abstractmethod
    def read(self) -> dict:
        pass

    @abstractmethod
    def write(self, data: dict):
        pass

    @abstractmethod
    def read_defaults(self) -> dict:
        pass


class AnkiJSONConfigProvider(ConfigProvider):
    def __init__(
        self,
        addon_package: str,
        addon_manager: "AddonManager",
    ):
        self._addon_package = addon_package
        self._addon_manager = addon_manager

    def read(self) -> dict:
        config = self._addon_manager.getConfig(self._addon_package)
        if config is None:
            # this should never happen, unless add-on files have been
            # tampered with
            raise ConfigError("Could not read add-on configuration")
        return config

    def write(self, data: dict):
        self._addon_manager.writeConfig(self._addon_package, data)

    def read_defaults(self) -> dict:
        defaults = self._addon_manager.addonConfigDefaults(self._addon_package)
        if defaults is None:
            # this should never happen, unless add-on files have been
            # tampered with
            raise ConfigError("Could not read add-on configuration defaults")
        return defaults


class AddonConfig(UserDict):
    def __init__(
        self,
        config_provider: ConfigProvider,
        config_signals: ConfigSignals,
        profile_adapter: ProfileAdapter,
    ):
        super().__init__()
        self._config_provider = config_provider
        self._profile_adapter = profile_adapter
        self.data = self._config_provider.read()
        self.signals = config_signals

    def save(self, emit_signal: bool = True):
        old_data = self._config_provider.read()
        changed_data = {}

        for key, new_value in self.data.items():
            if old_data.get(key) != new_value:
                changed_data[key] = new_value

        self._config_provider.write(self.data)

        if emit_signal:
            self.signals.saved.emit()
            if changed_data:
                self.signals.changed.emit(changed_data)

    def defaults(self) -> dict:
        return self._config_provider.read_defaults()
