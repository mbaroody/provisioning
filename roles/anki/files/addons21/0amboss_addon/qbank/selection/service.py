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
from typing import Any, Callable, Dict, List, Optional, Sequence

from aqt.qt import QObject, QThreadPool, QTimer, pyqtSignal, pyqtSlot

from ...shared import _, safe_print
from ...user import StudyObjective, StudyObjectiveService
from ..model_qbank import Question
from ..performance import (
    EventSubmitter,
    qbank_mapper_request,
    qbank_mapper_response,
    question_session_size_request,
    question_session_size_response,
    sample_items,
)
from ..service_mapper import QBankMapperService
from ..service_notes import AnkiNoteService
from ..service_qbank import QBankSessionService
from ..worker import Progress, SubmitEvent, SubmitProgress, TrackedWorker
from .types import QuestionSelectionOptions


class QBankSelectionUIServiceSlot(Enum):
    UPDATE_STUDY_OBJECTIVE = "update_study_objective"
    UPDATE_NOTE_MATCHES = "update_note_matches"
    UPDATE_QUESTION_MATCHES = "update_question_matches"
    UPDATE_SESSION_SIZE = "update_session_size"


class QBankSelectionUIService(QObject):
    study_objective_updated = pyqtSignal(object)  # StudyObjective
    note_matches_updated = pyqtSignal(object)  # List[int] {note_ids}
    question_matches_updated = pyqtSignal(object)  # List[str] {question_ids}
    session_size_updated = pyqtSignal(object)  # Optional[int] {session_size}
    progress_updated = pyqtSignal(str, float)  # str, float {message, value_percent}
    exception_encountered = pyqtSignal(
        object, object
    )  # Exception, QBankSelectionUIServiceSlot {exception, route}

    def __init__(
        self,
        note_service: AnkiNoteService,
        mapper_service: QBankMapperService,
        session_service: QBankSessionService,
        study_objective_service: StudyObjectiveService,
        event_submitter: EventSubmitter,
        thread_pool: QThreadPool,
        max_note_count: int,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._note_service = note_service
        self._mapper_service = mapper_service
        self._session_service = session_service
        self._study_objective_service = study_objective_service
        self._event_submitter = event_submitter
        self._thread_pool = thread_pool
        self._max_note_count = max_note_count
        self._timers: List[QTimer] = []
        self._workers: Dict[QBankSelectionUIServiceSlot, TrackedWorker] = {}

    @pyqtSlot()
    def update_study_objective(self) -> None:
        def task(
            submit_progress: SubmitProgress, submit_event: SubmitEvent
        ) -> StudyObjective:
            submit_progress(Progress(_("Fetching study objective..."), 5))
            study_objective = (
                self._study_objective_service.study_objective_value_and_label()
            )

            return study_objective

        worker = self._create_worker(
            task, QBankSelectionUIServiceSlot.UPDATE_STUDY_OBJECTIVE
        )
        worker.signals.result.connect(self.study_objective_updated.emit)

        self._thread_pool.start(worker)

    @pyqtSlot(str)
    def update_note_matches(self, query: str) -> None:
        """Serves as the entry point whenever we start without an existing selection of notes.

        Used in two paths:

            1. (current) Entry point from browser, when limiting by query (e.g. right-click on tag)
            2. (todo) Triggered by home screen version of the selection dialog that will include
            note selection criteria (e.g. time period, status)

        TODO: Expand arguments with corresponding criteria
        """

        def task(
            submit_progress: SubmitProgress, submit_event: SubmitEvent
        ) -> List[int]:
            submit_progress(Progress(_("Filtering notes..."), 10))
            notes = self._note_service.get_filtered_notes(filter_by=query)

            return [note.id for note in notes]

        worker = self._create_worker(
            task, QBankSelectionUIServiceSlot.UPDATE_NOTE_MATCHES
        )
        worker.signals.result.connect(self.note_matches_updated.emit)

        self._thread_pool.start(worker)

    @pyqtSlot(object, object)
    def update_question_matches(
        self, note_ids: Sequence[int], study_objective: StudyObjective
    ) -> None:
        def task(
            submit_progress: SubmitProgress, submit_event: SubmitEvent
        ) -> List[Question]:
            submit_progress(Progress(_("Gathering notes..."), 25))
            notes = self._note_service.get_notes_from_note_ids(note_ids=note_ids)
            note_sample = sample_items(notes, self._max_note_count)

            # Use multiple messages to signal progress when processing takes long
            interval = min(max(len(notes) // 500, 1), 10)
            delay = 1
            for message, value_percent in [
                (_("Processing notes..."), 50),
                (_("Identifying medical entities..."), 55),
                (_("Finding matching questions..."), 60),
                (_("Personalizing question selection..."), 65),
                (_("Finding additional questions..."), 70),
                (_("Personalizing additional questions..."), 75),
                (_("Finalizing..."), 80),
            ]:
                submit_progress(Progress(message, value_percent, delay))
                delay += interval

            submit_event(qbank_mapper_request(notes=notes, note_sample=note_sample))
            questions = self._mapper_service.fetch_matching_questions(
                notes=note_sample,
                study_objective=study_objective.value,
                request_id=self._event_submitter.request_id,
                request_origin=self._event_submitter.request_origin,
            )
            question_ids = [question.id for question in questions]
            submit_event(qbank_mapper_response(question_ids=question_ids))

            return questions

        worker = self._create_worker(
            task, QBankSelectionUIServiceSlot.UPDATE_QUESTION_MATCHES
        )
        worker.signals.result.connect(self.question_matches_updated.emit)

        self._thread_pool.start(worker)

    @pyqtSlot(object, object)
    def update_session_size(
        self, question_ids: List[str], options: QuestionSelectionOptions
    ) -> None:
        def task(
            submit_progress: SubmitProgress, submit_event: SubmitEvent
        ) -> Optional[int]:
            question_statuses = options.statuses
            question_difficulties = options.difficulties

            submit_progress(Progress(_("Filtering questions..."), 85))
            submit_event(
                question_session_size_request(
                    question_ids=question_ids,
                    question_statuses=question_statuses,
                    question_difficulties=question_difficulties,
                )
            )
            session_size = self._session_service.get_question_session_size(
                question_ids=question_ids,
                statuses=question_statuses,
                difficulties=question_difficulties,
            )
            submit_event(question_session_size_response(question_count=session_size))

            return session_size

        worker = self._create_worker(
            task, QBankSelectionUIServiceSlot.UPDATE_SESSION_SIZE
        )
        worker.signals.result.connect(self.session_size_updated.emit)

        self._thread_pool.start(worker)

    def _create_worker(
        self,
        task: Callable[[SubmitProgress, SubmitEvent], Any],
        slot: QBankSelectionUIServiceSlot,
    ) -> TrackedWorker:
        # Abort any previous worker for the same slot
        try:
            self._workers.pop(slot).cancel()
        except KeyError:
            pass
        worker = TrackedWorker(task=task, receiver=self)
        worker.signals.performance_event.connect(self._event_submitter)
        worker.signals.progress.connect(self._emit_progress)
        worker.signals.error.connect(
            lambda exception: self._handle_exception(exception, slot)
        )
        self._workers[slot] = worker
        return worker

    @pyqtSlot(object, object)
    def _handle_exception(
        self, exception: Exception, route: QBankSelectionUIServiceSlot
    ) -> None:
        safe_print(f"qbank_ui_service_error:{route}: ", exception)
        self.exception_encountered.emit(exception, route)

    @pyqtSlot(object)
    def _emit_progress(self, progress: Progress) -> None:
        @pyqtSlot()
        def emit():
            self.progress_updated.emit(progress.message, progress.value_percent)

        if not progress.delay:
            emit()
            return

        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(progress.delay * 1000)
        timer.timeout.connect(emit)
        timer.start()
        self._timers.append(timer)

    @pyqtSlot()
    def cleanup(self):
        for worker in self._workers.values():
            worker.cancel()
        for timer in self._timers:
            timer.stop()
        self._workers = {}
        self._timers = []
