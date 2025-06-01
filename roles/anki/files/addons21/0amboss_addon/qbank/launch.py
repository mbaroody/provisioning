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

import json
from typing import Callable, List, Optional, TYPE_CHECKING, cast

from aqt.qt import QObject, QWidget

from ..anki.utils import anki_show_text, anki_show_warning
from ..profile import ProfileAdapter
from ..shared import _
from ..user import StudyObjective
from .model_qbank import Question, QuestionSessionError
from .performance import (
    EventSubmitter,
    question_session_request,
    question_session_response,
)
from .service_qbank import QBankSessionService

if TYPE_CHECKING:
    from .selection import QuestionSelectionOptions


class QBankSessionLauncher(QObject):
    def __init__(
        self,
        session_service: QBankSessionService,
        web_browser: Callable[[str], None],
        store_url: str,
        profile: ProfileAdapter,
        parent: Optional[QWidget] = None,
        debug: bool = False,
    ):
        super().__init__(parent)
        self._session_service = session_service
        self._web_browser = web_browser
        self._store_url = store_url
        self._profile = profile
        self._debug = debug

    def launch_session(
        self,
        questions: List[Question],
        note_ids: List[int],
        options: "QuestionSelectionOptions",
        study_objective: StudyObjective,
        event_submitter: EventSubmitter,
    ):
        question_ids = [question.id for question in questions]
        event_submitter(
            question_session_request(
                question_ids=question_ids,
                question_statuses=options.statuses,
                question_difficulties=options.difficulties,
                max_size=options.count,
            )
        )

        question_session_meta = self._session_service.get_question_session_meta(
            question_ids=question_ids,
            statuses=options.statuses,
            difficulties=options.difficulties,
            max_size=options.count,
            order=options.order,
            request_origin=event_submitter.request_origin,
            note_count=len(note_ids),
        )

        if question_session_meta.error:
            if question_session_meta.error == QuestionSessionError.empty_session:
                show_qbank_unknown_error_warning(parent=self.parent())
            else:
                show_qbank_access_warning(
                    store_url=self._store_url,
                    request_origin_value=event_submitter.request_origin.value,
                    user_id=self._profile.id,
                    anon_id=self._profile.anon_id,
                    parent=self.parent(),
                )
            event_submitter(
                question_session_response(
                    question_session_meta=question_session_meta,
                    question_session_url=None,
                )
            )
            return None

        question_session_url = self._session_service.get_question_session_url(
            question_session_id=cast(str, question_session_meta.session_id),
            request_origin=event_submitter.request_origin,
        )
        event_submitter(
            question_session_response(
                question_session_meta=question_session_meta,
                question_session_url=question_session_url,
            )
        )

        self._web_browser(question_session_url)

        if not self._debug:
            return

        show_qbank_session_debug_info(
            questions=questions,
            note_ids=note_ids,
            options=options,
            study_objective=study_objective,
            session_url=question_session_url,
            parent=self.parent(),
        )

    def parent(self) -> Optional[QWidget]:  # type: ignore[override]
        return cast(Optional[QWidget], super().parent())


def show_qbank_access_warning(
    store_url: str,
    request_origin_value: str,
    user_id: Optional[str],
    anon_id: str,
    parent: Optional[QWidget] = None,
):
    url = f"{store_url}?utm_source=anki&utm_medium={request_origin_value}&aid={anon_id}"
    if user_id:
        url += f"&uid={user_id}"
    anki_show_warning(
        _("Could not create question session. Please make sure you have Qbank access.")
        + "<br><br>"
        + f"<a href='{url}'>"
        + _("Choose the membership that's right for you in our shop.")
        + "</a>",
        title=_("AMBOSS: Could not create question session"),
        parent=parent,
    )


def show_qbank_unknown_error_warning(parent: Optional[QWidget] = None):
    anki_show_warning(
        _("Could not create question session. Please try again later."),
        title=_("AMBOSS: Could not create question session"),
        parent=parent,
    )


def show_qbank_session_debug_info(
    questions: List[Question],
    note_ids: List[int],
    options: "QuestionSelectionOptions",
    study_objective: StudyObjective,
    session_url: str,
    parent: Optional[QWidget] = None,
):
    content = f"""
<h3>AMBOSS Qbank <-> Anki debug info</h3>

<h4>Generated session</h4>

<div><a href="{session_url}">{session_url}</a></div>

<h4>Note IDs</h4>

<div style="font-family: monospace, monospace;">{note_ids}</div>

<h4>Study objective</h4>

{study_objective.label}

<h4>Question session criteria</h4>

<pre>
question_statuses: {[s.value for s in options.statuses]}
question_difficulties: {[d.value for d in options.difficulties]}
question_order: {options.order.value}
</pre>

<h4>Found questions</h4>

<div>Total: <code>{len(questions)}</code></div>
<div>Session size: <code>{options.count}</code></div>

<pre>
{json.dumps([{"id": q.id, "score": q.score, "preview": (q.preview_text[:48] + '...' if q.preview_text else '...')} for q in questions], indent=2)}
</pre>
"""
    anki_show_text(
        content,
        copyBtn=True,
        type="html",
        title="AMBOSS Qbank debug info",
        minWidth=600,
        minHeight=500,
        parent=parent,
    )
