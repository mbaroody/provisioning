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

from typing import TYPE_CHECKING, Callable, Optional

from ..anki.errors import IMPORT_ERRORS

try:
    # Anki 2.1.45+
    from aqt.browser.sidebar.item import SidebarItemType
except IMPORT_ERRORS:
    SidebarItemType = None  # type: ignore
from aqt.qt import QCursor, QMenu, QPushButton, Qt, QWidget

from ..activity import ActivityService
from ..anki.cardbrowser import (
    get_all_note_ids,
    get_selected_note_ids,
    get_table_length,
    get_table_selection_length,
    is_notes_mode,
)
from ..anki.utils import anki_open_link, anki_show_warning
from ..shared import _, safe_print
from ..theme import ThemeManager
from ..user import UserService
from .icons import get_amboss_qicon
from .performance import (
    EventSubmitter,
    RequestOrigin,
    browser_qbank_button_clicked,
    browser_qbank_context_menu_clicked,
    generate_request_id,
)
from .selection import QBankSelectionUIFactory, QuestionSelectionOptions
from .styles import style_button_primary

if TYPE_CHECKING:
    from aqt.browser.sidebar.item import SidebarItem
    from aqt.browser.browser import Browser

from ..anki.cardbrowser import (
    ButtonFactory,
    SelectionListener,
    SidebarContextMenuVisitor,
)


class QBankButton(QPushButton):

    def __init__(
        self,
        item_label_getter: Callable[[int], str],
        initial_count: int = 0,
        night_mode: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._item_label_getter = item_label_getter
        self._icon_active = get_amboss_qicon("logo_mono.svg")
        self._icon_disabled = get_amboss_qicon("logo_mono_disabled.svg")
        self.setStyleSheet(style_button_primary)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.set_item_count(item_count=initial_count)
        self.setProperty("night_mode", str(night_mode))

    def setText(self, text: str) -> None:
        # hack: create padding to icon via nbsp
        return super().setText("\u2002" + text)

    def set_item_count(self, item_count: int):
        cta_text = _("Start Qbank session")
        if item_count == 0:
            self.setText(cta_text)
            self.setIcon(self._icon_disabled)
            self.setEnabled(False)
        else:
            self.setText(
                f"{cta_text} ({item_count} {self._item_label_getter(item_count)})"
            )
            self.setIcon(self._icon_active)
            self.setEnabled(True)
        self.update()


def get_item_label(browser: "Browser", item_count: int) -> str:
    if is_notes_mode(browser):
        return _("note") if item_count == 1 else _("notes")
    else:
        return _("card") if item_count == 1 else _("cards")


class QBankContextMenuProvider(SidebarContextMenuVisitor):
    def __init__(
        self,
        qbank_selection_ui_factory: QBankSelectionUIFactory,
        max_note_count: int,
        user_service: UserService,
        activity_service: ActivityService,
    ):
        self._qbank_selection_ui_factory = qbank_selection_ui_factory
        self._max_note_count = max_note_count
        self._user_service = user_service
        self._activity_service = activity_service

    def visit(self, menu: QMenu, item: "SidebarItem", browser: "Browser"):
        if SidebarItemType is None:
            safe_print("Warning: SidebarItemType is None")
            return
        if item.item_type != SidebarItemType.TAG:
            return
        menu.addSeparator()
        action = menu.addAction(_("Start AMBOSS Qbank session"))
        action.setIcon(get_amboss_qicon("logo.svg"))

        def start_qbank_session():
            if not check_login_state_and_maybe_warn(
                user_service=self._user_service, parent=browser
            ):
                return

            tag = item.full_name
            query = f"tag:{tag}"

            if len(tag) > 32:
                tag = tag.split("::")[-1][:32]

            event_submitter = EventSubmitter(
                request_id=generate_request_id(),
                request_origin=RequestOrigin.anki_card_browser_sidebar_menu,
                activity_service=self._activity_service,
            )

            event_submitter(
                browser_qbank_context_menu_clicked(
                    query=query,
                )
            )

            dialog, ui_service = self._qbank_selection_ui_factory.create_selection_ui(
                question_options=QuestionSelectionOptions(),
                context=f"Tag: {tag}",
                max_note_count=self._max_note_count,
                parent=browser,
                web_browser=anki_open_link,
                event_submitter=event_submitter,
            )

            dialog.set_note_query(query=query)
            dialog.show()

        action.triggered.connect(start_qbank_session)


class QBankButtonFactory(ButtonFactory):
    def __init__(
        self,
        qbank_selection_ui_factory: QBankSelectionUIFactory,
        max_note_count: int,
        user_service: UserService,
        activity_service: ActivityService,
        theme_manager: ThemeManager,
    ):
        self._qbank_selection_ui_factory = qbank_selection_ui_factory
        self._max_note_count = max_note_count
        self._user_service = user_service
        self._activity_service = activity_service
        self._theme_manager = theme_manager

    def create_button(self, browser: "Browser") -> QPushButton:
        def item_label_getter(item_count: int) -> str:
            return get_item_label(browser=browser, item_count=item_count)

        button = QBankButton(
            initial_count=0,
            item_label_getter=item_label_getter,
            night_mode=self._theme_manager.night_mode,
            parent=browser,
        )
        setattr(browser, "amboss_qbank_button", button)

        def start_qbank_session():
            if not check_login_state_and_maybe_warn(
                user_service=self._user_service, parent=browser
            ):
                return

            if should_consider_selection(browser):
                considered_note_ids = get_selected_note_ids(browser)
            else:
                considered_note_ids = get_all_note_ids(browser)

            try:
                query = browser.current_search()
            except AttributeError:
                query = browser.form.searchEdit.lineEdit().text()

            event_submitter = EventSubmitter(
                request_id=generate_request_id(),
                request_origin=RequestOrigin.anki_card_browser_toolbar_button,
                activity_service=self._activity_service,
            )

            event_submitter(
                browser_qbank_button_clicked(
                    query=query,
                    is_notes_mode=is_notes_mode(browser),
                    length_rows=get_table_length(browser),
                    length_selected=get_table_selection_length(browser),
                )
            )

            (
                dialog,
                ui_service,
            ) = self._qbank_selection_ui_factory.create_selection_ui(
                question_options=QuestionSelectionOptions(),
                context=_("{} selected Anki notes".format(len(considered_note_ids))),
                max_note_count=self._max_note_count,
                parent=browser,
                web_browser=anki_open_link,
                event_submitter=event_submitter,
            )

            dialog.set_note_ids(note_ids=list(considered_note_ids))
            dialog.show()

        button.clicked.connect(start_qbank_session)

        return button


class QBankSelectionListener(SelectionListener):
    def listen(self, browser: "Browser"):
        qbank_button: Optional[QBankButton] = getattr(
            browser, "amboss_qbank_button", None
        )
        if qbank_button is None:
            return

        if should_consider_selection(browser):
            considered_item_count = get_table_selection_length(browser)
        else:
            considered_item_count = get_table_length(browser)

        qbank_button.set_item_count(considered_item_count)


def check_login_state_and_maybe_warn(
    user_service: UserService, parent: QWidget
) -> bool:
    if user_service.is_logged_in():
        return True
    anki_show_warning(
        _(
            "To start a Qbank session, please first log in to AMBOSS from the 'AMBOSS'"
            " menu on Anki's home screen."
        ),
        title=_("AMBOSS: Please login"),
        parent=parent,
    )
    return False


def should_consider_selection(browser: "Browser") -> bool:
    return get_table_selection_length(browser) > 1
