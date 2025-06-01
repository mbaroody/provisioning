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

from typing import TYPE_CHECKING

from aqt.gui_hooks import state_did_change
from aqt.qt import QObject, pyqtSignal

if TYPE_CHECKING:
    from aqt.main import AnkiQt, MainWindowState


class AnkiStateService(QObject):

    state_switched_to_deckbrowser = pyqtSignal()

    def __init__(self, main_window: "AnkiQt"):
        super().__init__(main_window)
        state_did_change.append(self.on_main_window_state_change)  # type: ignore

    def on_main_window_state_change(
        self, new_state: "MainWindowState", previous_state: "MainWindowState"
    ):
        # skip initial deckBrowser state switch after launch
        if new_state == "deckBrowser" and previous_state not in (
            "profileManager",
            "startup",
        ):
            self.state_switched_to_deckbrowser.emit()
