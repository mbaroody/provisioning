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


from typing import Sequence, Tuple

from anki.utils import ids2str

from .model_notes import AbridgedNoteQuery

MATURE_INTERVAL = 21


def get_matured_notes_query(
    max_note_count: int,
) -> Tuple[AbridgedNoteQuery, Tuple[int, int]]:
    return """\
WITH
  cards_view AS (
  SELECT
    n.guid note_guid,
    n.id note_id,
    n.tags note_tags,
    n.flds note_flds,
    c.id card_id,
    c.ivl card_ivl,
    c.queue card_queue
  FROM
    cards c
  JOIN
    notes n
  ON
    c.nid = n.id
  WHERE
    c.ivl >= ?
    AND c.queue != -1),
  revlog_view AS (
  SELECT
    cv.card_id,
    r.id revlog_id
  FROM
    cards_view cv
  LEFT JOIN
    revlog r
  ON
    cv.card_id = r.cid),
  joined_view AS (
  SELECT
    cv.note_guid,
    cv.note_id,
    cv.note_tags,
    cv.note_flds,
    cv.card_id,
    cv.card_ivl,
    cv.card_queue,
    IFNULL(MAX(rv.revlog_id), 0) revlog_max_id
  FROM
    cards_view cv
  LEFT JOIN
    revlog_view rv
  ON
    cv.card_id = rv.card_id
  GROUP BY
    cv.note_guid,
    cv.note_id,
    cv.note_tags,
    cv.note_flds,
    cv.card_id,
    cv.card_ivl,
    cv.card_queue)
SELECT
  note_guid,
  note_id,
  note_tags,
  note_flds,
  GROUP_CONCAT(card_id) card_ids,
  GROUP_CONCAT(card_ivl) card_ivls,
  GROUP_CONCAT(card_queue) card_queues,
  GROUP_CONCAT(revlog_max_id) revlog_max_ids
FROM
  joined_view
GROUP BY
  note_guid,
  note_id,
  note_tags,
  note_flds
  ORDER BY
    MIN(card_ivl),
    note_guid
LIMIT
  ?;
""", (
        MATURE_INTERVAL,
        max_note_count,
    )


def get_notes_from_note_ids_query(note_ids: Sequence[int]) -> AbridgedNoteQuery:
    return f"""\
WITH
  cards_view AS (
  SELECT
    n.guid note_guid,
    n.id note_id,
    n.tags note_tags,
    n.flds note_flds,
    c.id card_id,
    c.ivl card_ivl,
    c.queue card_queue
  FROM
    cards c
  JOIN
    notes n
  ON
    c.nid = n.id
  WHERE
    n.id IN {ids2str(note_ids)}),
  revlog_view AS (
  SELECT
    cv.card_id,
    r.id revlog_id
  FROM
    cards_view cv
  LEFT JOIN
    revlog r
  ON
    cv.card_id = r.cid),
  joined_view AS (
  SELECT
    cv.note_guid,
    cv.note_id,
    cv.note_tags,
    cv.note_flds,
    cv.card_id,
    cv.card_ivl,
    cv.card_queue,
    IFNULL(MAX(rv.revlog_id), 0) revlog_max_id
  FROM
    cards_view cv
  LEFT JOIN
    revlog_view rv
  ON
    cv.card_id = rv.card_id
  GROUP BY
    cv.note_guid,
    cv.note_id,
    cv.note_tags,
    cv.note_flds,
    cv.card_id,
    cv.card_ivl,
    cv.card_queue)
SELECT
  note_guid,
  note_id,
  note_tags,
  note_flds,
  GROUP_CONCAT(card_id) card_ids,
  GROUP_CONCAT(card_ivl) card_ivls,
  GROUP_CONCAT(card_queue) card_queues,
  GROUP_CONCAT(revlog_max_id) revlog_max_ids
FROM
  joined_view
GROUP BY
  note_guid,
  note_id,
  note_tags,
  note_flds
ORDER BY
  MIN(card_ivl),
  note_guid
 """


def get_matured_card_count_query(max_note_count: int) -> Tuple[str, Tuple[int, int]]:
    return """\
WITH
  cards_view AS (
  SELECT
    n.guid note_guid,
    c.id card_id,
    c.ivl card_ivl
  FROM
    cards c
  JOIN
    notes n
  ON
    c.nid = n.id
  WHERE
    c.ivl >= ?
    AND c.queue != -1),
  joined_view AS (
  SELECT
    note_guid,
    COUNT(card_id) card_count
  FROM
    cards_view
  GROUP BY
    note_guid
  ORDER BY
    MIN(card_ivl),
    note_guid
  LIMIT
    ? )
SELECT
  SUM(card_count)
FROM
  joined_view;
""", (
        MATURE_INTERVAL,
        max_note_count,
    )
