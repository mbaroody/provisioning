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

from contextlib import contextmanager
from typing import Optional

from aqt.qt import (
    QHBoxLayout,
    QLabel,
    QSlider,
    QSpinBox,
    Qt,
    QWidget,
    pyqtSignal,
    pyqtSlot,
)


class SliderSpinboxWidget(QWidget):
    """
    Convenience widget that combines a QSlider and a QSpinBox, using
    custom logic to store and restore the last user-entered value after
    the maximum value has been changed.

    Explanation on custom logic:

    We listen to each session size change triggered by the user and store it
    as the new user preference. To avoid storing programmatic changes to the
    session size as a user preference, we disable signaling on programmatic
    changes. With signaling disabled, we update the UI imperatively and emit
    associated signals manually.
    """

    value_changed = pyqtSignal(int)

    def __init__(
        self,
        initial: int = 10,
        minimum: int = 1,
        maximum: int = 5000,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        layout_main = QHBoxLayout()
        layout_main.setContentsMargins(0, 0, 0, 0)
        layout_spinbox = QHBoxLayout()
        layout_spinbox.setSpacing(2)

        self.slider = QSlider(self)
        self.slider.setOrientation(Qt.Orientation.Horizontal)
        self.slider.setTickPosition(QSlider.TickPosition.NoTicks)
        self.slider.setObjectName("slider")

        self.spinbox = QSpinBox(self)
        self.spinbox.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.spinbox.setObjectName("spinbox")
        layout_spinbox.addWidget(self.spinbox)
        self.max_value = QLabel(self)
        layout_spinbox.addWidget(self.max_value)

        layout_main.addWidget(self.slider)
        layout_main.addLayout(layout_spinbox)
        self.setLayout(layout_main)

        self.slider.valueChanged["int"].connect(self.spinbox.setValue)
        self.spinbox.valueChanged["int"].connect(self.slider.setValue)
        self.spinbox.valueChanged["int"].connect(self.value_changed.emit)
        self.spinbox.valueChanged["int"].connect(self._cache_last_user_entered_value)

        if not (minimum <= initial <= maximum):
            raise ValueError("Invalid initial, minimum, or maximum value.")

        self._last_user_entered_value = initial
        self._last_minimum = minimum
        # avoid multiple calls to set_value() when initializing:
        self._set_minimum_without_storing(minimum)
        self._set_maximum(maximum)
        self.set_value(initial)

    def get_value(self) -> int:
        return self.spinbox.value()

    def get_maximum(self) -> int:
        return self.spinbox.maximum()

    def get_minimum(self) -> int:
        return self.spinbox.minimum()

    def set_value(self, value: int):
        with block_signals(self.spinbox, self.slider):
            self.spinbox.setValue(value)
            self.slider.setValue(value)
        self.value_changed.emit(value)

    def set_maximum(self, maximum: int):
        should_constrict_value = maximum == 0 or maximum < self.get_value()
        should_constrict_minimum = maximum == 0 or maximum < self.get_minimum()

        self._set_maximum(maximum)

        # potentially constrict value and minimum, or restore them to their last
        # values:

        if should_constrict_value:
            self.set_value(maximum)
        elif self.get_value() != self._last_user_entered_value:
            self.set_value(self._last_user_entered_value)

        if should_constrict_minimum:
            self._set_minimum_without_storing(maximum)
        elif self.get_minimum() != self._last_minimum:
            self.set_minimum(self._last_minimum)

    def set_minimum(self, minimum: int):
        self._set_minimum_without_storing(minimum)
        self._last_minimum = minimum

    def _set_maximum(self, maximum: int):
        with block_signals(self.spinbox, self.slider):
            self.spinbox.setMaximum(maximum)
            self.slider.setMaximum(maximum)
        self.max_value.setText(f" / {maximum}")

    def _set_minimum_without_storing(self, minimum: int):
        with block_signals(self.spinbox, self.slider):
            self.spinbox.setMinimum(minimum)
            self.slider.setMinimum(minimum)

    @pyqtSlot()
    def _cache_last_user_entered_value(self):
        self._last_user_entered_value = self.get_value()


@contextmanager
def block_signals(*widgets: QWidget):
    """
    Block signal emission, e.g. when setting a value on a widget in order to
    distinguish between user input and programmatic changes.

    When entering the block_signals context, we need to save the initial state
    at blocking time and restore it when exiting. Naively, we would block and
    unblock, but this does not account for the fact of the signal being already
    blocked, when entering, e.g. due to a block performed by upstream code
    (e.g. Qt or the widget library).

    Therefore we store the initial states through widget.blockSignals(True)
    which will return False if the signal was blocked, and True if it was not,
    and allows us to restore.
    """

    block_signals = [(widget, widget.blockSignals(True)) for widget in widgets]
    try:
        yield
    finally:
        for widget, block_signal in block_signals:
            widget.blockSignals(block_signal)
