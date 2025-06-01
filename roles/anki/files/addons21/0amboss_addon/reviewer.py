# AMBOSS Anki Add-on
#
# Copyright (C) 2019-2020 AMBOSS MD Inc. <https://www.amboss.com/us>
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


"""
Modifies Reviewer by injecting HTML and hijacking handlers.
"""
import json
from collections import OrderedDict
from enum import Enum
from typing import TYPE_CHECKING, Callable, List, Optional, Tuple, Union

import decorator
from aqt.qt import QThreadPool
from aqt.utils import tooltip as anki_tooltip
from urllib3.exceptions import HTTPError, ProtocolError, ProxyError

from .activity import ActivityService
from .config import AddonConfig, DisplaySettingName
from .debug import (
    ErrorCounter,
    ErrorCounterOverflowException,
    ErrorPromptFactory,
)
from .hooks import reviewer_did_show_answer, reviewer_did_show_question
from .network import TIMEOUT_ERRORS
from .phrases import PhraseFinder
from .qthreading import Worker
from .shared import _, safe_print
from .tooltip import TooltipRenderResult, TooltipRenderService

if TYPE_CHECKING:
    from aqt.reviewer import Reviewer

    try:  # 2.1.45+
        from anki.scheduler.v1 import Scheduler as SchedulerV1
        from anki.scheduler.v2 import Scheduler as SchedulerV2
        from anki.scheduler.v3 import Scheduler as SchedulerV3
    except (ImportError, ModuleNotFoundError):
        from anki.sched import Scheduler as SchedulerV1  # type: ignore[import,no-redef]
        from anki.schedv2 import (  # type: ignore[import,no-redef]
            Scheduler as SchedulerV2,
        )


class SchedulerAPIError(Exception):
    pass


class ReviewerState(Enum):
    QUESTION = "question"
    ANSWER = "answer"


class MainWindowState(Enum):
    REVIEW = "review"


def wrap(old: Callable, new: Callable, self):
    # TODO?:
    #  - put into a class, maybe as callable, at least don't assume argument name _old
    #  - replace completely by native anki.hooks.wrap
    """Override an existing method."""

    def decorator_wrapper(f: Callable, *args, **kwargs):
        return new(self, _old=old, *args, **kwargs)

    return decorator.decorator(decorator_wrapper)(old)


class ReviewerStyler:
    def __init__(self, addon_config: AddonConfig):
        self._addon_config = addon_config

    def get_highlights_style(self) -> str:
        color = self._addon_config["styleColorHighlights"]
        return f"span.amboss-marker {{ border-bottom-color: {color}; }}"


def _is_reviewer_in_review_state(reviewer: "Reviewer") -> bool:
    return (
        reviewer is not None
        and reviewer.mw.state == MainWindowState.REVIEW.value
        and reviewer.state in (ReviewerState.QUESTION.value, ReviewerState.ANSWER.value)
    )


class ReviewerErrorHandler:
    _proxy_error_types = (ProxyError,)
    _connection_error_types = (ConnectionError, ProtocolError)
    _generic_errors = (HTTPError, Exception)

    def __init__(
        self,
        error_prompt_factory: ErrorPromptFactory,
        proxy_error_counter: ErrorCounter,
        connection_error_counter: ErrorCounter,
        timeout_error_counter: ErrorCounter,
        error_lifetime: int,
    ):
        self._error_prompt_factory = error_prompt_factory
        self._proxy_error_counter = proxy_error_counter
        self._connection_error_counter = connection_error_counter
        self._timeout_error_counter = timeout_error_counter
        self._error_lifetime = error_lifetime

    def __call__(self, exception: Exception):
        try:
            raise exception
        except self._proxy_error_types as e:
            try:
                self._connection_error_counter.increase()
            except ErrorCounterOverflowException:
                self._error_prompt_factory.create_and_exec(
                    exception=e,
                    message_heading=_(
                        "Encountered an error while trying to connect to AMBOSS"
                    ),
                    window_title=_("AMBOSS - Connection Error"),
                )
        except self._connection_error_types:
            try:
                self._connection_error_counter.increase()
            except ErrorCounterOverflowException:
                anki_tooltip(_("Could not connect to AMBOSS."), self._error_lifetime)
        # Most SSL errors seems to be related to timeout, treat them as such.
        except TIMEOUT_ERRORS:
            try:
                self._timeout_error_counter.increase()
            except ErrorCounterOverflowException:
                anki_tooltip(_("Could not connect to AMBOSS."), self._error_lifetime)
        except self._generic_errors as e:
            self._error_prompt_factory.create_and_exec(exception=e)


class ReviewerScheduleService:
    _fetch_limit = 3

    def __init__(self, reviewer: "Reviewer"):
        self._reviewer = reviewer

    def get_upcoming_card_ids(self) -> List[int]:
        if self._reviewer.mw.col is None:
            return []

        scheduler = self._reviewer.mw.col.sched

        # As of Anki 2.1.45, Anki ships with three different schedulers, the legacy
        # scheduler, current scheduler, and a newly introduced experimental variant
        # that moves most of the logic to Rust. In this last iteration, querying
        # upcoming cards is now possible via a proper API. However, to maintain
        # compatibility with older versions of Anki and with newer versions that are
        # still running an earlier scheduler, we need to also support the old
        # approach of manually inspecting the scheduler's card queues.
        # See also. https://github.com/ankitects/anki/tree/main/pylib/anki/scheduler

        # version property is available on 2.1.45+
        if (
            hasattr(scheduler, "version")
            and scheduler.version >= 3  # type: ignore[attr-defined]
        ):
            card_fetcher = self._get_upcoming_card_ids_v3
        else:
            card_fetcher = self._get_upcoming_card_ids_v1_v2  # type: ignore[assignment]

        try:
            card_ids = card_fetcher(scheduler=scheduler)  # type: ignore[arg-type]
        except SchedulerAPIError as e:
            safe_print(e)
            card_ids = []

        return card_ids

    def _get_upcoming_card_ids_v1_v2(
        self, scheduler: Union["SchedulerV1", "SchedulerV2"]
    ) -> List[int]:
        """Fetch upcoming cards by looking at SchedulerV1/V2 card queues"""
        if not hasattr(scheduler, "_haveQueues"):
            raise SchedulerAPIError("Could not access V1/V2 card queues")

        if not scheduler._haveQueues:
            return []

        # There is no clear-cut queue of upcoming cards because the scheduler
        # draws up the next card on demand. So instead we iterate through
        # all individual queues and pick one candidate each

        cids: List[int] = []
        lrnQueue = getattr(scheduler, "_lrnQueue", None)

        if lrnQueue:
            cids.append(lrnQueue[0][1])  # heap of tuples (due, cid)

        for queue_name in ("_lrnDayQueue", "_revQueue", "_newQueue"):
            # misnomer: these are actually stacks of cids
            queue = getattr(scheduler, queue_name, None)
            if not queue:
                continue
            try:
                cids.append(queue[-1])
            except IndexError:
                continue

        return cids

    def _get_upcoming_card_ids_v3(self, scheduler: "SchedulerV3") -> List[int]:
        """Fetch upcoming cards using SchedulerV3 API"""
        if not hasattr(scheduler, "get_queued_cards"):
            raise SchedulerAPIError("Could not access V3 card queue")

        queued_cards = scheduler.get_queued_cards(fetch_limit=self._fetch_limit)

        if not queued_cards:
            return []

        cids = [c.card.id for c in queued_cards.cards]

        return cids


class ReviewerCardPhraseUpdater:
    """Updates card DOM with new phrase markers on reviewer changes."""

    def __init__(
        self,
        reviewer: "Reviewer",
        phrase_finder: PhraseFinder,
        schedule_service: ReviewerScheduleService,
        thread_pool: QThreadPool,
        error_handler: ReviewerErrorHandler,
        addon_config: AddonConfig,
        reviewer_styler: ReviewerStyler,
        activity_service: ActivityService,
    ):
        self._reviewer = reviewer
        self._phrase_finder = phrase_finder
        self._schedule_service = schedule_service
        self._thread_pool = thread_pool
        self._error_handler = error_handler
        self._addon_config = addon_config
        self._reviewer_styler = reviewer_styler
        self._activity_service = activity_service

        self._addon_config.signals.saved.connect(self._on_addon_config_saved)

    def register_hooks(self):
        """Adds user hooks triggered when question or answer is shown."""
        # TODO?: Consider refreshing highlights on login state change. Make sure reviewer web view is available.
        reviewer_did_show_question.append(self._on_card_updated)
        reviewer_did_show_answer.append(self._on_card_updated)

    def _on_addon_config_saved(self):
        self._toggle_highlights(self._should_enable_highlights())
        self._refresh_highlights()

    def _on_card_updated(self, *args):  # new-style hooks pass card object, old don't
        """Fires when card content is updated and marks found phrases."""
        if not self._should_enable_highlights():
            return
        if not self._reviewer.card:
            return

        self._dispatch_worker(
            self._reviewer.card.note(), self._find_phrase_pairs, self._mark_phrases
        )
        # cache upcoming notes, one out of each queue
        for card_id in self._schedule_service.get_upcoming_card_ids():
            try:
                card = self._reviewer.mw.col.get_card(card_id)  # type: ignore
            except AttributeError:
                card = self._reviewer.mw.col.getCard(card_id)  # type: ignore
            note = card.note()
            self._dispatch_worker(note, self._cache_phrase_pairs)

    def _dispatch_worker(
        self,
        note,
        worker_callback: Callable,
        result_callback: Optional[Callable] = None,
    ):
        worker = Worker(
            worker_callback,
            tuple(field.strip() for field in note.fields if field.strip()),
            note.guid,
        )
        if result_callback:
            worker.signals.result.connect(result_callback)
        worker.signals.error.connect(self._error_handler)
        self._thread_pool.start(worker)

    def _cache_phrase_pairs(self, fields: Tuple[str], guid: Optional[str]):
        # relies on get_phrases lru_cache
        self._phrase_finder.get_phrases(fields, guid)

    def _find_phrase_pairs(self, fields: Tuple[str], guid: Optional[str]) -> dict:
        phrases = self._phrase_finder.get_phrases(fields, guid)
        phrase_pairs = {
            term: phrase.group_id
            for term, phrase in phrases.items()
            if phrase is not None
        }
        return phrase_pairs

    def _mark_phrases(self, phrase_pairs: dict, canceled: bool):
        if canceled or not _is_reviewer_in_review_state(self._reviewer):
            return
        self._reviewer.web.eval(
            f"ambossAddon.tooltip.phraseMarker.mark({json.dumps(self._sort(phrase_pairs))})"
        )

    def _should_enable_highlights(self) -> bool:
        if not self._addon_config.get(DisplaySettingName.ENABLE_GENERAL.value):
            return False
        return (self._reviewer.state == ReviewerState.ANSWER.value) or (
            self._reviewer.state == ReviewerState.QUESTION.value
            and self._addon_config.get(DisplaySettingName.ENABLE_QUESTION.value, False)
        )

    def _toggle_highlights(self, state: bool):
        if not _is_reviewer_in_review_state(self._reviewer):
            return
        if not state:
            self._reviewer.web.eval(
                "ambossAddon.tooltip.phraseMarker.hideAll();"
                " ambossAddon.tooltip.tooltips.hideAll();"
            )
        else:
            self._on_card_updated()

    def _refresh_highlights(self):
        if not _is_reviewer_in_review_state(self._reviewer):
            return
        self._reviewer.web.eval("ambossAddon.tooltip.phraseMarker.hideAll();")
        self._reviewer.web.eval(
            f"ambossAddon.tooltip.setCSS({json.dumps(self._reviewer_styler.get_highlights_style())});"
        )
        self._on_card_updated()

    def _sort(self, phrase_pairs: dict) -> OrderedDict:
        """Order phrase pairs by descending phrase key length."""
        return OrderedDict(sorted(phrase_pairs.items(), key=lambda k: -len(k[0])))


class ReviewerTooltipUpdater:
    """Updates tippy tooltips with new tooltip content"""

    def __init__(
        self,
        reviewer: "Reviewer",
        tooltip_render_service: TooltipRenderService,
        thread_pool: QThreadPool,
        error_handler: ReviewerErrorHandler,
    ):
        self._reviewer = reviewer
        self._tooltip_service = tooltip_render_service
        self._thread_pool = thread_pool
        self._error_handler = error_handler
        self._worker: Optional[Worker] = None

    def update_tooltip(self, tippy_data: dict):
        phrase_group_id = tippy_data["phraseId"]
        found_term = tippy_data["term"]
        mark_id = tippy_data["markId"]
        self._worker = Worker(self._render_tooltip, phrase_group_id, found_term)
        self._worker.signals.result.connect(
            lambda t, c: self._update_tooltip(mark_id, t, c)
        )
        self._worker.signals.error.connect(self._error_handler)
        self._thread_pool.start(self._worker)

    def _render_tooltip(self, phrase_group_id, found_term) -> TooltipRenderResult:
        return self._tooltip_service.render_tooltip(phrase_group_id, found_term)

    def _update_tooltip(self, mark_id, result: TooltipRenderResult, canceled):
        if not _is_reviewer_in_review_state(self._reviewer):
            return
        self._reviewer.web.eval(
            f"""ambossAddon.tooltip.tooltips.setContentFor(
{json.dumps(mark_id)}, {json.dumps(result.html)}, {json.dumps(result.has_media)})"""
        )
        self._reviewer.web.eval(
            f"""\
try {{
  ambossAddon.tooltip.tooltipShown(
    {json.dumps(result.phrase_group_id)},
    {json.dumps(result.term)},
    {json.dumps(result.access_limit)},
    {json.dumps(result.rate_limit._asdict() if result.rate_limit else None)}
  )
}} catch(error) {{
  console.error(error)
}}"""
        )


class ReviewerTooltipManagerAdapter:
    """Provides utility methods for interacting with the tooltip manager JS object"""

    def __init__(self, reviewer: "Reviewer"):
        self._reviewer = reviewer

    def open_next_tooltip(self):
        if not _is_reviewer_in_review_state(self._reviewer):
            return
        self._reviewer.web.eval("ambossAddon.tooltip.tooltips.rotateTooltips();")

    def open_previous_tooltip(self):
        if not _is_reviewer_in_review_state(self._reviewer):
            return
        self._reviewer.web.eval("ambossAddon.tooltip.tooltips.rotateTooltips(true);")

    def close_tooltips(self):
        if not _is_reviewer_in_review_state(self._reviewer):
            return
        self._reviewer.web.eval("ambossAddon.tooltip.tooltips.hideAll();")
