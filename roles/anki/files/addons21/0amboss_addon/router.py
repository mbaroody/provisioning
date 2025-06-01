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

import json
from abc import ABC, abstractmethod
from typing import Optional

from .anki.version import VersionCheckResult
from .auth import AuthDialog, LoginHandler, RegisterHandler
from .debug import ErrorPromptFactory
from .links import ExternalLinkHandler, MediaLinkHandler
from .profile import ProfileAdapter
from .reviewer import ReviewerTooltipUpdater
from .shared import _
from .sidepanel import SidePanelController


class Router(ABC):
    @abstractmethod
    def __call__(self, cmd: str, arg: Optional[str] = None):
        raise NotImplementedError


class ReviewerRouter(Router):
    """Handles hijacked AMBOSS specific Anki reviewer bridge links."""

    def __init__(
        self,
        reviewer_tooltip_updater: ReviewerTooltipUpdater,
        external_link_handler: ExternalLinkHandler,
        media_link_handler: MediaLinkHandler,
    ):
        self._reviewer_tooltip_updater = reviewer_tooltip_updater
        self._external_link_handler = external_link_handler
        self._media_link_handler = media_link_handler

    def __call__(self, cmd: str, arg: Optional[str] = None):
        if cmd == "tooltip":
            assert arg is not None
            payload = json.loads(arg)
            self._reviewer_tooltip_updater.update_tooltip(payload)
            return
        if cmd == "url":
            assert arg is not None
            self._external_link_handler.open_url(arg)
            return
        if cmd == "isArticleViewerInternal":
            return self._external_link_handler.is_article_viewer_internal()
        if cmd == "media":
            assert arg is not None
            payload = json.loads(arg)
            url_with_access, url_without_access, media_url, media_copyright = (
                payload["url_with_access"],
                payload["url_without_access"],
                payload["media_url"],
                payload["media_copyright"],
            )
            self._media_link_handler.open_media(
                url_with_access=url_with_access,
                url_without_access=url_without_access,
                media_url=media_url,
                media_copyright=media_copyright,
            )
            return


class AuthRouter(Router):
    """Handles all auth bridge links."""

    def __init__(
        self,
        login_handler: LoginHandler,
        auth_dialog: AuthDialog,
        register_handler: RegisterHandler,
    ):
        self._login_handler = login_handler
        self._auth_dialog = auth_dialog
        self._register_handler = register_handler

    def __call__(self, cmd: str, arg: Optional[str] = None):
        if cmd == "login":
            assert arg is not None
            try:
                payload = json.loads(arg)
                username, password = payload["username"], payload["password"]
            except Exception:
                return False
            return self._login_handler.login(username, password)
        if cmd == "register":
            assert arg is not None
            try:
                payload = json.loads(arg)
                username, password, password_again = (
                    payload["username"],
                    payload["password"],
                    payload["password_again"],
                )
            except Exception:
                return False
            return self._register_handler.register(username, password, password_again)
        if cmd == "close":
            self._auth_dialog.accept()
            return


class AboutRouter(Router):
    def __init__(self, error_prompt_factory: ErrorPromptFactory):
        self._error_prompt_factory = error_prompt_factory

    def __call__(self, cmd: str, arg: Optional[str] = None):
        if cmd == "debug":
            self._error_prompt_factory.create_and_exec(
                exception=None,
                message_heading=_("Something isn't working like you expected?"),
                window_title=_("AMBOSS - Debug"),
            )


class VersionRouter(Router):
    def __init__(self, version_check_result: VersionCheckResult, addon_version: str):
        self._version_check_result = version_check_result
        self._addon_version = addon_version

    def __call__(self, cmd: str, arg: Optional[str] = None):
        if cmd == "warning":
            if not self._version_check_result.satisfied:
                return self._version_check_result._asdict()
            return False
        if cmd == "addonVersion":
            return self._addon_version
        if cmd == "ankiVersion":
            return self._version_check_result.current


class ProfileRouter(Router):
    def __init__(self, profile: ProfileAdapter):
        self._profile = profile

    def __call__(self, cmd: str, arg: Optional[str] = None):
        if cmd == "anonId":
            return self._profile.anon_id
        if cmd == "userId":
            return self._profile.id


class SidePanelRouter(Router):
    def __init__(self, side_panel_controller: SidePanelController):
        self._side_panel_controller = side_panel_controller

    def __call__(self, cmd: str, arg: Optional[str] = None):
        if cmd == "toggle":
            self._side_panel_controller.toggle()
