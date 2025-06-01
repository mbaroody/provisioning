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


from typing import Callable

from aqt.qt import QObject, QRunnable, pyqtSignal, pyqtSlot


class Worker(QRunnable):
    def __init__(self, task: Callable, *args, **kwargs):
        super(Worker, self).__init__()
        self._task = task
        self._args = args
        self._kwargs = kwargs
        self.canceled = False
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            result = self._task(*self._args, **self._kwargs)
        except Exception as e:
            self.signals.error.emit(e)
        else:
            self.signals.result.emit(result, self.canceled)
        finally:
            self.signals.finished.emit()


class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(Exception)
    result = pyqtSignal(object, bool)
