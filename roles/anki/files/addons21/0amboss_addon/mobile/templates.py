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


from typing import List, Optional, Protocol

from ..anki.collection import AnkiNotetypeService, CardSide, TemplateDict
from ..shared import safe_print


class HTMLProcessor(Protocol):
    def __call__(self, html: str) -> Optional[str]:
        """Processes html template, optionally returning modified version of template

        Args:
            html: template to modify

        Returns:
            modified template or None. A None return type signifies that template is not
            in need of any modifications.
        """
        ...


class TemplateUpdater:
    def __init__(self, notetype_service: AnkiNotetypeService):
        self._notetype_service = notetype_service

    def update_templates(
        self,
        templates: List[TemplateDict],
        html_processor: HTMLProcessor,
    ) -> bool:
        templates_were_modified = False

        template: TemplateDict
        for template in templates:
            templates_were_modified = self.update_template(
                template=template,
                html_processor=html_processor,
            )

        return templates_were_modified

    def update_template(
        self,
        template: TemplateDict,
        html_processor: HTMLProcessor,
    ):
        templates_were_modified = False

        for card_side in CardSide:
            card_side_template = self._notetype_service.get_template_side(
                template, card_side=card_side
            )
            if card_side_template is None:
                safe_print(f"Invalid {card_side} template. This should never happen.")
                return False
            modified_card_side_template = html_processor(html=card_side_template)
            if modified_card_side_template is not None:
                self._notetype_service.set_template_side(
                    template, card_side=card_side, content=modified_card_side_template
                )
                templates_were_modified = True

        return templates_were_modified
