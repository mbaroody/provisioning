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


import uuid
from typing import TYPE_CHECKING, Any, Dict, Optional

from .hooks import (
    amboss_did_firstrun,
    amboss_did_login,
    amboss_did_logout,
    profile_did_open,
)

if TYPE_CHECKING:
    from aqt.profiles import ProfileManager


AMBOSS_ID = "ambossId"
ANON_ID = "anonId"


class ProfileAdapter:
    # profile keys that we no longer use:
    _obsolete_keys = (
        "ambossHighlights",
        "ambossQuestionHighlights",
        "ambossCookies",
        "ambossCookiesDE",
    )

    _key_mobile_token_dict = "ambossMobileTokenData"

    def __init__(
        self,
        profile_manager: "ProfileManager",
        token_key: str,
        force_first_run: bool = False,
    ):
        self._profile_manager = profile_manager
        self._token_key = token_key
        self._force_first_run = force_first_run
        # Defer loading Anki profile as it's not available at program start
        self._profile: Dict[str, Any] = {}
        profile_did_open.append(self._on_profile_did_open)

    @property
    def token(self) -> Optional[str]:
        return self._profile.get(self._token_key)

    @token.setter
    def token(self, token: Optional[str]) -> None:
        self._profile[self._token_key] = token

    @property
    def mobile_token_dict(self) -> Optional[Dict[str, Any]]:
        return self._profile.get(self._key_mobile_token_dict)

    @mobile_token_dict.setter
    def mobile_token_dict(self, token_dict: Dict[str, Any]):
        self._profile[self._key_mobile_token_dict] = token_dict

    @property
    def id(self) -> Optional[str]:
        return self._profile.get(AMBOSS_ID)

    @id.setter
    def id(self, id: Optional[str]) -> None:
        self._profile[AMBOSS_ID] = id

    @property
    def anon_id(self) -> str:
        anon_id = self._profile.get(ANON_ID)
        if not anon_id:
            anon_id = str(uuid.uuid4())
            self.anon_id = anon_id
        return anon_id

    @anon_id.setter
    def anon_id(self, id: Optional[str]) -> None:  # type: ignore  # TODO: improve typing
        self._profile[ANON_ID] = id

    def _on_profile_did_open(self) -> None:
        """
        Perform actions on Anki profile open and/or first set-up of AMBOSS entries
        in Anki profile
        """

        self._profile = self._profile_manager.profile  # type: ignore

        self._delete_obsolete_keys()

        first_run = self._force_first_run or (
            self._token_key not in self._profile  # type: ignore
        )

        if first_run:
            amboss_did_logout()
            amboss_did_firstrun()
            return

        if self.token:
            amboss_did_login()
            return

        amboss_did_logout()

    def _delete_obsolete_keys(self):
        for key in self._obsolete_keys:
            if key in self._profile:
                try:
                    del self._profile[key]
                except Exception:
                    pass
