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

from typing import TYPE_CHECKING, Callable

from ..shared import safe_print
from .hooks import SimpleHook

if TYPE_CHECKING:
    from aqt.main import AnkiQt

sync_will_start = SimpleHook()
sync_did_finish = SimpleHook()


def _intercept_legacy_2126_sync(
    main_window: "AnkiQt", *, _old: Callable[["AnkiQt"], None]
):
    # collection is unloaded at this stage. load.
    if not main_window.loadCollection():
        # should loading fail, pass back to original handler
        return _old(main_window)
    sync_will_start()
    # unload again, pass back to original handler
    main_window.unloadCollection(lambda: _old(main_window))


def _signal_legacy_2126_sync_end(new_state: str, old_state: str):
    if old_state == "sync" and new_state != "sync":
        sync_did_finish()


def _intercept_legacy_2128_sync(
    main_window: "AnkiQt",
    after_sync: Callable[[], None],
    _old: Callable[["AnkiQt", Callable[[], None]], None],
):
    sync_will_start()

    def after_sync_wrapper():
        after_sync()
        sync_did_finish()

    return _old(main_window, after_sync_wrapper)


def hook_into_sync_system():
    try:  # 2.1.35+
        from aqt.gui_hooks import sync_did_finish as anki_sync_did_finish
        from aqt.gui_hooks import sync_will_start as anki_sync_will_start

        anki_sync_will_start.append(sync_will_start)
        anki_sync_did_finish.append(sync_did_finish)
    except (ImportError, ModuleNotFoundError):
        from anki.hooks import wrap
        from aqt.main import AnkiQt

        if hasattr(AnkiQt, "_sync_collection_and_media"):  # 2.1.28+
            AnkiQt._sync_collection_and_media = wrap(
                AnkiQt._sync_collection_and_media, _intercept_legacy_2128_sync, "around"
            )
        else:
            AnkiQt._sync = wrap(AnkiQt._sync, _intercept_legacy_2126_sync, "around")
            from aqt.gui_hooks import state_did_change

            state_did_change.append(_signal_legacy_2126_sync_end)


def is_auto_sync_enabled(main_window: "AnkiQt") -> bool:
    try:  # 2.1.28+
        return main_window.can_auto_sync()
    except AttributeError:
        return not (
            not main_window.pm.profile["syncKey"]  # type: ignore
            or not main_window.pm.profile["autoSync"]  # type: ignore
            or main_window.safeMode
            or main_window.restoringBackup
        )


def do_sync(main_window: "AnkiQt"):
    """Trigger interactive sync with AnkiWeb. Fail if corresponding API could
    not be called."""
    try:  # 2.1.28
        main_window.on_sync_button_clicked()
    except AttributeError:
        main_window.onSync()
    except Exception:
        safe_print("Could not trigger Anki sync")
