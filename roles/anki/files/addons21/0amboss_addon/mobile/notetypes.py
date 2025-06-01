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

from __future__ import annotations

import dataclasses  # 2.1.19+
from copy import deepcopy
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from ..anki.collection import AnkiNotetypeService, NotetypeDict
from ..anki.errors import NOTETYPE_ERRORS
from ..shared import safe_print
from .html import HTMLParsingError
from .templates import HTMLProcessor, TemplateUpdater


@dataclasses.dataclass
class NotetypesProcessingResult:
    success: bool = dataclasses.field(init=False)
    exception: Optional[Exception] = None
    skipped_notetypes: List[str] = dataclasses.field(default_factory=list)
    debug_data: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        self.success = not bool(self.exception)


class NotetypesProcessor:
    def __init__(
        self,
        notetype_service: AnkiNotetypeService,
        template_updater: TemplateUpdater,
        notetype_updater: NotetypeUpdater,
    ):
        self._notetype_service = notetype_service
        self._template_updater = template_updater
        self._notetype_updater = notetype_updater

    def process_all_notetypes_with(
        self, template_processor: HTMLProcessor
    ) -> NotetypesProcessingResult:
        """Perform template changes on all note types in the user collection"""
        notetype_service = self._notetype_service
        skipped_notetypes: List[str] = []

        for notetype in notetype_service.get_all_notetypes():
            original_notetype = deepcopy(notetype)
            notetype_name = notetype_service.get_name(notetype)

            # Attempt processing templates dict ####

            try:
                if not self._template_updater.update_templates(
                    templates=notetype_service.get_templates(notetype),
                    html_processor=template_processor,
                ):
                    continue
            except HTMLParsingError:
                safe_print(
                    "Warning: Skipping updating note type with template "
                    f"that is not parseable by html.parser: {notetype_name}"
                )
                skipped_notetypes.append(notetype_name)
                continue

            # Attempt writing note type changes ####

            notetype_update_result, error = self._notetype_updater.update_notetype(
                modified_notetype=notetype,
                original_notetype=original_notetype,
            )

            if notetype_update_result == NotetypeUpdateResult.INVALID_BEFORE_UPDATE:
                safe_print(
                    "Warning: Skipping updating note type with invalid note type:"
                    f" {notetype_name}\n"
                    f"Skipped due to: {type(error).__name__}: {error}"
                )
                skipped_notetypes.append(notetype_name)
                continue

            if notetype_update_result == NotetypeUpdateResult.INVALID_AFTER_UPDATE:
                debug_data = self._get_notetype_debug_data(
                    modified_notetype=notetype,
                    original_notetype=original_notetype,
                    notetype_name=notetype_name,
                )

                # abort early, do not process any other note types
                return NotetypesProcessingResult(exception=error, debug_data=debug_data)

        return NotetypesProcessingResult(skipped_notetypes=skipped_notetypes)

    def _get_notetype_debug_data(
        self,
        modified_notetype: NotetypeDict,
        original_notetype: NotetypeDict,
        notetype_name: str,
    ) -> Dict[str, Any]:
        return {
            "notetype_info": {
                "name": notetype_name,
                "fields": [
                    d.get("name")
                    for d in self._notetype_service.get_fields(original_notetype)
                ],
                "original_templates": self._notetype_service.get_templates(
                    original_notetype
                ),
                "modified_templates": self._notetype_service.get_templates(
                    modified_notetype
                ),
            }
        }


class NotetypeUpdateResult(Enum):
    VALID = 0
    INVALID_BEFORE_UPDATE = 1
    INVALID_AFTER_UPDATE = 2


class NotetypeUpdater:
    def __init__(self, notetype_service: AnkiNotetypeService):
        self._notetype_service = notetype_service

    def update_notetype(
        self,
        modified_notetype: NotetypeDict,
        original_notetype: NotetypeDict,
    ) -> Tuple[NotetypeUpdateResult, Optional[Exception]]:
        # NOTE: On 2.1.41 and up we can check whether we're dealing with an existing
        # issue inside the note type, or an issue introduced by us. To do so, we
        # trigger Anki's note type validator by attempting to save the original
        # note type. FIXME: This approach only works on 2.1.41 and up. On earlier
        # Anki revisions we are unaware of invalid note types.

        try:
            self._notetype_service.update_notetype(modified_notetype)

        except NOTETYPE_ERRORS as actual_error:  # 2.1.41+, 2.1.50+
            try:
                self._notetype_service.update_notetype(original_notetype)
            except NOTETYPE_ERRORS as trial_error:
                if trial_error.__class__ != actual_error.__class__:
                    raise
                # all good, template was invalid to start with
            else:  # no good, original template was valid, we caused error
                return NotetypeUpdateResult.INVALID_AFTER_UPDATE, actual_error

            return NotetypeUpdateResult.INVALID_BEFORE_UPDATE, actual_error

        return NotetypeUpdateResult.VALID, None
