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

from typing import Dict

from aqt.qt import QKeySequence, QObject, QShortcut, QWidget, pyqtSignal

from .config import AddonConfig, HotkeySettingName


class HotkeyManager(QObject):

    # NOTE: variable naming must be kept in sync with config.HotkeySettingName
    hotkeyOpenNextPopup = pyqtSignal()
    hotkeyOpenPreviousPopup = pyqtSignal()
    hotkeyClosePopup = pyqtSignal()
    hotkeyToggleSidePanel = pyqtSignal()

    def __init__(self, parent: QWidget, addon_config: AddonConfig):
        super().__init__(parent=parent)
        self._addon_config = addon_config
        self._shortcuts: Dict[str, QShortcut] = {}
        self.register_hotkeys()
        self._addon_config.signals.saved.connect(self._on_config_saved)

    def _on_config_saved(self):
        self.update_hotkeys()

    def register_hotkeys(self):
        # parent is always a QWidget, but pyright does not understand that
        parent: QWidget = self.parent()  # type: ignore

        for hotkey_setting in HotkeySettingName:
            name = hotkey_setting.value
            shortcut = QShortcut(
                QKeySequence(self._addon_config[name]),
                parent,
            )
            # connect shortcut to signals of same name defined as class attributes:
            hotkey_signal = getattr(self, name)
            shortcut.activated.connect(hotkey_signal)
            self._shortcuts[name] = shortcut

    def update_hotkeys(self):
        for hotkey_setting in HotkeySettingName:
            name = hotkey_setting.value
            shortcut = self._shortcuts[name]
            shortcut.setKey(QKeySequence(self._addon_config[name]))
