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


from typing import Sequence, Tuple, Union

from ..anki.collection import AnkiCollectionService
from .model_notes import (
    AbridgedNoteQuery,
    Notes,
    abridged_note_query_result_to_model,
    AbridgedNoteQueryResult,
)


class DataProvider:
    def __init__(self, anki_collection_service: AnkiCollectionService):
        self._anki_collection_service = anki_collection_service

    def get_notes_by_query(
        self,
        query: AbridgedNoteQuery,
        query_args: Tuple[Union[str, int, float, None], ...] = (),
    ) -> Notes:
        return [
            abridged_note_query_result_to_model(
                AbridgedNoteQueryResult._make(query_result)
            )
            for query_result in self._anki_collection_service.database.all(
                query, *query_args
            )
        ]

    def get_note_ids_by_filter(self, filter) -> Sequence[int]:
        return self._anki_collection_service.collection.find_notes(filter)

    def get_scalar_by_query(
        self,
        query: str,
        query_args: Tuple[Union[str, int, float, None], ...] = (),
    ) -> Union[str, int, float, None]:
        return self._anki_collection_service.database.scalar(query, *query_args)
