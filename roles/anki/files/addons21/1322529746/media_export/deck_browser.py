from concurrent.futures import Future

from anki.decks import DeckId
from aqt import gui_hooks, mw
from aqt.qt import QMenu, qconnect
from aqt.utils import showInfo, tooltip

from .exporter import DeckMediaExporter
from .pathlike.errors import PathLikeError
from .utils import export_media, get_gdrive_files_in_background


def setup_basic_export(menu: QMenu, did: int) -> None:
    exporter = DeckMediaExporter(mw.col, DeckId(did))
    action = menu.addAction("Export Media")
    qconnect(action.triggered, lambda: export_media(exporter=exporter))


def setup_advanced_export(menu: QMenu, did: int) -> None:
    def on_done(future: Future) -> None:
        try:
            file_names_in_gdrive, want_cancel = future.result()
        except PathLikeError as e:
            showInfo(str(e))
            return

        if want_cancel:
            tooltip("Cancelled Media Export.")
            return

        exporter = DeckMediaExporter(
            mw.col, DeckId(did), exclude_files=file_names_in_gdrive
        )
        export_media(exporter=exporter)

    action = menu.addAction("Export Media (exclude files in GDrive)")
    qconnect(action.triggered, lambda: get_gdrive_files_in_background(on_done=on_done))


def on_deck_browser_will_show_options_menu(menu: QMenu, did: int) -> None:
    """Adds a menu item under the gears icon to export a deck's media files."""

    setup_basic_export(menu, did)

    setup_advanced_export(menu, did)


def setup_deck_browser() -> None:
    gui_hooks.deck_browser_will_show_options_menu.append(
        on_deck_browser_will_show_options_menu
    )
