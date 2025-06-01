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

from typing import Callable, Dict, Optional, Union

from aqt.deckbrowser import DeckBrowser, DeckBrowserContent
from aqt.gui_hooks import deck_browser_will_render_content

from ..router import Router


class DeckBrowserPatcher:
    def __init__(self, stats_content_provider: Callable[[], str]):
        self._stats_content_provider = stats_content_provider

    def patch(self):
        def injector(
            deck_browser: DeckBrowser, deck_browser_content: DeckBrowserContent
        ):
            deck_browser_content.stats += self._stats_content_provider()

        deck_browser_will_render_content.append(injector)


DeckBrowserRoute = Union[Callable[[str], None], Callable[[], None]]


class DeckBrowserRouter(Router):
    def __init__(self):
        self._commands: Dict[str, DeckBrowserRoute] = {}

    def connect_command(self, cmd: str, action: DeckBrowserRoute):
        self._commands[cmd] = action

    def __call__(self, cmd: str, arg: Optional[str] = None):
        if cmd not in self._commands:
            return
        action = self._commands[cmd]
        action(arg) if arg is not None else action()  # type: ignore[call-arg]
