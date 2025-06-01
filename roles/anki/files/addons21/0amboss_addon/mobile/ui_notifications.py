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

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ..debug import ErrorPromptFactory
from ..shared import _
from .snippet import ModificationType

if TYPE_CHECKING:
    from aqt.main import AnkiQt

from aqt.utils import askUser as anki_ask_user
from aqt.utils import showInfo as anki_show_info
from aqt.utils import tooltip as anki_tooltip


class MobileNotificationService:
    def __init__(self, main_window: "AnkiQt", error_prompt_factory: ErrorPromptFactory):
        self._main_window = main_window
        self._error_prompt_factory = error_prompt_factory

    def show_opt_in_prompt(self) -> bool:
        confirmed = anki_ask_user(
            _(
                """\
Hi there! You've been selected to participate in the AMBOSS mobile support beta test!

Would you like to enable AMBOSS tooltips for your mobile devices? \
To do so, the add-on will insert a small snippet into all of your card templates.

You can revert this change at any point by heading to \
AMBOSS → Options and removing the checkmark at "AMBOSS mobile support (beta)".

Would you like to proceed now?"""
            ),
            parent=self._main_window,
            title="AMBOSS",
            defaultno=True,
        )
        return confirmed

    def show_results_dialog(
        self,
        modification_type: ModificationType,
        skipped_notetype_names: List[str],
    ):
        warning_message_fragments: List[str] = []

        if skipped_notetype_names:
            warning_message_fragments.append(
                _(
                    "Please note that the add-on was unable process to the following"
                    " note types due to incompatible or invalid card templates:"
                )
            )
            warning_message_fragments.append(
                "\n".join(f"    {name}" for name in skipped_notetype_names)
            )

            if modification_type == ModificationType.SNIPPET_INSERTED:
                warning_message_fragments.append(
                    _(
                        "However, mobile support should work fine for all other note"
                        " types."
                    )
                )
            else:
                warning_message_fragments.append(
                    _(
                        "In the unlikely event that mobile support is still active for"
                        " these note types, please feel free to manually edit the card"
                        " templates and remove the AMBOSS snippet at the end of each"
                        " card side."
                    )
                )

        warning_message = (
            ("(" + "\n\n".join(warning_message_fragments) + ")")
            if warning_message_fragments
            else ""
        )

        if modification_type == ModificationType.SNIPPET_INSERTED:
            success_statement = _("AMBOSS mobile support enabled!")
            extra = ""
        else:
            success_statement = _("AMBOSS mobile support disabled.")
            extra = "You can enable it again through the AMBOSS add-on settings."

        message_body = (
            success_statement if not extra else f"{success_statement}\n\n{extra}"
        )

        sync_instructions = _(
            "Please sync your mobile devices with AnkiWeb to see the changes."
        )

        message = "\n\n".join((message_body, sync_instructions, warning_message))

        anki_show_info(
            message,
            title=success_statement,
            parent=self._main_window,
        )

    def show_error_dialog(
        self,
        message: str,
        title: str,
        exception: Exception,
        debug_data: Optional[Dict[str, Any]] = None,
    ):
        self._error_prompt_factory.create_and_exec(
            exception=exception,
            window_title=title,
            message_heading=title,
            message_body=message,
            extra_debug_data=debug_data,
        )

    def show_anki_tooltip(
        self, message: str, lifetime_milliseconds: int = 3000, parent: Any = None
    ):
        anki_tooltip(
            msg=message,
            period=lifetime_milliseconds,
            parent=parent or self._main_window,
            x_offset=20,
            y_offset=120,
        )
