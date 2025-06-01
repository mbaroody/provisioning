# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from collections.abc import Iterable
from typing import NamedTuple, Optional

from aqt.qt import *


class GridWidgetPosition(NamedTuple):
    widget: QWidget
    row: int
    col: int


def widgets_to_grid_items(widgets: Iterable[QWidget], n_columns: int = 2) -> Iterable[GridWidgetPosition]:
    row = col = 1
    for widget in widgets:
        yield GridWidgetPosition(widget, row, col)
        if col < n_columns:
            col += 1
        else:
            row += 1
            col = 1


def place_widgets_in_grid(
    widgets: Iterable[QWidget],
    n_columns: int = 2,
    alignment: Optional[Qt.AlignmentFlag] = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
) -> QGridLayout:
    grid = QGridLayout()
    if alignment is not None:
        grid.setAlignment(alignment)
    for item in widgets_to_grid_items(widgets, n_columns):
        grid.addWidget(item.widget, item.row, item.col)
    return grid
