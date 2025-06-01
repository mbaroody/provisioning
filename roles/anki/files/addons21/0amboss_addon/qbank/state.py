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


import time
from typing import List, Optional

from aqt.qt import QObject, QThreadPool

from ..activity import ActivityService
from ..shared import safe_print
from ..user import StudyObjectiveService, UserService
from .model_notes import Notes
from .model_qbank import QuestionStatus
from .performance import (
    EventSubmitter,
    RequestOrigin,
    anki_mature_note_query,
    generate_request_id,
    qbank_mapper_request,
    qbank_mapper_response,
    question_session_size_request,
    question_session_size_response,
)
from .service_mapper import QBankMapperService
from .service_notes import AnkiNoteService
from .service_qbank import QBankSessionService
from .ui_home import QBankHomeWidget, QBankHomeWidgetState
from .worker import SubmitEvent, SubmitProgress, TrackedWorker


class LoggedInQBankStateResolver:
    def __init__(
        self,
        qbank_service: QBankSessionService,
        mapper_service: QBankMapperService,
        study_objective_service: StudyObjectiveService,
        question_statuses: Optional[List[QuestionStatus]] = None,
        last_update_interval: int = 24 * 60 * 60,
    ):
        self._qbank_service = qbank_service
        self._mapper_service = mapper_service
        self._study_objective_service = study_objective_service
        self._question_statuses = question_statuses
        self._last_update_interval = last_update_interval

        self._last_question_ids: Optional[List[str]] = None
        self._last_mature_notes: Optional[Notes] = None
        self._last_update: float = 0

    def resolve_state(
        self,
        mature_notes: Notes,
        matured_card_count: int,
        submit_event: SubmitEvent,
        request_id: str,
        request_origin: RequestOrigin,
    ) -> QBankHomeWidgetState:
        (
            study_objective_value,
            study_objective_label,
        ) = self._study_objective_service.study_objective_value_and_label()

        if not mature_notes or not matured_card_count:
            return QBankHomeWidgetState(
                logged_in=True,
                matured_count_total=0,
                unlocked_total=0,
                question_ids=[],
                study_objective=study_objective_label,
            )

        question_ids = self.question_ids(
            mature_notes=mature_notes,
            study_objective_value=study_objective_value,
            study_objective_label=study_objective_label,
            submit_event=submit_event,
            request_id=request_id,
            request_origin=request_origin,
        )

        if not question_ids:
            return QBankHomeWidgetState(
                logged_in=True,
                matured_count_total=matured_card_count,
                unlocked_total=0,
                question_ids=[],
                study_objective=study_objective_label,
            )

        question_session_size = self._question_session_size(
            question_ids=question_ids,
            submit_event=submit_event,
        )

        if not question_session_size:
            return QBankHomeWidgetState(
                logged_in=True,
                matured_count_total=matured_card_count,
                unlocked_total=0,
                question_ids=question_ids,
                study_objective=study_objective_label,
            )

        return QBankHomeWidgetState(
            logged_in=True,
            matured_count_total=matured_card_count,
            unlocked_total=question_session_size,
            question_ids=question_ids,
            study_objective=study_objective_label,
        )

    def refresh_question_ids(self, mature_notes: Notes) -> bool:
        if self._last_mature_notes != mature_notes:
            return True

        if self._last_update + self._last_update_interval <= time.time():
            return True

        return False

    def question_ids(
        self,
        mature_notes: Notes,
        study_objective_value: Optional[str],
        study_objective_label: Optional[str],
        submit_event: SubmitEvent,
        request_id: str,
        request_origin: RequestOrigin,
    ) -> Optional[List[str]]:
        if not self.refresh_question_ids(mature_notes):
            return self._last_question_ids

        submit_event(
            qbank_mapper_request(
                notes=mature_notes,
                note_sample=mature_notes,
                study_objective=study_objective_label,
            )
        )

        questions = self._mapper_service.fetch_matching_questions(
            notes=mature_notes,
            study_objective=study_objective_value,
            request_id=request_id,
            request_origin=request_origin,
        )

        self._last_update = time.time()
        self._last_mature_notes = mature_notes
        self._last_question_ids = [question.id for question in questions]

        submit_event(qbank_mapper_response(question_ids=self._last_question_ids))

        return self._last_question_ids

    def _question_session_size(
        self,
        question_ids: List[str],
        submit_event: SubmitEvent,
    ) -> Optional[int]:
        submit_event(
            question_session_size_request(
                question_ids=question_ids,
                question_statuses=self._question_statuses,
            )
        )
        question_session_size = self._qbank_service.get_question_session_size(
            question_ids=question_ids, statuses=self._question_statuses
        )
        submit_event(
            question_session_size_response(question_count=question_session_size)
        )
        return question_session_size


class LoggedOutQBankStateResolver:
    @staticmethod
    def resolve_state(matured_card_count: int) -> QBankHomeWidgetState:
        return QBankHomeWidgetState(
            logged_in=False,
            matured_count_total=matured_card_count,
            unlocked_total=0,
            question_ids=None,
            study_objective=None,
        )


class QBankStateService:
    def __init__(
        self,
        user_service: UserService,
        note_service: AnkiNoteService,
        logged_out_qbank_state_resolver: LoggedOutQBankStateResolver,
        logged_in_qbank_state_resolver: LoggedInQBankStateResolver,
        activity_service: ActivityService,
        qbank_widget: QBankHomeWidget,
        max_widget_note_count: int,
    ):
        self._user_service = user_service
        self._note_service = note_service
        self._logged_out_qbank_state_resolver = logged_out_qbank_state_resolver
        self._logged_in_qbank_state_resolver = logged_in_qbank_state_resolver
        self._activity_service = activity_service
        self._qbank_home_widget = qbank_widget
        self._max_widget_note_count = max_widget_note_count

    def is_widget_visible(self) -> bool:
        return self._qbank_home_widget.is_visible()

    def update_ui(self, state: QBankHomeWidgetState):
        self._qbank_home_widget.update(widget_state=state)

    def fetch_state(
        self,
        submit_progress: SubmitProgress,
        submit_event: SubmitEvent,
        request_id: str,
        request_origin: RequestOrigin,
    ) -> QBankHomeWidgetState:
        mature_notes = self._note_service.get_matured_notes(
            max_note_count=self._max_widget_note_count
        )
        matured_card_count = self._note_service.get_matured_card_count(
            max_note_count=self._max_widget_note_count
        )

        submit_event(
            anki_mature_note_query(
                notes=mature_notes,
                max_note_count=self._max_widget_note_count,
            )
        )

        if not self._user_service.is_logged_in():
            return self._logged_out_qbank_state_resolver.resolve_state(
                matured_card_count=matured_card_count
            )

        return self._logged_in_qbank_state_resolver.resolve_state(
            mature_notes=mature_notes,
            matured_card_count=matured_card_count,
            submit_event=submit_event,
            request_id=request_id,
            request_origin=request_origin,
        )

    def maybe_show_load_state(self) -> None:
        if (
            self._user_service.is_logged_in()
            and not self._qbank_home_widget.state.logged_in
        ):
            self.update_ui(QBankHomeWidgetState())


class QBankStateUpdateScheduler(QObject):
    def __init__(
        self,
        thread_pool: QThreadPool,
        qbank_state_service: QBankStateService,
        activity_service: ActivityService,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._thread_pool = thread_pool
        self._activity_service = activity_service
        self._qbank_state_service = qbank_state_service

    def schedule_state_update(self) -> None:
        if not self._qbank_state_service.is_widget_visible():
            return
        event_submitter = EventSubmitter(
            activity_service=self._activity_service,
            request_id=generate_request_id(),
            request_origin=RequestOrigin.anki_home_qbank_widget,
        )
        self._qbank_state_service.maybe_show_load_state()

        def task(submit_progress: SubmitProgress, submit_event: SubmitEvent):
            return self._qbank_state_service.fetch_state(
                submit_progress=submit_progress,
                submit_event=submit_event,
                request_id=event_submitter.request_id,
                request_origin=event_submitter.request_origin,
            )

        worker = TrackedWorker(task=task, receiver=self)
        worker.signals.performance_event.connect(event_submitter)
        worker.signals.result.connect(self._qbank_state_service.update_ui)
        worker.signals.error.connect(lambda error: safe_print(f"{__file__}: {error}"))
        self._thread_pool.start(worker)
