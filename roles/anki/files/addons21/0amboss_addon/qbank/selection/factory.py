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

from typing import Callable, Optional, Tuple, Type

from aqt.qt import QThreadPool, QWidget

from ...debug import ErrorPromptFactory
from ...profile import ProfileAdapter
from ...theme import ThemeManager
from ...user import StudyObjectiveService
from ..launch import QBankSessionLauncher
from ..performance import EventSubmitter
from ..service_mapper import QBankMapperService
from ..service_notes import AnkiNoteService
from ..service_qbank import QBankSessionService
from .dialog import QBankSelectionDialog
from .service import QBankSelectionUIService
from .types import QuestionSelectionOptions


class QBankSelectionUIFactory:
    def __init__(
        self,
        dialog_factory: Type[QBankSelectionDialog],
        ui_service_factory: Type[QBankSelectionUIService],
        theme_manager: ThemeManager,
        error_prompt_factory: ErrorPromptFactory,
        note_service: AnkiNoteService,
        mapper_service: QBankMapperService,
        session_service: QBankSessionService,
        study_objective_service: StudyObjectiveService,
        profile: ProfileAdapter,
        thread_pool: QThreadPool,
        loading_url: str,
        launcher_factory: Type[QBankSessionLauncher],
        store_url: str,
        debug: bool = False,
    ):
        self._dialog_factory = dialog_factory
        self._ui_service_factory = ui_service_factory
        self._theme_manager = theme_manager
        self._error_prompt_factory = error_prompt_factory
        self._note_service = note_service
        self._mapper_service = mapper_service
        self._session_service = session_service
        self._study_objective_service = study_objective_service
        self._profile = profile
        self._thread_pool = thread_pool
        self._loading_url = loading_url
        self._launcher_factory = launcher_factory
        self._store_url = store_url
        self._debug = debug

    def create_selection_ui(
        self,
        question_options: QuestionSelectionOptions,
        context: str,
        max_note_count: int,
        web_browser: Callable[[str], None],
        event_submitter: EventSubmitter,
        parent: Optional[QWidget] = None,
    ) -> Tuple[QBankSelectionDialog, QBankSelectionUIService]:
        dialog = self._dialog_factory(
            theme_manager=self._theme_manager,
            error_prompt_factory=self._error_prompt_factory,
            event_submitter=event_submitter,
            question_options=question_options,
            context=context,
            loading_url=self._loading_url,
            parent=parent,
        )

        ui_service = self._ui_service_factory(
            note_service=self._note_service,
            mapper_service=self._mapper_service,
            session_service=self._session_service,
            study_objective_service=self._study_objective_service,
            event_submitter=event_submitter,
            thread_pool=self._thread_pool,
            max_note_count=max_note_count,
            parent=dialog,
        )

        session_launcher = self._launcher_factory(
            session_service=self._session_service,
            web_browser=web_browser,
            store_url=self._store_url,
            profile=self._profile,
            parent=parent,
            debug=self._debug,
        )

        dialog.update_study_objective_requested.connect(
            ui_service.update_study_objective
        )
        ui_service.study_objective_updated.connect(dialog.set_study_objective)

        dialog.update_note_matches_requested.connect(ui_service.update_note_matches)
        ui_service.note_matches_updated.connect(dialog.set_note_ids)

        dialog.update_question_matches_requested.connect(
            ui_service.update_question_matches
        )
        ui_service.question_matches_updated.connect(dialog.set_questions)

        dialog.update_session_size_requested.connect(ui_service.update_session_size)
        ui_service.session_size_updated.connect(dialog.set_question_count)

        ui_service.progress_updated.connect(dialog.update_progress)

        ui_service.exception_encountered.connect(dialog.handle_service_error)

        dialog.create_session_requested.connect(
            lambda questions, note_ids, study_objective, options: session_launcher.launch_session(
                questions=questions,
                note_ids=note_ids,
                study_objective=study_objective,
                options=options,
                event_submitter=event_submitter,
            )
        )

        dialog.destroyed.connect(ui_service.cleanup)

        return dialog, ui_service
