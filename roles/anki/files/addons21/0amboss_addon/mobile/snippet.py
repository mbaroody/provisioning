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

import base64
import json
from enum import Enum
from typing import NamedTuple

from .html import TagUpdater
from .notetypes import NotetypesProcessingResult, NotetypesProcessor


class ModificationType(Enum):
    SNIPPET_REMOVED = 0
    SNIPPET_INSERTED = 1


class SnippetData(NamedTuple):
    # camelCase for consistency with JS
    anonId: str
    userId: str
    token: str


class SnippetManager:
    _snippet_template = """\
<script type="module" src="{script_uri}" data-addon="{data_addon}" \
id="amboss-snippet"></script>"""

    def __init__(self, notetypes_processor: NotetypesProcessor, script_uri: str):
        self._notetypes_processor = notetypes_processor
        self._script_uri = script_uri

    def insert_snippet(self, data: SnippetData) -> NotetypesProcessingResult:
        # TODO: Update snippet if data_addon changed
        data_addon = base64.b64encode(
            json.dumps(data._asdict(), ensure_ascii=True).encode("utf-8")
        ).decode("utf-8")
        snippet = self._snippet_template.format(
            script_uri=self._script_uri, data_addon=data_addon
        )
        return self._notetypes_processor.process_all_notetypes_with(
            template_processor=lambda html: TagUpdater.add_or_replace_tag(snippet, html)
        )

    def remove_snippet(self) -> NotetypesProcessingResult:
        # Tag removal is solely based on tag ID and thus URI- and data-agnostic
        snippet = self._snippet_template.format(script_uri="", data_addon="")
        return self._notetypes_processor.process_all_notetypes_with(
            template_processor=lambda html: TagUpdater.remove_tag(snippet, html)
        )
