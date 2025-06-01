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


from typing import Any, Callable, List

from aqt.qt import QObject, pyqtSignal


class SimpleHook:
    def __init__(self):
        self._callbacks: List[Callable[[], Any]] = []

    def append(self, cb: Callable[[], Any]):
        self._callbacks.append(cb)

    def remove(self, cb: Callable[[], Any]):
        self._callbacks.remove(cb)

    def __call__(self):
        for callback in self._callbacks:
            callback()


class SimpleSingleShotHook(SimpleHook):
    def __init__(self):
        super().__init__()
        self._called: bool = False

    def __call__(self):
        if self._called:
            return
        super().__call__()
        self._called = True


class HookSignalMediator(QObject):
    """Small Qt object that can be used to transform a hook call into
    a signal that can be connected to from a different thread.

    Useful for custom hooks that are fired off in background threads.
    """

    called = pyqtSignal()

    def __call__(self):
        self.called.emit()
