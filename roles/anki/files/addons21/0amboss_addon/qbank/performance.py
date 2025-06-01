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


from enum import Enum
from hashlib import md5
from json import dumps
from random import choice, sample, seed
from string import ascii_lowercase, digits
from typing import TYPE_CHECKING, Any, Dict, List, Optional, TypedDict

from ..activity import ActivityService
from .model_notes import Notes, SampledAbridgedNote
from .model_qbank import (
    QuestionDifficulty,
    QuestionSessionMeta,
    QuestionStatus,
)

if TYPE_CHECKING:
    from .selection import (
        QBankSelectionDialogState,
        QBankSelectionUIServiceSlot,
        QuestionSelectionOptions,
    )

# Event creation


class RequestOrigin(Enum):
    anki_card_browser_sidebar_menu = "anki_card_browser_sidebar_menu"
    anki_card_browser_toolbar_button = "anki_card_browser_toolbar_button"
    anki_home_qbank_widget = "anki_home_qbank_widget"


class Event(TypedDict):
    activity: str
    properties: Dict[str, Any]


# UI interactions


def browser_qbank_button_clicked(
    query: str, is_notes_mode: bool, length_rows: int, length_selected: int
) -> Event:
    return {
        "activity": "browser_qbank_button_clicked",
        "properties": {
            "query": query,
            "view_mode": "note" if is_notes_mode else "card",
            "browser_result_count": length_rows,
            "browser_selection_count": length_selected,
        },
    }


def browser_qbank_context_menu_clicked(query: str) -> Event:
    return {
        "activity": "browser_qbank_context_menu_clicked",
        "properties": {
            "query": query,
        },
    }


def qbank_selection_dialog_shown() -> Event:
    return {
        "activity": "qbank_selection_dialog_shown",
        "properties": {},
    }


def qbank_selection_dialog_rejected(
    dialog_state: "QBankSelectionDialogState",
    shown_for_seconds: float,
    error_encountered: Optional["QBankSelectionUIServiceSlot"],
) -> Event:
    return {
        "activity": "qbank_selection_dialog_rejected",
        "properties": {
            "dialog_state": dialog_state.name,
            "shown_for_seconds": shown_for_seconds,
            "error_encountered": error_encountered.value if error_encountered else None,
        },
    }


def qbank_selection_dialog_accepted(
    question_selection_options: "QuestionSelectionOptions",
    dialog_state: "QBankSelectionDialogState",
    shown_for_seconds: float,
    error_encountered: Optional["QBankSelectionUIServiceSlot"],
) -> Event:
    return {
        "activity": "qbank_selection_dialog_accepted",
        "properties": {
            "question_count": question_selection_options.count,
            "question_statuses": [s.value for s in question_selection_options.statuses],
            "question_difficulties": [
                s.value for s in question_selection_options.difficulties
            ],
            "dialog_state": dialog_state.name,
            "shown_for_seconds": shown_for_seconds,
            "error_encountered": error_encountered.value if error_encountered else None,
        },
    }


# Service events


def anki_mature_note_query(notes: Notes, max_note_count: int) -> Event:
    return {
        "activity": "anki_mature_note_query",
        "properties": {
            "note_subsample": subsample_notes(notes),
            "note_count": len(notes),
            "max_note_count": max_note_count,
        },
    }


def qbank_mapper_request(
    notes: Notes,
    note_sample: Notes,
    study_objective: Optional[str] = None,
    query: Optional[str] = None,
) -> Event:
    return {
        "activity": "qbank_mapper_request",
        "properties": {
            "note_query": query[:128] if query is not None else None,
            "note_query_length": len(query) if query is not None else None,
            "note_subsample": subsample_notes(note_sample),
            "note_count": len(notes),
            "note_sample_count": len(notes),
            "request_study_objective": study_objective,
        },
    }


def qbank_mapper_response(question_ids: List[str]) -> Event:
    return {
        "activity": "qbank_mapper_response",
        "properties": {
            "response_question_id_sample": sample_items(question_ids, 128),
            "response_question_id_count": len(question_ids),
        },
    }


def question_session_size_request(
    question_ids: List[str],
    question_statuses: Optional[List[QuestionStatus]] = None,
    question_difficulties: Optional[List[QuestionDifficulty]] = None,
) -> Event:
    return {
        "activity": "question_session_size_request",
        "properties": {
            "request_question_sample": sample_items(question_ids, 128),
            "request_question_count": len(question_ids),
            **_question_session_criteria_properties(
                question_statuses=question_statuses,
                question_difficulties=question_difficulties,
            ),
        },
    }


def question_session_size_response(question_count: Optional[int]) -> Event:
    return {
        "activity": "question_session_size_response",
        "properties": {
            "response_question_count": question_count,
        },
    }


def question_session_request(
    question_ids: List[str],
    max_size: Optional[int] = None,
    question_statuses: Optional[List[QuestionStatus]] = None,
    question_difficulties: Optional[List[QuestionDifficulty]] = None,
) -> Event:
    return {
        "activity": "question_session_request",
        "properties": {
            "request_question_sample": sample_items(question_ids, 64),
            "request_question_count": len(question_ids),
            "request_question_max_size": max_size,
            **_question_session_criteria_properties(
                question_statuses=question_statuses,
                question_difficulties=question_difficulties,
            ),
        },
    }


def question_session_response(
    question_session_meta: QuestionSessionMeta,
    question_session_url: Optional[str],
) -> Event:
    return {
        "activity": "question_session_response",
        "properties": {
            "response_question_ids": sample_items(
                question_session_meta.question_ids, 128
            ),
            "response_question_count": len(question_session_meta.question_ids),
            "question_session_id": question_session_meta.session_id,
            "question_session_url": question_session_url,
            "question_session_error": question_session_meta.error.value
            if question_session_meta.error
            else None,
        },
    }


# Event submission


class EventSubmitter:
    def __init__(
        self,
        activity_service: ActivityService,
        request_id: str,
        request_origin: RequestOrigin,
    ):
        self.activity_service = activity_service
        self._request_id = request_id
        self._request_origin = request_origin

    def __call__(self, event: Event):
        activity_and_properties: Dict[str, Any] = {
            "activity": event["activity"],
            "properties": {
                **{
                    "request_id": self._request_id,
                    "request_origin": self._request_origin.value,
                },
                **event["properties"],
            },
        }
        self.activity_service.register_activity(**activity_and_properties)

    @property
    def request_id(self) -> str:
        return self._request_id

    @property
    def request_origin(self) -> RequestOrigin:
        return self._request_origin


# Helpers


def generate_request_id() -> str:
    return "".join(choice(ascii_lowercase + digits) for _ in range(16))


def sample_items(items: list, max_items: int, reproducible: bool = True) -> list:
    if max_items >= len(items):
        return items
    if reproducible:
        seed(md5(dumps(items).encode("utf-8")).hexdigest())
    sampled = [items[i] for i in sorted(sample(range(len(items)), max_items))]
    if reproducible:
        seed()
    return sampled


def subsample_notes(
    notes: Notes, max_random_notes: int = 32, max_first_tags: int = 2
) -> List[Dict[str, Any]]:
    note_sample = sample_items(notes, max_items=max_random_notes)
    return [
        SampledAbridgedNote(
            guid=note.guid, tag_sample=note.tags[:max_first_tags]
        )._asdict()
        for note in note_sample
    ]


def _question_session_criteria_properties(
    question_statuses: Optional[List[QuestionStatus]],
    question_difficulties: Optional[List[QuestionDifficulty]],
) -> Dict[str, Optional[List[str]]]:
    return {
        "request_question_statuses": [i.value for i in question_statuses]
        if question_statuses is not None
        else None,
        "request_question_difficulties": [i.value for i in question_difficulties]
        if question_difficulties is not None
        else None,
    }
