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
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    FrozenSet,
    NamedTuple,
    Optional,
    Union,
)
from urllib.parse import urlencode

import certifi
from urllib3 import (
    HTTPConnectionPool,
    HTTPResponse,
    Retry,
    connection_from_url,
)
from urllib3.exceptions import MaxRetryError, SSLError, TimeoutError

from .activity import ActivityCookieService

if TYPE_CHECKING:
    from urllib3._collections import HTTPHeaderDict


TIMEOUT_ERRORS = (TimeoutError, MaxRetryError, SSLError)


class RateLimit(NamedTuple):
    limit: Optional[int]
    remaining: int
    reset: Optional[int]


class TokenAuth:
    """
    Stateful object that holds token and basic auth credentials with authorization header representation.
    TODO: Remove once circular dependencies have been resolved.
    """

    def __init__(self, token: Optional[str] = None):
        assert token is None or isinstance(token, str)
        self._token = token

    def get_header(self) -> Optional[dict]:
        return {"Authorization": f"Bearer {self._token}"} if self._token else None

    def set_token(self, token: Optional[str]) -> None:
        self._token = token

    def __bool__(self) -> bool:
        return self._token is not None


class MIMEType(Enum):
    form = "application/x-www-form-urlencoded"
    json = "application/json"


class MIMEMapper:
    @staticmethod
    def body(
        data: Optional[dict], mime_type: Optional[MIMEType]
    ) -> Union[None, str, bytes, dict]:
        if not data:
            return None
        elif mime_type == MIMEType.json:
            return json.dumps(data).encode("utf-8")
        elif mime_type == MIMEType.form:
            return urlencode(data)
        else:
            return data

    @staticmethod
    def header(mime_type: Optional[MIMEType]) -> Dict[str, str]:
        return {"Content-Type": mime_type.value} if mime_type else {}


class HTTPClient:
    def __init__(
        self,
        uri: str,
        pool: HTTPConnectionPool,
        headers: Dict[str, str],
        cookie_service: ActivityCookieService,
    ):
        self._uri = uri
        self._pool = pool
        self._headers = headers
        self._cookie_service = cookie_service

    def post(
        self,
        data: Optional[dict] = None,
        headers: Optional[Dict[str, str]] = None,
        mime_type: Optional[MIMEType] = MIMEType.json,
        timeout: Optional[int] = None,
    ) -> HTTPResponse:
        return self._pool.request(
            "POST",
            self._uri,
            body=MIMEMapper.body(data, mime_type),
            headers=dict(
                d
                for h in [
                    hh
                    for hh in [
                        headers,
                        self._headers,
                        self._cookie_service.cookie_header(),
                        MIMEMapper.header(mime_type),
                    ]
                    if hh
                ]
                for d in h.items()
            ),
            **{"timeout": timeout} if timeout else {},
        )


class HTTPConnectionPoolFactory:
    def __init__(
        self,
        *,
        timeout: int,
        retries: Optional[int] = 2,
        retry_statuses: FrozenSet[int] = frozenset([413, 429, 503]),
        retry_methods: FrozenSet[str] = frozenset(
            ["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"]
        ),
        maxsize: int = 1,
        block: object = False,
    ):
        """
        Connection pool with retry configuration:

        :param retries:
            Total number of retries to allow.
            Set to `None` to disable retries.
            Set to `0` to fail on the first retry.
            Connections will only raise `MaxRetryError` if set and retries exceeded.

        :param retry_statuses:
            A set of integer HTTP status codes that we should force a retry on.
            A retry is initiated if the request method is in `retry_methods`
            and the response status code is in `retry_statuses`.
            See :attr:`urllib3.util.retry.Retry.RETRY_AFTER_STATUS_CODES`.

        :param retry_methods:
            Set of uppercased HTTP method verbs that we should retry on.
            By default, we retry on methods which are considered to be
            idempotent.
            See :attr:`urllib3.util.retry.Retry.DEFAULT_ALLOWED_METHODS`.
        """
        self._timeout = timeout
        self._retry_count = retries
        self._retry_methods = retry_methods
        self._retry_statuses = retry_statuses
        self._maxsize = maxsize
        self._block = block
        self._ca_certs = certifi.where()

    def create(self, uri: str) -> HTTPConnectionPool:
        kw: Dict[str, Any] = {
            "timeout": self._timeout,
            "maxsize": self._maxsize,
            "block": self._block,
        }
        if uri.startswith("https"):
            kw["ca_certs"] = kw.get("ca_certs", self._ca_certs)
        if self._retry_count is not None:
            try:
                kw["retries"] = Retry(
                    total=self._retry_count,
                    status_forcelist=self._retry_statuses,
                    allowed_methods=self._retry_methods,
                )
            except TypeError:
                kw["retries"] = Retry(
                    total=self._retry_count,
                    status_forcelist=self._retry_statuses,
                )
        return connection_from_url(uri, **kw)


class HTTPClientFactory:
    def __init__(
        self,
        connection_pool_factory: HTTPConnectionPoolFactory,
        user_agent: str,
        cookie_service: ActivityCookieService,
    ):
        self._connection_pool_factory = connection_pool_factory
        self._user_agent = user_agent
        self._cookie_service = cookie_service

    def create(self, uri: str, headers: Optional[Dict[str, str]] = None) -> HTTPClient:
        return HTTPClient(
            uri,
            self._connection_pool_factory.create(uri),
            {
                **{"User-Agent": self._user_agent},
                **(headers if headers else {}),
            },
            self._cookie_service,
        )


class RateLimitHeader(Enum):
    limit = "x-amboss-ratelimit-limit"
    remaining = "x-amboss-ratelimit-remaining"
    reset = "x-amboss-ratelimit-reset"


class RateLimitParser:
    @classmethod
    def parse(cls, headers: "HTTPHeaderDict") -> Optional[RateLimit]:
        try:
            return RateLimit(
                limit=cls._cast(headers, RateLimitHeader.limit),
                remaining=cls._cast(headers, RateLimitHeader.remaining) or -1,
                reset=cls._cast(headers, RateLimitHeader.reset),
            )
        except TypeError:
            return None

    @staticmethod
    def _cast(
        headers: "HTTPHeaderDict",
        header_key: RateLimitHeader,
    ) -> Optional[int]:
        """
        Tries to cast headers to Optional[int] if they're optional, int if they're not.
        HTTPHeaderDict may not contain ints and does not cast numerical values so we don't check for that.

        :raises TypeError: When mandatory header cannot be cast.
        """

        header = headers.get(header_key.value)
        if isinstance(header, str) and header.isnumeric():
            return int(header)
        if header_key == RateLimitHeader.remaining:
            raise TypeError(f"Cannot cast {header_key.value} from {header}")
        return None
