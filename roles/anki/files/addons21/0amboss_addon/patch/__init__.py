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


from abc import ABC, abstractmethod

from ..hooks import profile_did_open


class Patcher(ABC):
    @abstractmethod
    def patch(self):
        raise NotImplementedError


class MultiPatcher:
    """
    Patches Anki classes, e.g., to use our controller on Anki's python-javascript bridge.
    Forgivingly tries patch strategies in descending order until one works.
    """

    def __init__(self, *patch_strategies: Patcher):
        self._patch_strategies = patch_strategies
        self._patched: bool = False

    def defer_patch_once(self):
        """
        Defer patch until profile loaded to win out in possible add-on conflicts
        when using the monkey-patch strategy.
        """
        profile_did_open.append(self.patch_once)

    def patch_once(self):
        """
        Only fire on first profile load. Hook subscriptions persist across
        profile switches, so we do not want to repeat them on next profile load
        """
        if self._patched:
            return
        self._patch()
        self._patched = True

    def _patch(self):
        exc = None
        for patch_strategy in self._patch_strategies:
            try:
                patch_strategy.patch()
            except Exception as e:
                exc = e
            else:
                return
        if exc:
            raise exc
