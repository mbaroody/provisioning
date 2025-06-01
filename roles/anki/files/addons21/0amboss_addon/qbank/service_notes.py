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


from typing import Sequence

from .data import DataProvider
from .model_notes import Notes
from .query import (
    get_matured_card_count_query,
    get_matured_notes_query,
    get_notes_from_note_ids_query,
)


class AnkiNoteService:
    def __init__(self, data_provider: DataProvider):
        self._data_provider = data_provider

    def get_matured_notes(self, max_note_count: int) -> Notes:
        return self._data_provider.get_notes_by_query(
            *get_matured_notes_query(max_note_count=max_note_count)
        )

    def get_matured_card_count(self, max_note_count: int) -> int:
        return (
            self._data_provider.get_scalar_by_query(  # type: ignore[return-value]
                *get_matured_card_count_query(max_note_count=max_note_count)
            )
            or 0
        )

    def get_filtered_notes(self, filter_by: str) -> Notes:
        note_ids = self._data_provider.get_note_ids_by_filter(filter_by)
        if not note_ids:
            return []
        return self.get_notes_from_note_ids(note_ids=note_ids)

    def get_notes_from_note_ids(self, note_ids: Sequence[int]) -> Notes:
        return self._data_provider.get_notes_by_query(
            get_notes_from_note_ids_query(note_ids)
        )
