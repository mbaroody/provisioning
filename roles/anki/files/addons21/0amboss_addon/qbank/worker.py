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

import weakref
from typing import Any, Callable, NamedTuple

from aqt.qt import QObject, QRunnable, pyqtSignal, pyqtSlot, sip

from .performance import Event


class Progress(NamedTuple):
    message: str
    value_percent: float  # 0 - 100
    delay: int = 0  # seconds


SubmitProgress = Callable[[Progress], None]
SubmitEvent = Callable[[Event], None]


class TrackedWorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(Exception)
    result = pyqtSignal(object)
    performance_event = pyqtSignal(object)  # performance.Event
    progress = pyqtSignal(object)  # Progress


class TrackedWorker(QRunnable):
    def __init__(
        self,
        task: Callable[[SubmitProgress, SubmitEvent], Any],
        receiver: QObject,
    ):
        super().__init__()
        self._task = task
        self._canceled = False
        self._receiver_ref = weakref.ref(receiver)
        self.signals = TrackedWorkerSignals()

    @pyqtSlot()
    def run(self):
        if self.is_cancelled_or_deleted():
            return

        exception = None
        result = None

        try:
            result = self._task(self.submit_progress, self.submit_event)
        except Exception as e:
            exception = e

        if self.is_cancelled_or_deleted():
            return

        if exception:
            self.signals.error.emit(exception)
        else:
            self.signals.result.emit(result)

        self.signals.finished.emit()

    def cancel(self):
        self._canceled = True

    def is_cancelled_or_deleted(self) -> bool:
        """As TrackedWorker is a QRunnable without a parent, it is not
        automatically deleted when the receiver is deleted. To prevent
        signalling to a deleted receiver, we store a weak reference to
        the receiver and gate signalling behind the following check
        that asserts that neither the receiver has been gc'ed
        nor the C/C++ object it wraps, nor the TrackedWorkerSignals
        instance we emit signals through.
        """
        receiver = self._receiver_ref()
        return (
            self._canceled
            or (receiver and sip.isdeleted(receiver))
            or sip.isdeleted(self.signals)
        )

    def submit_progress(self, progress: Progress):
        if not self.is_cancelled_or_deleted():
            self.signals.progress.emit(progress)

    def submit_event(self, event: Event):
        if not self.is_cancelled_or_deleted():
            self.signals.performance_event.emit(event)
