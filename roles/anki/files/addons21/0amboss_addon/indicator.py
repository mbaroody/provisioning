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


import json
from typing import TYPE_CHECKING, Optional

from aqt.qt import QObject, pyqtSignal, pyqtSlot

from .config import AddonConfig, HotkeySettingName
from .shared import _
from .theme import ThemeManager

if TYPE_CHECKING:
    from aqt.main import AnkiQt


class Indicator(QObject):

    clicked = pyqtSignal()

    def __init__(
        self,
        main_window: "AnkiQt",
        theme_manager: ThemeManager,
        addon_config: AddonConfig,
        show: bool = False,
    ):
        super().__init__(parent=main_window)
        self._main_window = main_window
        self._theme_manager = theme_manager
        self._addon_config = addon_config
        self.show = show

        self._addon_config.signals.saved.connect(self.toolbar_redraw)

    def indicator_markup(self) -> str:
        hotkey = self._addon_config[HotkeySettingName.TOGGLE_SIDE_PANEL.value]
        theme_class = (
            "amboss-indicator-night"
            if self._theme_manager.night_mode
            else "amboss-indicator-day"
        )
        cta = _("Open AMBOSS viewer")
        return f"""\
<a
 title="{cta} ({hotkey})"
 href=#
 onclick="return pycmd('amboss:side_panel:toggle');"
 data_e2e_test_id="amboss-action-indicator"
>
<span
  class="amboss-indicator {theme_class}"
>
</span>
</a>
"""

    @pyqtSlot()
    def toggle(self, show: Optional[bool] = None):
        self.show = show if show is not None else not show
        self._main_window.toolbar.web.eval(
            f"ambossAddon.indicator.toggle({json.dumps(self.show)});"
        )

    @pyqtSlot()
    def toolbar_redraw(self):
        """
        Redraw the toolbar to sync the indicator to config state
        (e.g. updating the hotkey in the tooltip message)
        """
        toolbar = self._main_window.toolbar
        if hasattr(toolbar, "redraw"):
            toolbar.redraw()  # 2.1.28+
        else:
            toolbar.draw()
