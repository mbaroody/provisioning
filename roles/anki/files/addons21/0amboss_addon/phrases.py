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
from functools import lru_cache
from typing import Dict, List, NamedTuple, Optional, Tuple

from urllib3.exceptions import HTTPError, HTTPWarning

from .graphql import (
    GraphQLException,
    GraphQLQueryResolver,
    GraphQLQueryResponse,
)
from .hooks import (
    amboss_did_access_change,
    amboss_did_login,
    amboss_did_logout,
)
from .network import HTTPClientFactory, RateLimit, TokenAuth
from .profile import ProfileAdapter


class Phrase(NamedTuple):
    title: str
    group_id: str
    anchor_id: Optional[str]
    article_id: Optional[str]
    article_title: Optional[str]
    public_url: Optional[str]
    section_title: Optional[str]


class Destination(NamedTuple):
    label: str
    article_id: str
    anchor: Optional[str]
    public_url: Optional[str]


class Media(NamedTuple):
    id: str
    url: str
    copyright: str
    aspect_ratio: float


class PhraseGroup(NamedTuple):
    title: str
    id: str
    synonyms: List[str]
    abstract: Optional[str]
    translation: Optional[str]
    destinations: List[Destination]
    media: List[Media]
    access_limit: bool
    rate_limit: Optional[RateLimit]


phrase_group_operation_name = "AnkiPhraseGroup"


def phrase_group_query(eid: str):
    return f"""\
    query {phrase_group_operation_name} {{
      phraseGroup(eid: "{eid}") {{
        eid
        title
        synonyms
        abstract
        translation
        destinations {{
          label
          articleEid
          anchor
          publicUrl
        }}
        media {{
          eid
          title
          canonicalUrl
          aspectRatio
          copyright {{
            html
          }}
        }}
      }}
    }}"""


class PhraseMapper:
    """Maps result dict of phrase metadata to namedtuple Phrase object."""

    @staticmethod
    def map(d: dict) -> Phrase:
        return Phrase(
            title=d.get("phrase_title"),  # type: ignore[arg-type]
            group_id=d.get("pg_id"),  # type: ignore[arg-type]
            anchor_id=d.get("ankerlink_id"),
            article_id=d.get("lc_id"),
            article_title=d.get("lc_title"),
            section_title=d.get("ls_title"),
            public_url=d.get("public_article_url"),
        )


class DestinationMapper:
    """Maps GraphQL SememeDestination JSON to namedtuple Destination object."""

    @staticmethod
    def map(d: dict) -> Destination:
        return Destination(
            label=d.get("label"),  # type: ignore[arg-type]
            article_id=d.get("articleEid"),  # type: ignore[arg-type]
            anchor=d.get("anchor"),
            public_url=d.get("publicUrl"),
        )


class MediaMapper:
    """Maps GraphQL MediaAsset JSON to namedtuple Media object."""

    @staticmethod
    def map(d: dict) -> Media:
        return Media(
            id=d.get("eid"),  # type: ignore[arg-type]
            url=d.get("canonicalUrl"),  # type: ignore[arg-type]
            copyright=d.get("copyright", {}).get("html"),  # type: ignore[arg-type]
            aspect_ratio=d.get("aspectRatio"),  # type: ignore[arg-type]
        )


class PhraseGroupMapper:
    """Maps GraphQL PhraseGroup JSON to namedtuple PhraseGroup object."""

    def __init__(
        self, destination_mapper: DestinationMapper, media_mapper: MediaMapper
    ):
        self._dest_mapper = destination_mapper
        self._media_mapper = media_mapper

    def map(self, phrase_group_response: GraphQLQueryResponse) -> Optional[PhraseGroup]:
        phrase_group_data = phrase_group_response.data.get("data", {}).get(
            "phraseGroup"
        )
        if not phrase_group_data:
            return None
        media_data = phrase_group_data.get("media", []) or []
        media: List[dict] = [
            media_asset for media_asset in media_data if isinstance(media_asset, dict)
        ]
        return PhraseGroup(
            title=phrase_group_data.get("title"),
            id=phrase_group_data.get("eid"),
            synonyms=phrase_group_data.get("synonyms", []),
            abstract=phrase_group_data.get("abstract"),
            translation=phrase_group_data.get("translation"),
            destinations=[
                self._dest_mapper.map(dest)
                for dest in phrase_group_data.get("destinations", [])
            ],
            media=[self._media_mapper.map(media_asset) for media_asset in media],
            access_limit=self._is_access_limited(phrase_group_response.data),
            rate_limit=(
                phrase_group_response.meta.rate_limit
                if phrase_group_response.meta
                else None
            ),
        )

    @staticmethod
    def _is_access_limited(d: dict) -> bool:
        errors = d.get("errors", [{}])
        for error in errors:
            if error.get("message") == "permission.user_is_not_authorized":
                return True
            path = error.get("path", [None])
            if isinstance(path, list) and path[-1] == "abstract":
                return True
        return False


class PhraseFinderHTTPClient:
    """Client for fetching phrase metadata of list of Anki notes from REST endpoint."""

    def __init__(
        self, uri: str, token_auth: TokenAuth, http_client_factory: HTTPClientFactory
    ):
        self._token_auth = token_auth
        self._client = http_client_factory.create(uri)

    def post(self, strings: Tuple[str, ...], guid: Optional[str]) -> dict:
        try:
            response = self._client.post(
                {"card_text_list": list(strings), "guid": guid},
                self._token_auth.get_header(),
            )
        except (HTTPError, HTTPWarning) as e:
            raise e
        try:
            return json.loads(response.data.decode("utf-8"))
        except ValueError:
            return {}


class PhraseFinderCacheClient:
    """Client for fetching phrase metadata and caching it."""

    def __init__(self, phrase_finder_https_client: PhraseFinderHTTPClient):
        self._phrase_finder_https_client = phrase_finder_https_client
        amboss_did_access_change.append(self.get_phrase_dict.cache_clear)
        amboss_did_login.append(self.get_phrase_dict.cache_clear)
        amboss_did_logout.append(self.get_phrase_dict.cache_clear)

    @lru_cache(maxsize=128)
    def get_phrase_dict(self, strings: Tuple[str, ...], guid: Optional[str]) -> dict:
        # TODO: cache individual phrases as well as tuples
        return self._phrase_finder_https_client.post(strings, guid)


class PhraseRepository:
    """Holds cache of found Phrase metadata objects based on phrase group ID."""

    # TODO: phrase group ID might not be a valid key, as multiple phrases can belong to the same group
    # TODO: REST API returns synonym, not main phrase, use that normalized + encoded as key instead
    _phrases_by_id: Dict[str, Phrase] = {}

    def get_phrase_by_id(self, phrase_group_id: str):
        return self._phrases_by_id.get(phrase_group_id, None)

    def store(self, phrase: Phrase):
        self._phrases_by_id[phrase.group_id] = phrase


class PhraseFinder:
    """
    Finds matching phrases and their phrase group IDs in Anki note fields.
    Stores the found phrases in PhraseRepository.
    """

    def __init__(
        self,
        client: PhraseFinderCacheClient,
        repository: PhraseRepository,
        mapper: PhraseMapper,
    ):
        self._client = client
        self._repository = repository
        self._mapper = mapper
        amboss_did_access_change.append(self.get_phrases.cache_clear)
        amboss_did_login.append(self.get_phrases.cache_clear)
        amboss_did_logout.append(self.get_phrases.cache_clear)

    @lru_cache(maxsize=128)
    def get_phrases(
        self, strings: Tuple[str], guid: Optional[str]
    ) -> Dict[str, Phrase]:
        response = self._client.get_phrase_dict(strings, guid)
        if "results" not in response or len(response) == 0:
            return {}
        phrases = {}
        for result in response["results"]:
            phrase = self._mapper.map(result)
            phrases[result["term"]] = phrase
            self._repository.store(phrase)
        return phrases


class PhraseGroupClient:
    def __init__(self, query_resolver: GraphQLQueryResolver, profile: ProfileAdapter):
        self._query_resolver = query_resolver
        self._profile = profile

    def phrase_group_response(self, phrase_id: str) -> GraphQLQueryResponse:
        """
        :raises GraphQLException
        """
        return self._query_resolver.resolve(
            phrase_group_query(phrase_id), phrase_group_operation_name
        )


class PhraseGroupResolver:
    def __init__(
        self,
        phrase_group_client: PhraseGroupClient,
        phrase_group_mapper: PhraseGroupMapper,
    ):
        self._phrase_group_client = phrase_group_client
        self._phrase_group_mapper = phrase_group_mapper

        amboss_did_access_change.append(self.resolve.cache_clear)
        amboss_did_login.append(self.resolve.cache_clear)
        amboss_did_logout.append(self.resolve.cache_clear)

    @lru_cache(maxsize=64)
    def resolve(self, phrase: Phrase) -> Optional[PhraseGroup]:
        """
        Resolves phrase group ID to PhraseGroup objects with metadata such as abstract, destinations and notifications.
        Using LRU cache because it's changing only very slowly and more dynamic properties are compiled on-the-fly.

        :raises GraphQLException
        """
        try:
            return self._phrase_group_mapper.map(
                self._phrase_group_client.phrase_group_response(phrase.group_id)
            )
        except GraphQLException as e:
            raise e
