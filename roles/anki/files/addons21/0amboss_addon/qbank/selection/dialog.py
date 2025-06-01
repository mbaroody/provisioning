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
from time import time
from typing import Callable, List, Optional, Tuple

from aqt.qt import (
    QDialog,
    QFrame,
    QLabel,
    QSizePolicy,
    QSpacerItem,
    Qt,
    QVBoxLayout,
    QWidget,
    pyqtSignal,
    pyqtSlot,
)

from ...anki.utils import anki_show_info, anki_show_warning
from ...debug import ErrorPromptFactory
from ...shared import _
from ...theme import ThemeManager
from ...user import StudyObjective
from ..icons import get_amboss_qicon
from ..model_qbank import Question
from ..performance import (
    EventSubmitter,
    qbank_selection_dialog_accepted,
    qbank_selection_dialog_rejected,
    qbank_selection_dialog_shown,
)
from ..styles import style_separator
from .button import StartSessionButton
from .count import SliderSpinboxWidget
from .criteria import QuestionCriteriaWidget
from .loading import LoadingWidget
from .service import QBankSelectionUIServiceSlot
from .types import QuestionSelectionOptions


class QBankSelectionDialogState(Enum):
    READY = 0
    LOADING_MATCHES = 1
    LOADING_SESSION_SIZE = 2


class QBankSelectionDialog(QDialog):
    update_study_objective_requested = pyqtSignal()
    update_note_matches_requested = pyqtSignal(str)  # str {note query string}
    update_question_matches_requested = pyqtSignal(
        object, object
    )  # List[int], StudyObjective {note_ids, study_objective}
    update_session_size_requested = pyqtSignal(
        object, object
    )  # List[Questions], QuestionSelectionOptions {questions and options}
    create_session_requested = pyqtSignal(
        object, object, object, object
    )  # List[Questions], List[int], StudyObjective, QuestionSelectionOptions
    # {questions, note_ids, study_objective, options}

    def __init__(
        self,
        theme_manager: ThemeManager,
        error_prompt_factory: ErrorPromptFactory,
        event_submitter: EventSubmitter,
        loading_url: str,  # this is annoying, let's refactor dep injection of URLs
        question_options: QuestionSelectionOptions,
        context: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._theme_manager = theme_manager
        self._error_prompt_factory = error_prompt_factory
        self._event_submitter = event_submitter
        self._icon_amboss = get_amboss_qicon("logo_mono.svg")
        self.setProperty("night_mode", str(theme_manager.night_mode))

        self._questions: Optional[List[Question]] = None
        self._note_ids: Optional[List[int]] = None
        self._note_query: Optional[str] = None
        self._study_objective: Optional[StudyObjective] = None

        self._time_shown: Optional[float] = None
        self._error_encountered: Optional[QBankSelectionUIServiceSlot] = None

        # Set up layout and widgets

        night_mode = theme_manager.night_mode
        create_section = create_section_factory(night_mode)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(16)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        font_title = self.font()
        font_title.setPointSize(10)

        layout_context = QVBoxLayout()
        title_context = QLabel(
            _("Create AMBOSS Qbank Session Based on").upper(), parent=self
        )
        title_context.setFont(font_title)
        self.context = QLabel(self)
        font_context = self.context.font()
        font_context.setPointSize(16)
        self.context.setFont(font_context)
        self.context.setObjectName("context")  # for UI tests
        layout_context.addWidget(title_context)
        layout_context.addWidget(self.context)
        main_layout.addLayout(layout_context)

        self.container_study_objective, layout_study_objective = create_section(self)
        title_study_objective = QLabel(_("Study objective").upper(), parent=self)
        title_study_objective.setFont(font_title)
        self.study_objective = QLabel(self)
        self.study_objective.setObjectName("study_objective")
        layout_study_objective.addWidget(title_study_objective)
        layout_study_objective.addWidget(self.study_objective)
        main_layout.addWidget(self.container_study_objective)

        self.loading = LoadingWidget(
            height=320, url=loading_url, theme_manager=theme_manager, parent=self
        )
        self.loading.setContentsMargins(0, 30, 0, 20)
        self.loading.setObjectName("loading")
        main_layout.addWidget(self.loading)

        self.container_criteria, layout_criteria = create_section(self)
        self.criteria = QuestionCriteriaWidget(
            question_statuses=[],
            question_difficulties=[],
            night_mode=night_mode,
            parent=self,
        )
        self.criteria.setObjectName("criteria")
        layout_criteria.addWidget(self.criteria)
        main_layout.addWidget(self.container_criteria)

        self.container_question_count, layout_question_count = create_section(self)
        title_question_count = QLabel(_("Question Count").upper(), parent=self)
        title_question_count.setFont(font_title)
        self.question_count = SliderSpinboxWidget(parent=self)
        self.question_count.setObjectName("question_count")
        layout_question_count.addWidget(title_question_count)
        layout_question_count.addWidget(self.question_count)
        main_layout.addWidget(self.container_question_count)

        main_layout.addStretch(1)

        self.button_start = StartSessionButton(
            label=_("Start Qbank Session"),
            night_mode=night_mode,
            parent=self,
        )
        self.button_start.setObjectName("button_start")
        main_layout.addWidget(self.button_start)

        # Wire up signals and slots

        self.criteria.criteria_changed.connect(self.trigger_update_session_size)
        self.button_start.clicked.connect(self.accept)
        self.accepted.connect(self.trigger_create_session)

        # Set options

        # - labels
        self.set_context(context)

        # - question options
        self.criteria.set_question_statuses(question_options.statuses)
        self.criteria.set_question_difficulties(question_options.difficulties)
        self.question_count.set_value(question_options.count)

        # Finalize

        self._state: QBankSelectionDialogState
        self.set_state(QBankSelectionDialogState.LOADING_MATCHES)
        self.setLayout(main_layout)
        self.resize(480, 500)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.setWindowTitle(_("Start an AMBOSS Qbank Session"))

    def show(self) -> None:
        self._time_shown = time()
        self._event_submitter(qbank_selection_dialog_shown())
        return super().show()

    def accept(self) -> None:
        self._event_submitter(
            qbank_selection_dialog_accepted(
                question_selection_options=self.get_question_options(),
                dialog_state=self._state,
                shown_for_seconds=self._time_elapsed(),
                error_encountered=self._error_encountered,
            )
        )
        return super().accept()

    def reject(self) -> None:
        self._event_submitter(
            qbank_selection_dialog_rejected(
                dialog_state=self._state,
                shown_for_seconds=self._time_elapsed(),
                error_encountered=self._error_encountered,
            )
        )
        return super().reject()

    def _time_elapsed(self) -> float:
        if self._time_shown is None:
            return 0
        return time() - self._time_shown

    @pyqtSlot(object)
    def set_study_objective(self, study_objective: StudyObjective):
        value = study_objective.value
        label = study_objective.label
        if value is None or label is None:
            label = _("General studies")
        else:
            label = f"USMLE {label}" if value.startswith("step") else label

        self.study_objective.setText(label)
        self._study_objective = study_objective
        self.trigger_update_question_matches()

    def set_note_query(self, query: str):
        self._note_query = query
        self.trigger_update_note_matches()

    @pyqtSlot(object)
    def set_note_ids(self, note_ids: List[int]):
        self._note_ids = note_ids
        self.trigger_update_question_matches()

    @pyqtSlot(object)
    def set_questions(self, questions: List[Question]):
        self._questions = questions
        if not questions:
            self.set_question_count(0)
            self.set_state(QBankSelectionDialogState.READY)
            anki_show_info(
                _(
                    "We were unable to find a good set of questions matching your study"
                    " objective for your selection of cards. Please try again with a"
                    " different selection."
                ),
                title=_("AMBOSS: No Matching Questions Found"),
                parent=self,
            )
            return
        self.trigger_update_session_size()

    def get_study_objective(self) -> Optional[StudyObjective]:
        return self._study_objective

    def get_note_ids(self) -> Optional[List[int]]:
        return self._note_ids

    def get_questions(self) -> Optional[List[Question]]:
        return self._questions

    def get_question_ids(self) -> Optional[List[str]]:
        if self._questions is None:
            return None
        return [question.id for question in self._questions]

    def set_context(self, context: str):
        self._context = context
        self.context.setText(self._context)

    def get_question_options(self) -> QuestionSelectionOptions:
        return QuestionSelectionOptions(
            count=self.question_count.get_value(),
            statuses=self.criteria.get_question_statuses(),
            difficulties=self.criteria.get_question_difficulties(),
        )

    @pyqtSlot(object)
    def set_question_count(self, count: Optional[int]):
        if count is None:
            anki_show_warning(
                _(
                    "We could not determine the question session size for your "
                    "selection of cards. Please try again with a different selection."
                ),
                title=_("AMBOSS: Unable to Determine Session Size"),
                parent=self,
            )
            count = 0
        self.question_count.set_maximum(count)
        self.set_state(QBankSelectionDialogState.READY)

    def set_state(self, state: QBankSelectionDialogState):
        if state == QBankSelectionDialogState.LOADING_MATCHES:
            self.loading.show()
            self.container_study_objective.hide()
            self.container_criteria.hide()
            self.container_question_count.hide()
            self.button_start.set_enabled(False)
        elif state == QBankSelectionDialogState.LOADING_SESSION_SIZE:
            self.loading.hide()
            self.container_study_objective.show()
            self.container_criteria.show()
            self.container_question_count.show()
            self.container_question_count.setEnabled(False)
            self.button_start.set_loading()
        elif state == QBankSelectionDialogState.READY:
            self.loading.hide()
            self.container_study_objective.show()
            self.container_criteria.show()
            self.container_question_count.show()
            maximum_questions = self.question_count.get_maximum()
            count_selector_enabled = maximum_questions > 0
            self.container_question_count.setEnabled(count_selector_enabled)
            self.button_start.set_enabled(count_selector_enabled)

        self._state = state

    def get_state(self) -> QBankSelectionDialogState:
        return self._state

    @pyqtSlot(str, float)
    def update_progress(self, message: str, value_percent: float):
        if self._state != QBankSelectionDialogState.LOADING_MATCHES:
            return
        self.loading.set_text(message)

    def trigger_update_study_objective(self):
        self.update_study_objective_requested.emit()

    def trigger_update_note_matches(self):
        self.set_state(QBankSelectionDialogState.LOADING_MATCHES)
        self.update_note_matches_requested.emit(self._note_query)

    def trigger_update_question_matches(self):
        self.set_state(QBankSelectionDialogState.LOADING_MATCHES)
        study_objective = self.get_study_objective()
        if study_objective is None:
            self.update_study_objective_requested.emit()
            return
        self.update_question_matches_requested.emit(
            self.get_note_ids(), study_objective
        )

    @pyqtSlot()
    def trigger_update_session_size(self):
        self.set_state(QBankSelectionDialogState.LOADING_SESSION_SIZE)
        self.update_session_size_requested.emit(
            self.get_question_ids(), self.get_question_options()
        )

    @pyqtSlot()
    def trigger_create_session(self):
        self.create_session_requested.emit(
            self.get_questions(),
            self.get_note_ids(),
            self.get_study_objective(),
            self.get_question_options(),
        )

    @pyqtSlot(object, object)
    def handle_service_error(
        self, exception: Exception, service_slot: QBankSelectionUIServiceSlot
    ):
        if self._error_encountered:  # avoid multiple error prompts
            return
        self._error_encountered = service_slot
        self._error_prompt_factory.create_and_exec(
            exception,
            message_heading=_("Encountered an error while starting a question session"),
            message_body=_("Error context: ") + service_slot.value,
            parent=self,
        )
        self.reject()


def create_separator(parent: QWidget, night_mode: bool) -> QFrame:
    separator = QFrame(parent)
    separator.setFrameShape(QFrame.Shape.HLine)
    separator.setFrameShadow(QFrame.Shadow.Sunken)
    separator.setStyleSheet(style_separator)
    separator.setProperty("night_mode", str(night_mode))
    return separator


def create_vertical_spacer(
    height: int, size_policy: QSizePolicy.Policy = QSizePolicy.Policy.Fixed
) -> QSpacerItem:
    return QSpacerItem(20, height, QSizePolicy.Policy.Minimum, size_policy)


def create_section_factory(
    night_mode: bool,
) -> Callable[[QWidget], Tuple[QWidget, QVBoxLayout]]:
    def create_section(parent: QWidget) -> Tuple[QWidget, QVBoxLayout]:
        container = QWidget(parent)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        container.setLayout(layout)
        separator = create_separator(parent, night_mode)
        layout.addWidget(separator)
        layout.addSpacerItem(create_vertical_spacer(10))
        return container, layout

    return create_section
