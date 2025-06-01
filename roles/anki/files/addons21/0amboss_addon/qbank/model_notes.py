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


from typing import List, NamedTuple, Optional

from ..anki.collection import AnkiCollectionService


class Card(NamedTuple):
    ivl: int
    queue: Optional[int] = None
    rev: Optional[int] = None


class AbridgedNote(NamedTuple):
    guid: str
    id: int
    tags: List[str]
    fields: List[str]
    cards: Optional[List[Card]] = None

    def dict(self):
        d = self._asdict()
        if self.cards is not None:
            d["cards"] = [c._asdict() for c in self.cards]
        return d


class SampledAbridgedNote(NamedTuple):
    guid: str
    tag_sample: List[str]


Notes = List[AbridgedNote]
SampledNotes = List[SampledAbridgedNote]

AbridgedNoteQuery = str


class AbridgedNoteQueryResult(NamedTuple):
    note_guid: str
    note_id: int
    note_tags: str
    note_fields: str
    card_ids: str
    card_intervals: str
    card_queues: str
    revlog_max_ids: str


def abridged_note_query_result_to_model(
    result: AbridgedNoteQueryResult,
) -> AbridgedNote:
    return AbridgedNote(
        guid=result.note_guid,
        id=result.note_id,
        tags=result.note_tags.strip().split(" "),
        fields=result.note_fields.split(AnkiCollectionService.db_separator),
        cards=[
            Card(
                ivl=int(interval_str),
                queue=int(queue_str),
                rev=int(revlog_max_id_str) if revlog_max_id_str != "0" else None,
            )
            for interval_str, queue_str, revlog_max_id_str in zip(
                result.card_intervals.split(","),
                result.card_queues.split(","),
                result.revlog_max_ids.split(","),
            )
        ],
    )
