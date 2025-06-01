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

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, Sequence

from anki.utils import ids2str

from .errors import IMPORT_ERRORS

try:
    from aqt.gui_hooks import browser_sidebar_will_show_context_menu  # 2.1.45+
except IMPORT_ERRORS:
    browser_sidebar_will_show_context_menu = None  # type: ignore # noqa: F401

from aqt.gui_hooks import browser_did_change_row, browser_will_show
from aqt.qt import QMenu, QModelIndex, QPushButton

from ..debug import QBANK_DEBUG_ACTIVE

if TYPE_CHECKING:
    from aqt.browser.browser import Browser
    from aqt.browser.sidebar.item import SidebarItem
    from aqt.browser.sidebar.tree import SidebarTreeView


class SidebarContextMenuVisitor(ABC):
    @abstractmethod
    def visit(self, menu: QMenu, item: "SidebarItem", browser: "Browser"):
        pass


class ButtonFactory(ABC):
    @abstractmethod
    def create_button(self, browser: "Browser") -> QPushButton:
        pass


class SelectionListener(ABC):
    @abstractmethod
    def listen(self, browser: "Browser"):
        pass


class SidebarContextMenuExtender:
    def __init__(self, context_menu_visitor: SidebarContextMenuVisitor):
        self._context_menu_visitor = context_menu_visitor

    def maybe_extend_context_menu(
        self,
        sidebar: "SidebarTreeView",
        menu: QMenu,
        item: "SidebarItem",
        index: QModelIndex,
    ):
        self._context_menu_visitor.visit(menu=menu, item=item, browser=sidebar.browser)


class SearchLayoutExtender:
    def __init__(self, button_factory: ButtonFactory):
        self._button_factory = button_factory

    def extend_search_layout(self, browser: "Browser"):
        button = self._button_factory.create_button(browser)
        layout = browser.form.gridLayout
        layout.addWidget(button, 0, layout.columnCount() + 1)


class CardBrowserPatcher:
    def __init__(
        self,
        sidebar_context_menu_extender: Optional[SidebarContextMenuExtender],
        search_layout_extender: SearchLayoutExtender,
        selection_listener: SelectionListener,
    ):
        self._sidebar_context_menu_extender = sidebar_context_menu_extender
        self._search_layout_extender = search_layout_extender
        self._selection_listener = selection_listener

    def patch(self):
        if (
            browser_sidebar_will_show_context_menu is not None
            and self._sidebar_context_menu_extender is not None
        ):
            browser_sidebar_will_show_context_menu.append(
                self._sidebar_context_menu_extender.maybe_extend_context_menu
            )
        browser_will_show.append(self._search_layout_extender.extend_search_layout)
        browser_did_change_row.append(self._selection_listener.listen)

        if not QBANK_DEBUG_ACTIVE:  # FIXME: temporary
            return

        from aqt.gui_hooks import browser_will_show_context_menu
        from aqt.qt import QApplication
        from aqt.utils import tooltip

        def extend_browser_context_menu(browser: "Browser", menu: QMenu):
            def copy_note_property(property: str):
                if (card := browser.card) is None or (note := card.note()) is None:
                    return
                value = getattr(note, property, None)
                if value is None:
                    tooltip(f"Could not get {property} for note")
                    return
                QApplication.clipboard().setText(str(value))
                tooltip(f"Copied {value} to clipboard")

            action = menu.addAction("Copy NID")
            action.triggered.connect(lambda: copy_note_property(property="id"))
            action = menu.addAction("Copy GUID")
            action.triggered.connect(lambda: copy_note_property(property="guid"))

        browser_will_show_context_menu.append(extend_browser_context_menu)


def get_all_note_ids(browser: "Browser") -> Sequence[int]:
    # FIXME: Extend Anki browser API to avoid private properties access
    try:
        return browser.table._state.get_note_ids(browser.table._model._items)  # 2.1.45+
    except Exception:
        database = browser.col.db
        card_ids = browser.model.cards  # type: ignore[attr-defined]
        if database is None or not card_ids:
            return []
        return database.list(
            f"""select distinct nid from cards where id in {ids2str(card_ids)}"""
        )


def get_selected_note_ids(browser: "Browser") -> Sequence[int]:
    try:
        return browser.selected_notes()  # 2.1.45+
    except Exception:
        return browser.selectedNotes()


# Determining note ids for table rows is expensive, so we use dedicated
# APIs for determining lengths rather than e.g. just returning len(get_all_note_ids()):


def get_table_selection_length(browser: "Browser") -> int:
    try:
        return browser.table.len_selection()
    except Exception:
        return len(browser.selectedCards())


def get_table_length(browser: "Browser") -> int:
    try:
        return browser.table.len()  # 2.1.45+
    except Exception:
        return len(browser.model.cards)  # type: ignore[attr-defined]


def is_notes_mode(browser: "Browser") -> bool:
    try:
        return browser.table.is_notes_mode()
    except Exception:
        return False
