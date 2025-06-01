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

import html
import json
import re
import urllib.parse
from typing import TYPE_CHECKING, Any, Dict, List, NamedTuple, Optional

from .debug import DebugService
from .graphql import GraphQLClientException, GraphQLNetworkException
from .network import RateLimit
from .notification import NotificationService
from .phrases import (
    Media,
    Phrase,
    PhraseGroup,
    PhraseGroupResolver,
    PhraseRepository,
)
from .profile import ProfileAdapter
from .shared import _
from .user import ArticleAccessTarget, UserService

if TYPE_CHECKING:
    from aqt.reviewer import Reviewer


class Destination(NamedTuple):
    article_parts: List[str]
    article_id: str
    anchor_id: Optional[str]
    public_url: Optional[str]


class Tooltip(NamedTuple):
    hit: str
    guid: Optional[str]
    title: str
    synonyms: List[str]
    abstract: Optional[str]
    translation: Optional[str]
    destinations: List[Destination]
    media: List[Media]
    client_notification: Optional[str]
    server_notification: Optional[str]
    rate_limit: Optional[RateLimit] = None


class TooltipRenderResult(NamedTuple):
    phrase_group_id: str
    term: str
    html: str
    has_media: bool
    access_limit: bool
    rate_limit: Optional[RateLimit]


class TooltipDestinationLabelFactory:
    """Generates Tooltip.destination labels for Phrase objects."""

    def create(self, article_parts: List[str]) -> str:
        return " → ".join(article_parts)


class TooltipQueryFactory:
    def __init__(self, profile: ProfileAdapter):
        self._profile = profile

    def query_parts(self, hit: Optional[str], guid: Optional[str]) -> Dict[str, str]:
        return {
            "utm_source": "anki",
            "utm_medium": "anki",
            "utm_campaign": "anki",
            "utm_term": urllib.parse.quote_plus(hit.lower()) if hit else "",
            "guid": urllib.parse.quote(guid) if guid else "",
            "aid": self._profile.anon_id,
            "uid": self._profile.id if self._profile.id else "",
        }


class TooltipURLService:
    def __init__(self, tooltip_query_factory: TooltipQueryFactory):
        self._tooltip_query_factory = tooltip_query_factory

    def url_with_query(
        self, url: str, hit: Optional[str] = None, guid: Optional[str] = None
    ) -> str:
        # TODO: Refactor to use url.url_with_query instead
        urlobj = urllib.parse.urlparse(url)
        return urllib.parse.urlunparse(
            urlobj._replace(
                query=urllib.parse.urlencode(
                    {
                        **dict(urllib.parse.parse_qsl(urlobj.query)),
                        **self._tooltip_query_factory.query_parts(hit, guid),
                    }
                )
            )
        )


class PhraseTooltipMapper:
    @staticmethod
    def map(
        phrase: Phrase,
        found_term: str,
        guid: Optional[str],
        server_notification: Optional[str],
    ) -> Tooltip:
        return Tooltip(
            hit=found_term,
            guid=guid,
            title=phrase.title,
            synonyms=[],
            abstract=None,
            translation=None,
            destinations=[
                Destination(
                    article_parts=[
                        p for p in [phrase.article_title, phrase.section_title] if p
                    ],
                    article_id=phrase.article_id,
                    anchor_id=phrase.anchor_id,
                    public_url=phrase.public_url,
                )
            ]
            if phrase.article_title and phrase.article_id
            else [],
            media=[],
            client_notification=None,
            server_notification=server_notification,
        )


class PhraseGroupTooltipMapper:
    def __init__(
        self,
        tooltip_url_service: TooltipURLService,
        store_uri: str,
        register_uri: str,
        user_service: UserService,
    ):
        self._tooltip_url_service = tooltip_url_service
        self._store_uri = store_uri
        self._register_uri = register_uri
        self._user_service = user_service

    def map(
        self,
        phrase_group: PhraseGroup,
        found_term: str,
        guid: Optional[str],
        server_notification: Optional[str],
    ) -> Tooltip:
        return Tooltip(
            hit=found_term,
            guid=guid,
            title=phrase_group.title,
            synonyms=phrase_group.synonyms,
            abstract=phrase_group.abstract,
            translation=phrase_group.translation,
            destinations=[
                Destination(
                    article_parts=[destination.label],
                    article_id=destination.article_id,
                    anchor_id=destination.anchor,
                    public_url=destination.public_url,
                )
                for destination in phrase_group.destinations
            ],
            media=phrase_group.media,
            client_notification=self._access_notification(
                phrase_group, found_term, guid
            ),
            server_notification=server_notification,
            rate_limit=phrase_group.rate_limit,
        )

    def _access_notification(
        self, phrase_group: PhraseGroup, found_term: str, guid: Optional[str]
    ) -> Optional[str]:
        if not phrase_group.access_limit:
            return None
        if self._user_service.is_logged_in():
            header = _("Your access to AMBOSS has expired.")
            message = _("Choose the membership that's right for you in our shop.")
            url = self._tooltip_url_service.url_with_query(
                self._store_uri, found_term, guid
            )
            link = f"""\
                <a href='{url}' class="amboss-shop-link">
                  {message}
                </a>"""
            data_e2e_test_id = "message-access-expired"
        else:
            header = _("Your trial AMBOSS add-on access has expired.")
            message = _(
                "Create a free AMBOSS account to continue using the add-on, explore our"
                " Library and Qbank."
            )
            pycmd_arg = f"amboss:reviewer:url:{self._register_uri}"
            link = f"""\
                <a
                  href=# onclick='return pycmd({json.dumps(pycmd_arg)});'
                  class="amboss-register-link"
                  data_e2e_test_id="action-register"
                >
                  {message}
                </a>"""
            data_e2e_test_id = "message-trial-expired"
        return f"""\
            <div class="amboss-card-client-notification-error amboss-card-client-notification-access-expired" data-e2e-test-id="{data_e2e_test_id}">
              <p class="amboss-card-client-notification-access-expired-header">
                {header}
              </p>
              <p>
                {link}
              </p>
            </div>
            """


class TooltipFactory:
    """Creates a Tooltip object based on Phrase, PhraseGroup and other (user) criteria."""

    # TODO: make this more intelligent and prepare to show notifications based on (user) criteria
    def __init__(
        self,
        phrase_mapper: PhraseTooltipMapper,
        phrase_group_mapper: PhraseGroupTooltipMapper,
    ):
        self._phrase_mapper = phrase_mapper
        self._phrase_group_mapper = phrase_group_mapper

    def create_from_phrase_group(
        self,
        phrase_group: PhraseGroup,
        found_term: str,
        guid: Optional[str],
        server_notification: Optional[str],
    ) -> Tooltip:
        return self._phrase_group_mapper.map(
            phrase_group, found_term, guid, server_notification
        )

    def create_from_phrase(
        self,
        phrase: Phrase,
        found_term: str,
        guid: Optional[str],
        server_notification: Optional[str],
    ) -> Tooltip:
        return self._phrase_mapper.map(phrase, found_term, guid, server_notification)

    def create_from_client_notification(
        self,
        client_notification: str,
        found_term: str,
        guid: Optional[str],
        server_notification: Optional[str],
    ) -> Tooltip:
        return Tooltip(
            hit=found_term,
            guid=guid,
            title="",
            synonyms=[],
            abstract=None,
            translation=None,
            destinations=[],
            media=[],
            client_notification=client_notification,
            server_notification=server_notification,
        )


class TooltipService:
    def __init__(
        self,
        phrase_repository: PhraseRepository,
        phrase_group_resolver: PhraseGroupResolver,
        factory: TooltipFactory,
        notification_service: NotificationService,
    ):
        self._phrase_repository = phrase_repository
        self._phrase_group_resolver = phrase_group_resolver
        self._factory = factory
        self._notification_service = notification_service

    def get_tooltip(
        self, phrase_group_id: str, found_term: str, guid: Optional[str]
    ) -> Tooltip:
        phrase = self._phrase_repository.get_phrase_by_id(phrase_group_id)
        server_notification = self._notification_service.tooltip_notification()
        if not phrase:
            return self._factory.create_from_client_notification(
                _("Phrase not found."), found_term, guid, server_notification
            )
        try:
            phrase_group = self._phrase_group_resolver.resolve(phrase)
        except GraphQLClientException:
            header = _("Oops, something went wrong!")
            prelude = _(
                "Try restarting Anki to continue using the platform. If the problem"
                " persists, please"
            )
            action = _("contact customer support.")
            url = _("https://www.amboss.com/us/contact")
            return self._factory.create_from_client_notification(
                f"""\
                <div class="amboss-card-client-notification-error">
                  {header}
                  <br><br>
                  {prelude}
                  <a href="{url}?utm_source=anki&utm_medium=anki_error&utm_campaign=anki">
                    {action}
                  </a>
                </div>
                """,
                found_term,
                guid,
                server_notification,
            )
        except GraphQLNetworkException:
            return self._factory.create_from_client_notification(
                _("Can't connect to AMBOSS."), found_term, guid, server_notification
            )
        except Exception as e:
            # re-raise unexpected exception
            raise e
        if not phrase_group:
            return self._factory.create_from_phrase(
                phrase, found_term, guid, server_notification
            )
        return self._factory.create_from_phrase_group(
            phrase_group, found_term, guid, server_notification
        )


class TooltipRenderer:
    """Renders a Tooltip object into HTML."""

    def __init__(
        self,
        destination_label_factory: TooltipDestinationLabelFactory,
        debug_service: DebugService,
        user_service: UserService,
        library_uri: str,
        feedback_uri: str,
        amboss_dashboard_uri: str,
        media_viewer_with_access_url_template: str,
        media_viewer_without_access_url_template: str,
        tooltip_url_service: TooltipURLService,
        addon_module: str,
    ):
        self._destination_label_factory = destination_label_factory
        self._debug_service = debug_service
        self._user_service = user_service
        self._library_uri = library_uri
        self._feedback_uri = feedback_uri
        self._amboss_dashboard_uri = amboss_dashboard_uri
        self._media_viewer_with_access_url_template = (
            media_viewer_with_access_url_template
        )
        self._media_viewer_without_access_url_template = (
            media_viewer_without_access_url_template
        )
        self._tooltip_url_service = tooltip_url_service
        self._addon_module = addon_module

    def render(self, tooltip: Tooltip) -> str:
        tooltip_props = {
            "serverNotification": tooltip.server_notification,
            "title": tooltip.title,
            "synonyms": tooltip.synonyms,
            "translation": tooltip.translation,
            "media": self.combine_media(tooltip),
            "mainImageCaption": _("Click image to open enlarged view"),
            "clientNotification": tooltip.client_notification,
            "abstract": tooltip.abstract,
            "destinations": self.combine_destinations(tooltip),
            "bottomBarAmbossLink": self._tooltip_url_service.url_with_query(
                self._amboss_dashboard_uri, tooltip.hit, tooltip.guid
            ),
            "bottomBarHelpLink": self._tooltip_url_service.url_with_query(
                self._feedback_uri, tooltip.hit, tooltip.guid
            ),
            "feedbackText": _("Feedback"),
            "footerImgUrl": f"/_addons/{self._addon_module}/web/media/logo_day.svg",
        }

        return f"""<amboss-tooltip-content props="{html.escape(json.dumps(tooltip_props))}" data-e2e-test-id="amboss-tooltip-content" />"""

    def combine_media(self, tooltip: Tooltip) -> List[Dict[str, Any]]:
        return [
            mm for mm in [self.create_media(m, tooltip) for m in tooltip.media] if mm
        ]

    def create_media(self, media: Media, tooltip: Tooltip) -> Dict[str, Any]:
        return {
            "url_with_access": self._tooltip_url_service.url_with_query(
                self._media_viewer_with_access_url_template.format(
                    phrase_title=urllib.parse.quote(tooltip.title, ""),
                    media_id=media.id,
                ),
                tooltip.hit,
                tooltip.guid,
            ),
            "url_without_access": self._tooltip_url_service.url_with_query(
                self._media_viewer_without_access_url_template.format(
                    media_id=media.id,
                ),
                tooltip.hit,
                tooltip.guid,
            ),
            "media_url": media.url,
            "media_copyright": re.sub('target="[^"]+"', "", media.copyright)
            if media.copyright
            else "",
            "id": media.id,
        }

    def combine_destinations(self, tooltip: Tooltip):
        return [
            dd
            for dd in [
                self.create_destinations(d, tooltip.hit, tooltip.guid)
                for d in tooltip.destinations
            ]
            if dd
        ]

    def create_destinations(
        self, destination: Destination, hit: str, guid: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        if (
            self._user_service.article_access_target
            == ArticleAccessTarget.platform_article
        ):
            dest_url = self._tooltip_url_service.url_with_query(
                f"{self._library_uri}/{destination.article_id}"
                f"{('#' + destination.anchor_id) if destination.anchor_id else ''}",
                hit,
                guid,
            )
        elif (
            destination.public_url
            and self._user_service.article_access_target
            == ArticleAccessTarget.public_article
        ):
            dest_url = self._tooltip_url_service.url_with_query(
                destination.public_url, hit, guid
            )
        else:
            return None

        dest = {
            "pycmdUrl": dest_url,
            "phraseTerm": urllib.parse.quote_plus(hit.lower()) if hit else "",
            "anchorId": urllib.parse.quote_plus(destination.anchor_id)
            if destination.anchor_id
            else "",
            "articleId": urllib.parse.quote_plus(destination.article_id),
            "articleAccessTargetType": self._user_service.article_access_target.value,
            "cardGuid": urllib.parse.quote_plus(guid) if guid else "",
            "destinationText": self._destination_label_factory.create(
                destination.article_parts
            ),
        }
        return dest


class TooltipRenderService:
    def __init__(
        self, service: TooltipService, renderer: TooltipRenderer, reviewer: "Reviewer"
    ):
        self._service = service
        self._renderer = renderer
        self._reviewer = reviewer

    def render_tooltip(
        self, phrase_group_id: str, found_term: str
    ) -> TooltipRenderResult:
        tooltip = self._service.get_tooltip(
            phrase_group_id,
            found_term,
            self._reviewer.card.note().guid if self._reviewer.card else None,
        )
        html = self._renderer.render(tooltip)
        return TooltipRenderResult(
            phrase_group_id=phrase_group_id,
            term=found_term,
            html=html,
            has_media=bool(tooltip.media),
            access_limit="amboss-card-client-notification-access-expired"
            in html,  # TODO: improve
            rate_limit=tooltip.rate_limit,
        )
