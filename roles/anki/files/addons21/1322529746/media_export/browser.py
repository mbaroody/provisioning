from typing import Any, List, Optional, Tuple

import aqt
from aqt import mw, tr
from aqt.browser import Browser
from aqt.gui_hooks import browser_will_show_context_menu
from aqt.qt import *
from aqt.utils import disable_help_button, showInfo

from .exporter import NoteMediaExporter
from .utils import export_media


def export_media_from_selected_notes(browser: Browser) -> None:
    selected_nids = browser.selected_notes()
    mid = mw.col.get_note(selected_nids[0]).mid
    if any(mw.col.get_note(nid).mid != mid for nid in selected_nids):
        showInfo("Please select notes of the same note type.", parent=browser)
        return

    model = mw.col.models.get(mid)
    field_names = [x["name"] for x in model["flds"]]

    # remove AnkiHub ID field
    field_names = [x for x in field_names if x != "ankihub_id"]

    selected_field_names, cancelled = choose_multiple_from_list(
        "Choose fields to export media from", field_names, parent=browser
    )

    if cancelled:
        return

    if not selected_field_names:
        showInfo("No fields selected.", parent=browser)
        return

    notes = [mw.col.get_note(nid) for nid in selected_nids]
    exporter = NoteMediaExporter(
        col=mw.col,
        notes=notes,
        fields=selected_field_names,
    )
    export_media(exporter=exporter)


def choose_multiple_from_list(
    prompt: str, choices: list[str], parent: Any = None
) -> Tuple[List[str], bool]:
    if not parent:
        parent = aqt.mw.app.activeWindow()
    d = QDialog(parent)
    disable_help_button(d)
    d.setWindowModality(Qt.WindowModality.WindowModal)
    l = QVBoxLayout()
    d.setLayout(l)
    t = QLabel(prompt)
    l.addWidget(t)
    list_widget = QListWidget()
    list_widget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
    list_widget.addItems(choices)
    l.addWidget(list_widget)
    bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
    qconnect(bb.accepted, d.accept)
    l.addWidget(bb)

    cancelled = False
    dialog_code = d.exec()
    if dialog_code != QDialog.DialogCode.Accepted:
        cancelled = True

    return [x.text() for x in list_widget.selectedItems()], cancelled


def on_browser_will_show_context_menu(browser: Browser, context_menu: QMenu) -> None:
    if browser.table.is_notes_mode():
        menu = context_menu
    else:
        notes_submenu: Optional[QMenu] = next(
            (
                menu  # type: ignore
                for menu in context_menu.findChildren(QMenu)
                if menu.title() == tr.qt_accel_notes()  # type: ignore
            ),
            None,
        )
        if notes_submenu is None:
            return
        menu = notes_submenu

    menu.addSeparator()
    menu.addAction(
        "Export Media",
        lambda: export_media_from_selected_notes(browser),
    )


def setup_browser() -> None:
    browser_will_show_context_menu.append(on_browser_will_show_context_menu)
