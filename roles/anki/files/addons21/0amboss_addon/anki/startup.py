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

from typing import TYPE_CHECKING

from aqt.gui_hooks import profile_did_open

if TYPE_CHECKING:
    from aqt.main import AnkiQt

from .hooks import SimpleSingleShotHook
from .sync import is_auto_sync_enabled, sync_did_finish

# Guarantees execution after sync run if sync is enabled
anki_did_load_and_sync = SimpleSingleShotHook()


def setup_startup_hooks(main_window: "AnkiQt"):
    def on_profile_did_open():
        if is_auto_sync_enabled(main_window=main_window):
            sync_did_finish.append(anki_did_load_and_sync)
        else:
            anki_did_load_and_sync()

    profile_did_open.append(on_profile_did_open)
