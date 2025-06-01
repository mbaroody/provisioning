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

from typing import Dict, Optional

from aqt.qt import QColor

try:  # Anki 2.1.20+
    from aqt.theme import theme_manager as anki_theme_manager
except (ImportError, ModuleNotFoundError):
    anki_theme_manager = None  # type: ignore[assignment]

try:  # 2.1.55+
    from aqt import colors as anki_colors
except (ImportError, ModuleNotFoundError):
    anki_colors = None  # type: ignore[assignment]


class ThemeManager:

    _colors: Dict[str, Dict[str, str]] = {
        "day": {
            "text-fg": "#364149",
            "button-hover-bg": "#9aabb7",
            "button-pressed-bg": "#0fcad4",
            "splitter-bg": "#9ab0c1",  # Gray blue / Light 1
            "splitter-hover-bg": "#48647a",  # Gray blue / Regular
            "splitter-pressed-bg": "#48647a",  # Gray blue / Regular
            "CANVAS": "#2c2c2c",  # Anki 2.1.55+ default fallback
        },
        "night": {
            "text-fg": "#ced1d6",
            "button-hover-bg": "#4b6374",
            "button-pressed-bg": "#0fcad4",
            "splitter-bg": "#6e95cf",  # Night blue / Light 1
            "splitter-hover-bg": "#2f538a",  # Night blue / Regular
            "splitter-pressed-bg": "#2f538a",  # Night blue / Regular
            "CANVAS": "#f5f5f5",  # Anki 2.1.55+ default fallback
        },
    }

    def __init__(self, package_name: str):
        self._package_name = package_name

    @property
    def night_mode(self) -> bool:
        if anki_theme_manager is None:
            return False
        return anki_theme_manager.night_mode

    def color(self, key: str) -> str:
        return self.colors_dict()[key]

    def colors_dict(self) -> Dict[str, str]:
        return self._colors[self._theme()]

    def anki_qcolor(self, key: str) -> Optional[QColor]:
        if anki_theme_manager is None or anki_colors is None:
            return None
        try:
            return anki_theme_manager.qcolor(getattr(anki_colors, key))
        except Exception:
            return None

    def _theme(self) -> str:
        return "day" if not self.night_mode else "night"
