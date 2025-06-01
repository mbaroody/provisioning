# AMBOSS Anki Add-on
#
# Copyright (C) 2019-2023 AMBOSS MD Inc. <https://www.amboss.com/us>
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


from .debug import DebugService


class UserAgentService:
    def __init__(self, debug_service: DebugService, anki_version: str):
        self._debug_service = debug_service
        self._anki_version = anki_version

    def user_agent(self) -> str:
        amboss = self._debug_service.get_for_machine().get("amboss", {})
        anki = self._debug_service.get_for_machine().get("anki", {})
        return (
            f"""AMBOSS Anki add-on (AMBOSS v{amboss.get("version")}; Anki v{self._anki_version}); """
            + "; ".join(
                f"{k}: {v}"
                for k, v in {
                    "Python": anki.get("python"),
                    "PyQt": anki.get("pyqt"),
                    "Chromium": anki.get("chromium"),
                    "Platform": anki.get("platform"),
                    "AnkiBuild": anki.get("version"),
                    "Flavor": anki.get("flavor"),
                    "Language": amboss.get("language"),
                    "Stage": amboss.get("stage"),
                    "Channel": amboss.get("channel"),
                }.items()
            )
        )
