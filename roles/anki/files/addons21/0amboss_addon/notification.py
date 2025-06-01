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
import time
from functools import lru_cache
from typing import Dict, NamedTuple, Optional

from urllib3.exceptions import HTTPError, HTTPWarning

from .hooks import (
    amboss_did_access_change,
    amboss_did_login,
    amboss_did_logout,
)
from .network import HTTPClientFactory, TokenAuth


class UpdateData(NamedTuple):
    version: str
    name: str
    url: str
    changelog: str
    bytes: Optional[int] = None
    sha1: Optional[str] = None

    def to_dict(self) -> Dict[str, Optional[str]]:
        return dict(self._asdict())

    @staticmethod
    def from_dict(d: Optional[Dict]) -> "UpdateData":
        """Maps dict to parsed UpdateData or None to default. Doesn't validate."""
        d = d if isinstance(d, dict) else {}
        return UpdateData(
            version=d.get("version", "0.0.1"),
            name=d.get("name", "0amboss"),
            url=d.get("url", ""),
            changelog=d.get("changelog", ""),
            bytes=d.get("bytes", None),
            sha1=d.get("sha1", None),
        )


class UpdateNotification(NamedTuple):
    min: UpdateData
    max: Optional[UpdateData] = None

    def to_dict(self) -> Dict[str, Optional[Dict[str, Optional[str]]]]:
        return {
            "min": self.min.to_dict(),
            "max": None if not self.max else self.max.to_dict(),
        }

    @staticmethod
    def from_dict(d: Optional[Dict]) -> "UpdateNotification":
        """Maps dict to parsed UpdateNotification or None to default. Doesn't validate."""
        d = d if isinstance(d, dict) else {}
        return UpdateNotification(
            min=UpdateData.from_dict(d.get("min")),
            max=UpdateData.from_dict(d.get("max")) if d.get("max") else None,
        )


class NotificationService:
    def __init__(
        self,
        tooltip_uri: str,
        update_uri: str,
        token_auth: TokenAuth,
        http_client_factory: HTTPClientFactory,
        polling_interval: int,
        addon_version: str,
        anki_version: str,
    ):
        self._token_auth = token_auth
        self._polling_interval = polling_interval
        self._addon_version = addon_version
        self._anki_version = anki_version
        self._tooltip_client = http_client_factory.create(tooltip_uri)
        self._update_client = http_client_factory.create(update_uri)
        amboss_did_access_change.append(self._server_notification_cached.cache_clear)
        amboss_did_login.append(self._server_notification_cached.cache_clear)
        amboss_did_logout.append(self._server_notification_cached.cache_clear)

    def tooltip_notification(self) -> Optional[str]:
        return self._server_notification_cached("tooltip", self._ttl_hash())

    def update_notification(self) -> UpdateNotification:
        return UpdateNotification.from_dict(
            self._server_notification_cached("update", self._ttl_hash())
        )

    @lru_cache(maxsize=2)
    def _server_notification_cached(self, client_key: str, _hash=None):
        """
        Queries notification API and holds maximum of 2 results for (clientKey, _hash) tuples in cache.
        Broadly swallows any exceptions and failures in retrieving notifications, e.g., if user is not authorized.
        """
        try:
            response = self._client(client_key).post(
                {
                    "addon_version": self._addon_version,
                    "anki_version": self._anki_version,
                },
                self._token_auth.get_header(),
            )
        except (HTTPError, HTTPWarning):
            return None
        try:
            response = json.loads(response.data.decode("utf-8"))
        except ValueError:
            return None
        return response.get("notification")

    def _client(self, key: str):
        if key == "tooltip":
            return self._tooltip_client
        if key == "update":
            return self._update_client
        raise ValueError(f"No client for key='{key}'")

    def _ttl_hash(self):
        return round(time.time() / self._polling_interval)
