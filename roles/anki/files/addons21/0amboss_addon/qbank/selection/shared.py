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

from typing import Callable, Iterable

from aqt.qt import QCheckBox, pyqtBoundSignal


def create_checkbox_selection_state_guard(
    checkbox: QCheckBox,
    group: Iterable[QCheckBox],
    signal_on_change: pyqtBoundSignal,
) -> Callable[[bool], None]:
    def selection_state_guard(checked: bool):
        if checked is False and sum(cb.isChecked() for cb in group) == 0:
            # guard against removing last remaining checkmark
            checkbox.setChecked(True)
            return
        signal_on_change.emit()

    return selection_state_guard
