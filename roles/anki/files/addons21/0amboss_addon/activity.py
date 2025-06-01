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
from typing import TYPE_CHECKING, Dict, Optional
from urllib.parse import quote

if TYPE_CHECKING:
    from aqt.webview import AnkiWebView

    from .profile import ProfileAdapter


class ActivityService:
    def __init__(self, web_view: "AnkiWebView", profile: "ProfileAdapter"):
        self._web_view = web_view
        self._profile = profile

    def register_activity(self, activity: str, properties: Optional[dict] = None):
        # TODO?: assert within python that `ambossAddon` exists
        self._web_view.eval(
            f"""\
if (typeof ambossAddon !== "undefined" && ambossAddon.analytics) {{
  ambossAddon.analytics.track("{activity}", {json.dumps(properties or {})})
}}"""
        )


class ActivityCookieService:
    def __init__(self, profile: "ProfileAdapter", domain: str):
        self._profile = profile
        self._domain = domain

    def cookie_header(self) -> Dict[str, str]:
        return {
            "Cookie": "; ".join(
                [
                    f"{name}={quote(value)}"
                    for name, value in {
                        "ajs_anonymous_id": self._profile.anon_id,
                        "ajs_user_id": self._profile.id,
                    }.items()
                    if value
                ]
            )
        }
