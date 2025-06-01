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


from typing import TYPE_CHECKING, Any, Callable, Tuple, Union

from aqt.deckbrowser import DeckBrowser
from aqt.reviewer import Reviewer

from ..controller import Controller
from ..reviewer import wrap
from . import Patcher

if TYPE_CHECKING:
    from aqt.webview import WebContent  # 2.1.22+


class MainViewHookPatcher(Patcher):
    """
    Patches link handling to use our controller via hooks.
    Requires Anki >= 2.1.22
    """

    def __init__(self, controller: Controller):
        self._controller = controller

    def patch(self):
        from aqt.gui_hooks import webview_did_receive_js_message

        webview_did_receive_js_message.append(self._on_webview_did_receive_js_message)

    def _on_webview_did_receive_js_message(
        self, handled: Tuple[bool, Any], message: str, context: Any
    ) -> Tuple[bool, Any]:
        if not isinstance(context, (Reviewer, DeckBrowser)):
            return handled
        # FIXME: This is a bandaid to fix pycmd communication in the deckbrowser
        # Controller should return two values, one signalling whether message was
        # handled, one the return value if handled. However, changing this will
        # require more extensive modifications across many parts of the code base,
        # so for now we simply assume that False == not handled, which is going
        # to be the case in most cases, but not when the actual return value is False
        result = self._controller(message)
        if result is False:
            return handled
        return True, result


class ReviewerHTMLPatcher:
    """Injects our JS and CSS into reviewer web content."""

    def __init__(
        self,
        base_folder: str,
        js: Tuple[str, ...] = (),
        css: Tuple[str, ...] = (),
        css_calls: Tuple[Callable, ...] = (),
    ):
        self._base_folder = base_folder
        self._js = js
        self._css = css
        self._css_calls = css_calls

    def patch(self):
        """"""
        try:  # Anki 2.1.22+
            # register web content hook to update reviewer HTML content
            from aqt.gui_hooks import webview_will_set_content

            webview_will_set_content.append(self._on_webview_will_set_content)
        except (ImportError, ModuleNotFoundError):
            # Legacy: monkey-patch original Reviewer.revHtml method to add
            # our own web elements.
            # NOTE: consider using anki.hooks.wrap instead
            Reviewer.revHtml = wrap(
                Reviewer.revHtml, ReviewerHTMLPatcher._on_rev_html, self
            )

    def _on_webview_will_set_content(
        self, web_content: "WebContent", context: Union[Reviewer, Any]
    ):
        if not isinstance(context, Reviewer):
            # TODO?: Extend support to other web views
            return

        web_content.body += self._injection()

    def _injection(self):
        inject = "\n"
        for f in self._js:
            inject += f"""<script src="{self._base_folder}/{f}"></script>\n"""
        for f in self._css:
            inject += f"""<link rel="stylesheet" href="{self._base_folder}/{f}">\n"""
        for c in self._css_calls:
            inject += f"<style>{c()}</style>\n"
        return inject

    def _on_rev_html(self, reviewer: Reviewer, _old: Callable):
        """
        :param reviewer: original Reviewer instance to be monkey-patched
        :param _old: original Reviewer.revHtml
        :return: reviewer HTML code
        """
        return _old(reviewer) + self._injection()
