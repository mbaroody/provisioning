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


from typing import Deque
from urllib.parse import quote

from aqt.utils import openLink

from .config import AddonConfig, DisplaySettingName
from .sidepanel import SidePanelController
from .user import ArticleAccessTarget, UserService


class ExternalLinkHandler:
    def __init__(
        self,
        addon_config: AddonConfig,
        side_panel_controller: SidePanelController,
        history: Deque[str],
    ):
        self._addon_config = addon_config
        self._side_panel_controller = side_panel_controller
        self._history = history

    def open_url(self, url: str) -> None:
        self._history.clear()
        if self.is_article_viewer_internal():
            self._side_panel_controller.show_url(url)
        else:
            openLink(url)

    def is_article_viewer_internal(self) -> bool:
        return self._addon_config[DisplaySettingName.ENABLE_ARTICLE_VIEWER.value]


class MediaLinkHandler:
    def __init__(
        self,
        external_link_handler: ExternalLinkHandler,
        side_panel_controller: SidePanelController,
        user_service: UserService,
        media_wall_url: str,
        history: Deque[str],
    ):
        self._external_link_handler = external_link_handler
        self._side_panel_controller = side_panel_controller
        self._user_service = user_service
        self._media_wall_url = media_wall_url
        self._history = history

    def open_media(
        self,
        url_with_access: str,
        url_without_access: str,
        media_url: str,
        media_copyright: str,
    ) -> None:
        if (
            self._user_service.article_access_target
            == ArticleAccessTarget.platform_article
        ):
            self._external_link_handler.open_url(url_with_access)
        elif self._user_service.is_logged_in(cached=True):
            self._external_link_handler.open_url(url_without_access)
        else:
            self._history.append(url_without_access)
            self._side_panel_controller.show_url(
                f"{self._media_wall_url}&mediaUrl={quote(media_url)}&mediaCopyright={quote(media_copyright)}"
            )
