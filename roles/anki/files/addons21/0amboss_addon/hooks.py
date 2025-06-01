# AMBOSS Anki Add-on
#
# Copyright (C) 2019-2020 AMBOSS MD Inc. <https://www.amboss.com/us>
# Copyright (C) 2020 Ankitects Pty Ltd and contributors
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

"""
Custom hooks, based on Anki's typed new-style hook system
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Callable, List, Optional

try:
    from anki.hooks import (  # might be removed in the future
        addHook,
        remHook,
        runHook,
    )
except (ImportError, ModuleNotFoundError):
    addHook = remHook = runHook = None  # type: ignore[assignment]

if TYPE_CHECKING:
    import anki  # noqa: F401
    import anki.cards  # noqa: F401


class HookException(Exception):
    pass


class HookModule(Enum):
    AQT = "aqt.gui_hooks"
    ANKI = "anki.hooks"


class _Hook(ABC):
    @abstractmethod
    def append(self, v):
        ...

    @abstractmethod
    def remove(self, v):
        ...

    @abstractmethod
    def __call__(self, *args, **kwargs):
        ...


# Legacy anki hooks support


class _LegacyShimHook:

    """
    Provides a shim between Anki's legacy hook system and new-style hooks with
    support for type annotations

    Subclasses should implement the type-annotations of the new-style hook they
    wrap
    """

    _legacy_hook_name: str  # Name on Anki < 2.1.20
    _new_hook_name: str  # Name on Anki >= 2.1.20
    _hook_module: HookModule

    _hook: Optional[_Hook]

    def __init__(self):
        try:  # New-style hooks
            # not using importlib because we can't be sure Anki ships with it
            hook_module = __import__(
                self._hook_module.value, fromlist=self._new_hook_name
            )
            self._hook = getattr(hook_module, self._new_hook_name)
        except (ImportError, ModuleNotFoundError):  # Legacy-style hooks
            if not addHook or not remHook or not runHook:
                # This should never happen
                raise HookException("Could not hook into Anki")
            self._hook = None

    def append(self, cb: Callable) -> None:
        if self._hook:
            self._hook.append(cb)
        elif addHook:
            addHook(self._legacy_hook_name, cb)

    def remove(self, cb: Callable) -> None:
        if self._hook:
            self._hook.remove(cb)
        elif remHook:
            remHook(self._legacy_hook_name, cb)

    def __call__(self) -> None:
        if self._hook:
            self._hook()
        elif runHook:
            runHook(self._legacy_hook_name)


class _ProfileDidOpenHook(_LegacyShimHook):
    _legacy_hook_name = "profileLoaded"
    _new_hook_name = "profile_did_open"  # Anki >=2.1.20
    _hook_module = HookModule.AQT

    def append(self, cb: Callable[[], None]):
        """()"""
        super().append(cb)

    def remove(self, cb: Callable[[], None]):
        """()"""
        super().remove(cb)


class _ProfileWillCloseHook(_LegacyShimHook):
    _legacy_hook_name = "unloadProfile"
    _new_hook_name = "profile_will_close"  # Anki >=2.1.20
    _hook_module = HookModule.AQT

    def append(self, cb: Callable[[], None]):
        super().append(cb)

    def remove(self, cb: Callable[[], None]):
        super().remove(cb)


class _ReviewerDidShowQuestionHook(_LegacyShimHook):
    _legacy_hook_name = "showQuestion"
    _new_hook_name = "reviewer_did_show_question"  # Anki >=2.1.20
    _hook_module = HookModule.AQT

    def append(self, cb: Callable[["anki.cards.Card"], None]):
        """
        (card: Card)
        NOTE: Legacy hook does not supply card object
        """
        super().append(cb)

    def remove(self, cb: Callable[["anki.cards.Card"], None]):
        """
        (card: Card)
        NOTE: Legacy hook does not supply card object
        """
        super().remove(cb)


class _ReviewerDidShowAnswerHook(_LegacyShimHook):
    _legacy_hook_name = "showAnswer"
    _new_hook_name = "reviewer_did_show_answer"  # Anki >=2.1.20
    _hook_module = HookModule.AQT

    def append(self, cb: Callable[["anki.cards.Card"], None]):
        """
        (card: Card)
        NOTE: Legacy hook does not supply card object
        """
        super().append(cb)

    def remove(self, cb: Callable[["anki.cards.Card"], None]):
        """
        (card: Card)
        NOTE: Legacy hook does not supply card object
        """
        super().remove(cb)


profile_did_open = _ProfileDidOpenHook()
profile_will_close = _ProfileWillCloseHook()
reviewer_did_show_question = _ReviewerDidShowQuestionHook()
reviewer_did_show_answer = _ReviewerDidShowAnswerHook()


# Custom new-style hooks


class AMBOSSHook(_Hook):
    def __init__(self):
        self._hooks: List[Callable[[], None]] = []

    def append(self, cb: Callable[[], None]) -> None:
        """()"""
        self._hooks.append(cb)

    def remove(self, cb: Callable[[], None]) -> None:
        """()"""
        if cb in self._hooks:
            self._hooks.remove(cb)

    def __call__(self) -> None:  # type: ignore[override]
        for hook in self._hooks:
            try:
                hook()
            except:  # noqa: E722
                # if the hook fails, remove it
                self._hooks.remove(hook)
                raise


amboss_did_access_change = AMBOSSHook()
amboss_did_login = AMBOSSHook()
amboss_did_logout = AMBOSSHook()
amboss_did_firstrun = AMBOSSHook()
