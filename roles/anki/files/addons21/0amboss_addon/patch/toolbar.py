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


import json
from typing import TYPE_CHECKING, Any, Callable, List, Tuple, Union

from ..controller import CONTROLLER_PREFIX, Controller
from ..indicator import Indicator
from . import Patcher

if TYPE_CHECKING:
    from aqt.toolbar import TopToolbar  # 2.1.22+
    from aqt.toolbar import Toolbar  # type-hints only, separate import for legacy paths
    from aqt.webview import WebContent  # 2.1.22+
else:
    # this weird pattern is needed for mypy to not complain while still being
    # able to evaluate TopToolbar outside of TYPE_CHECKING
    try:
        from aqt.toolbar import TopToolbar
    except (ImportError, ModuleNotFoundError):
        TopToolbar = None


class TopToolbarHookPatcher(Patcher):
    def __init__(
        self,
        controller: Controller,
        package_name: str,
        indicator: Indicator,
        js: Tuple[str, ...] = (),
    ):
        self._controller = controller
        self._package_name = package_name
        self._indicator = indicator
        self._js = js

    def patch(self):
        from aqt.gui_hooks import (
            top_toolbar_did_init_links,
            webview_did_receive_js_message,
            webview_will_set_content,
        )

        webview_will_set_content.append(self._on_webview_will_set_content)
        webview_did_receive_js_message.append(self._on_webview_did_receive_js_message)
        top_toolbar_did_init_links.append(self._on_top_toolbar_did_init_links)

    def _on_webview_will_set_content(
        self, web_content: "WebContent", context: Union[Any, "TopToolbar"]
    ):
        if TopToolbar is None or not isinstance(context, TopToolbar):
            return

        web_content.js += [f"/_addons/{self._package_name}/web/{f}" for f in self._js]
        web_content.head += "\n".join(
            [
                f"<script>ambossAddon.indicator.toggle({json.dumps(self._indicator.show)});</script>"
            ]
        )
        web_content.css.append(f"/_addons/{self._package_name}/web/css/indicator.css")

    def _on_webview_did_receive_js_message(
        self, handled: Tuple[bool, Any], message: str, context: Any
    ) -> Tuple[bool, Any]:
        if not isinstance(context, TopToolbar):
            return handled
        if not message.startswith(CONTROLLER_PREFIX):
            return handled
        return True, self._controller(message)

    def _on_top_toolbar_did_init_links(self, links: List[str], *args):
        links.append(self._indicator.indicator_markup())


class TopToolbarMonkeyPatcher(Patcher):
    def __init__(
        self,
        controller: Controller,
        package_name: str,
        indicator: Indicator,
        js: Tuple[str, ...] = (),
    ):
        self._controller = controller
        self._package_name = package_name
        self._indicator = indicator
        self._js = js

    def patch(self):
        from anki.hooks import wrap as anki_wrap
        from aqt.toolbar import Toolbar

        Toolbar._linkHTML = anki_wrap(Toolbar._linkHTML, self._link_html, "around")  # type: ignore
        Toolbar._linkHandler = anki_wrap(  # type: ignore
            Toolbar._linkHandler, self._link_handler, "around"
        )
        self._indicator.toolbar_redraw()

    def _link_html(self, toolbar: "Toolbar", links: List[str], _old: Callable) -> str:
        return "\n".join(
            [
                f"""<script src="/_addons/{self._package_name}/web/{f}"></script>"""
                for f in self._js
            ]
            + [
                f"<script>ambossAddon.indicator.toggle({json.dumps(self._indicator.show)});</script>",
                _old(toolbar, links),
                f"""<link rel="stylesheet" href="/_addons/{self._package_name}/web/css/indicator.css">""",
                self._indicator.indicator_markup(),
            ]
        )

    def _link_handler(self, toolbar: "Toolbar", link: str, _old: Callable):
        if not link.startswith(CONTROLLER_PREFIX):
            return _old(toolbar, link)
        return self._controller(link)


class TopToolbar22Patcher(TopToolbarHookPatcher, TopToolbarMonkeyPatcher):
    """Supports Anki 2.1.22+. Uses hooks where applicable, monkey-patching where not."""

    def patch(self):
        from anki.hooks import wrap as anki_wrap
        from aqt.toolbar import Toolbar

        super().patch()
        Toolbar._linkHTML = anki_wrap(Toolbar._linkHTML, super()._link_html, "around")  # type: ignore
