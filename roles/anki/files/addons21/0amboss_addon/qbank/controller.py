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

import json
from typing import TYPE_CHECKING, Final, List, Optional, cast

from aqt.qt import QWidget

from ..activity import ActivityService
from ..anki.utils import anki_open_link, anki_show_text
from ..debug import QBANK_DEBUG_ACTIVE, ErrorPromptFactory
from ..profile import ProfileAdapter
from ..shared import _
from .launch import show_qbank_access_warning, show_qbank_unknown_error_warning
from .model_notes import Notes
from .model_qbank import (
    Question,
    QuestionDifficulty,
    QuestionOrder,
    QuestionSessionError,
    QuestionStatus,
)
from .performance import (
    EventSubmitter,
    RequestOrigin,
    generate_request_id,
    question_session_request,
    question_session_response,
)
from .service_qbank import QBankSessionService
from .state import QBankStateUpdateScheduler
from .ui_home import QBankHomeWidget

if TYPE_CHECKING:
    from aqt import DialogManager
    from aqt.main import AnkiQt
    from ..sidepanel import SidePanelController


def maybe_debug(
    notes: Notes, questions: List[Question], parent_widget: Optional[QWidget] = None
):
    if QBANK_DEBUG_ACTIVE:  # debug
        debug_content = f"""
<h3>AMBOSS Qbank <-> Anki debug info</h3>

<h4>Note IDs</h4>

<div style="font-family: monospace, monospace;">{[note.id for note in notes]}</div>

<h4>Found questions</h4>

<pre>
{json.dumps([{"id": q.id, "score": q.score, "preview": (q.preview_text[:48] + '...' if q.preview_text else '...')} for q in questions], indent=2)}
</pre>
"""
        anki_show_text(
            debug_content,
            copyBtn=True,
            type="html",
            title="AMBOSS Qbank debug info",
            minWidth=600,
            minHeight=500,
            parent=parent_widget,
        )


class QBankController:
    def __init__(
        self,
        qbank_service: QBankSessionService,
        qbank_state_update_scheduler: QBankStateUpdateScheduler,
        qbank_widget: QBankHomeWidget,
        main_window: "AnkiQt",
        side_panel_controller: "SidePanelController",
        activity_service: ActivityService,
        error_prompt_factory: ErrorPromptFactory,
        dialog_manager: "DialogManager",
        profile: ProfileAdapter,
        store_url: str,
        question_statuses: Optional[List[QuestionStatus]] = None,
    ):
        self._qbank_service = qbank_service
        self._qbank_state_update_scheduler = qbank_state_update_scheduler
        self._qbank_home_widget = qbank_widget
        self._main_window = main_window
        self._side_panel_controller = side_panel_controller
        self._activity_service = activity_service
        self._error_prompt_factory = error_prompt_factory
        self._dialog_manager = dialog_manager
        self._profile = profile
        self._store_url = store_url
        self._question_statuses = question_statuses
        self._order: Final[QuestionOrder] = QuestionOrder.INITIAL

    def start_global_question_session(self, max_size: Optional[int] = None):
        try:
            question_ids = self._qbank_home_widget.question_ids
            if not question_ids:
                return
            # TODO: Discuss UX - side panel desired?
            self.start_question_session(
                question_ids=question_ids,
                statuses=self._question_statuses,
                request_origin=RequestOrigin.anki_home_qbank_widget,
                sidepanel=True,
                max_size=max_size,
            )
        except Exception as e:
            self._error_prompt_factory.create_and_exec(
                e,
                message_heading=_(
                    "Encountered an error while starting a question session"
                ),
            )

    def start_question_session(
        self,
        question_ids: List[str],
        request_origin: RequestOrigin,
        statuses: Optional[List[QuestionStatus]] = None,
        difficulties: Optional[List[QuestionDifficulty]] = None,
        sidepanel: bool = False,
        request_id: Optional[str] = None,
        max_size: Optional[int] = None,
    ) -> Optional[str]:
        request_id = request_id or generate_request_id()
        submit_event = EventSubmitter(
            activity_service=self._activity_service,
            request_id=request_id,
            request_origin=request_origin,
        )

        submit_event(
            question_session_request(
                question_ids=question_ids,
                question_statuses=statuses,
                question_difficulties=difficulties,
                max_size=max_size,
            )
        )
        question_session_meta = self._qbank_service.get_question_session_meta(
            question_ids=question_ids,
            statuses=statuses,
            difficulties=difficulties,
            max_size=max_size,
            order=self._order,
            request_origin=request_origin,
        )
        if question_session_meta.error:
            if question_session_meta.error == QuestionSessionError.empty_session:
                if request_origin == RequestOrigin.anki_home_qbank_widget:
                    self._qbank_state_update_scheduler.schedule_state_update()
                show_qbank_unknown_error_warning(parent=self._main_window)
            else:
                show_qbank_access_warning(
                    store_url=self._store_url,
                    request_origin_value=request_origin.value,
                    user_id=self._profile.id,
                    anon_id=self._profile.anon_id,
                    parent=self._main_window,
                )
            submit_event(
                question_session_response(
                    question_session_meta=question_session_meta,
                    question_session_url=None,
                )
            )
            return None
        question_session_url = self._qbank_service.get_question_session_url(
            question_session_id=cast(str, question_session_meta.session_id),
            request_origin=request_origin,
        )
        submit_event(
            question_session_response(
                question_session_meta=question_session_meta,
                question_session_url=question_session_url,
            )
        )
        if sidepanel:
            self._side_panel_controller.show_url(question_session_url)
        else:
            anki_open_link(question_session_url)
        return question_session_url

    def launch_card_browser(self):
        self._dialog_manager.open("Browser", self._main_window)
