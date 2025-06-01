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

import json
from typing import Dict, NamedTuple, Optional

from urllib3.exceptions import RequestError, TimeoutError

from ..network import HTTPClientFactory
from ..network import TokenAuth as LongTermTokenAuth
from ..profile import ProfileAdapter
from .jwt import extract_jwt_claims
from .service_time import TimeService


class TokenData(NamedTuple):
    token: str
    expiration_time: int
    issued_at_time: int


class TokenError(Exception):
    def __init__(self, msg="Could not get token data", *args, **kwargs):
        super().__init__(msg, *args, **kwargs)


class TokenExpirationError(TokenError):
    pass


class TokenTimeoutError(TokenError):
    pass


class TokenAuthorizationError(TokenError):
    pass


class TokenFetcherHTTPClient:
    def __init__(
        self,
        url: str,
        long_term_token_auth: LongTermTokenAuth,
        http_client_factory: HTTPClientFactory,
    ):
        self._long_term_token_auth = long_term_token_auth
        self._http_client = http_client_factory.create(url)

    def post(self) -> Dict[str, str]:
        try:
            response = self._http_client.post(
                headers=self._long_term_token_auth.get_header(), timeout=5
            )
        except TimeoutError as e:
            raise TokenTimeoutError(str(e)) from e
        except RequestError as e:
            raise TokenError(str(e)) from e
        if 400 <= response.status < 500:
            raise TokenAuthorizationError(f"HTTP status code {response.status}")
        try:
            return json.loads(response.data.decode("utf-8"))
        except ValueError as e:
            raise TokenError(str(e)) from e


class TokenFetcher:
    def __init__(self, http_client: TokenFetcherHTTPClient):
        self._http_client = http_client

    def fetch_token(self) -> TokenData:
        result = self._http_client.post()

        access_token = result.get("access_token")
        if access_token is None:
            raise TokenError("Malformed response: Missing `access_token` field")

        jwt_claims = extract_jwt_claims(token=access_token)

        return TokenData(
            token=access_token,
            expiration_time=jwt_claims.exp,
            issued_at_time=jwt_claims.iat,
        )


class TokenService:
    def __init__(self, token_fetcher: TokenFetcher, profile_adapter: ProfileAdapter):
        self._token_fetcher = token_fetcher
        self._profile_adapter = profile_adapter

    def fetch_token(self) -> TokenData:
        token_data = self._token_fetcher.fetch_token()
        self._set_cached_token(token_data=token_data)
        return token_data

    def get_cached_token(self) -> Optional[TokenData]:
        token_dict = self._profile_adapter.mobile_token_dict
        if token_dict is None:
            return None
        if "issued_at_time" not in token_dict:
            try:  # update legacy tokens cached before 09/2022
                jwt_claims = extract_jwt_claims(token_dict.get("token", ""))
                issued_at_time = int(jwt_claims.iat)
            except Exception:
                issued_at_time = int(TimeService.time())
            token_dict["issued_at_time"] = issued_at_time
        return TokenData(**token_dict)

    def _set_cached_token(self, token_data: TokenData):
        self._profile_adapter.mobile_token_dict = token_data._asdict()


class TokenRefreshService:
    def __init__(
        self,
        token_service: TokenService,
        time_service: TimeService,
        refresh_token_at_fraction_left: float = 0.5,
    ):
        self._time_service = time_service
        self._token_service = token_service
        self._refresh_token_at_fraction_left = refresh_token_at_fraction_left

    def get_token(self) -> TokenData:
        cached_token = self._token_service.get_cached_token()

        if not cached_token:
            return self._token_service.fetch_token()

        token_lifetime_fraction_left = calc_token_lifetime_fraction_left(
            self._time_service, cached_token
        )
        if token_lifetime_fraction_left > self._refresh_token_at_fraction_left:
            return cached_token

        try:
            token = self._token_service.fetch_token()
        except TokenError as e:
            if self._time_service.days_until(cached_token.expiration_time) > 0:
                # fall back on cached until expired
                return cached_token
            raise TokenExpirationError from e
        return token


def calc_token_lifetime_fraction_left(
    time_service: TimeService, token_data: TokenData
) -> float:
    days_until_expiry = time_service.days_until(token_data.expiration_time)
    if days_until_expiry < 1:
        return 0
    days_since_issued = -time_service.days_until(token_data.issued_at_time)
    days_lifetime = days_until_expiry + days_since_issued
    if days_lifetime < 1:  # token issued past expiry
        return 0
    return days_until_expiry / days_lifetime
