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


"""
Everything to do with the side panel web view
"""

from typing import TYPE_CHECKING, Callable, Dict, NamedTuple, Optional

from aqt.qt import (
    QObject,
    QUrl,
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineSettings,
    pyqtSignal,
)
from aqt.utils import openLink
from packaging import version

from .user import UserService
from .web import WebPage

if TYPE_CHECKING:
    from aqt.main import AnkiQt


class RedirectionResult(NamedTuple):
    fragment: str
    redirected_to: Optional[str]


class SidePanelURLRedirector:
    """Maps URLs containing string fragments to different URLs

    :param anon_redirects: Dictionary mapping URL string fragment to the URL to redirect
                           to, for anonymous users. The redirect URL may be set to None to
                           block loading sites containing the string fragment entirely.
    :param user_redirects: Same as above, but for authenticated users.
    """

    def __init__(
        self,
        user_service: UserService,
        anon_redirects: Dict[str, Optional[str]],
        user_redirects: Dict[str, Optional[str]],
    ):
        self._user_service = user_service
        self._anon_redirects = anon_redirects
        self._user_redirects = user_redirects

    def maybe_redirect(self, url: str) -> Optional[RedirectionResult]:
        redirects = (
            self._user_redirects
            if self._user_service.is_logged_in()
            else self._anon_redirects
        )
        for fragment, redirected_to in redirects.items():
            if fragment in url:
                return RedirectionResult(fragment=fragment, redirected_to=redirected_to)
        return None


class ConditionallyExternallyOpeningWebPage(QWebEnginePage):
    """
    Self-deleting QWebEnginePage that selectively opens links in system-default
    web browser
    """

    def __init__(
        self,
        url_redirector: SidePanelURLRedirector,
        web_profile: QWebEngineProfile,
        parent: "SidePanelWebPage",
    ) -> None:
        super().__init__(web_profile, parent)
        self._url_redirector = url_redirector

    def acceptNavigationRequest(
        self, url: QUrl, type: QWebEnginePage.NavigationType, isMainFrame: bool
    ) -> bool:

        redirection_result = self._url_redirector.maybe_redirect(url.toString())

        if redirection_result is not None:
            self.parent().setUrl(url)
        else:
            openLink(url.toString())

        self.deleteLater()

        return False

    def parent(self) -> "SidePanelWebPage":
        return super().parent()  # type: ignore[return-value]


class SidePanelWebPage(WebPage):

    """
    Modified version of AnkiWebPage with support for custom web engine profiles.

    Opens all links inside the view safe for ones explicitly requesting
    a new tab / new window. These are passed on to the system-default handler.
    """

    url_redirected = pyqtSignal(str, str)

    def __init__(
        self,
        web_profile: QWebEngineProfile,
        url_redirector: SidePanelURLRedirector,
        main_window: "AnkiQt",
        anki_version: Optional[str] = None,
        on_bridge_cmd: Optional[Callable] = None,
        parent: Optional[QObject] = None,
    ):
        QWebEnginePage.__init__(self, web_profile, parent)

        # Web profile needs to exist until web page destroyed, so bind it to the web
        # page as its child:
        web_profile.setParent(self)

        # required for opening external links:
        self.settings().setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True
        )

        self.setBridgeCommand(on_bridge_cmd)

        self._url_redirector = url_redirector
        self._main_window = main_window
        self._anki_version = version.parse(anki_version) if anki_version else None

        # AnkiWebPage.__init__

        # NOTE: We take over initializing the superclass manually here. This is not
        # a good practice, but the only way to use a custom web profile without
        # running into order-of-destruction issues with Qt.

        # FIXME: By taking these steps over, we add a hard dependency on AnkiWebPage
        # implementation details. This means that we have to keep our code in sync
        # with future changes to AnkiWebPage, while also maintaining backwards
        # compatibility with earlier versions of the class. This does not seem
        # tenable in the long term.

        self._onBridgeCmd = self._wrapped_bridge_command
        self._setupBridge()
        self.open_links_externally = True

    def acceptNavigationRequest(self, qurl: QUrl, nav_type, is_main_frame) -> bool:
        url = qurl.toString()
        if "localhost" in url:
            return True

        redirection_result = self._url_redirector.maybe_redirect(url)

        if redirection_result is None:
            return True
        elif redirection_result.redirected_to is None:
            return False

        self.setUrl(QUrl(redirection_result.redirected_to))

        self.url_redirected.emit(
            redirection_result.fragment, redirection_result.redirected_to
        )

        # On some older versions of Anki, a Qt bug breaks web view focus and prevents typing.
        # We therefore give up trying to focus on the sidebar web view and let the user click on input.
        if not self._anki_version or self._anki_version < version.parse("2.1.29"):
            self._main_window.web.setFocus()

        return False

    def createWindow(self, type: QWebEnginePage.WebWindowType) -> QWebEnginePage:
        """Handle links opened in new tab/window"""
        return ConditionallyExternallyOpeningWebPage(
            url_redirector=self._url_redirector, web_profile=self.profile(), parent=self
        )
