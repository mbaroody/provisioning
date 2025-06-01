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

from typing import Callable, Optional, Tuple

from ..shared import safe_print
from .hooks import SimpleHook

cards_will_be_exported = SimpleHook()
cards_did_export = SimpleHook()

# TODO: Improve type annotations for new hooks once dev target is 2.1.54+


def exporter_hook_handler_factory(
    downstream_hook: SimpleHook,
    trigger_for_exporters: Tuple[type, ...],
) -> Callable[[type, type], type]:
    def fire_hook_if_exporter_matches(export_options: type, exporter: type) -> type:
        # need to always return export_options as this is a filter hook
        if isinstance(exporter, trigger_for_exporters):
            downstream_hook()
        return export_options

    return fire_hook_if_exporter_matches


def legacy_exporter_hook_handler_factory(
    downstream_hook: SimpleHook,
    trigger_for_exporters: Tuple[type, ...],
) -> Callable[[type], None]:
    def fire_hook_if_exporter_matches(exporter: type) -> None:
        if isinstance(exporter, trigger_for_exporters):
            downstream_hook()

    return fire_hook_if_exporter_matches


def hook_into_anki_exporters():
    # NOTE: There is a small unavoidable support gap in that the new export system
    # is not supported on Anki 2.1.52-2.1.54. As enabling the new system on these
    # versions required either manually running a debug command, or toggling a
    # setting in Anki's preferences, the affected user group is likely tiny
    # to non-existent, so no further action is needed.

    try:  # 2.1.55+, new exporters enabled by default

        # New-style exporters

        from aqt.gui_hooks import (
            exporter_did_export,  # pyright: ignore[reportGeneralTypeIssues]
            exporter_will_export,  # pyright: ignore[reportGeneralTypeIssues]
        )

        from aqt.import_export.exporting import (  # type: ignore
            ApkgExporter,
            CardCsvExporter,
            ColpkgExporter,
        )

        supported_exporters = (ColpkgExporter, ApkgExporter, CardCsvExporter)

        exporter_will_export_handler = exporter_hook_handler_factory(
            downstream_hook=cards_will_be_exported,
            trigger_for_exporters=supported_exporters,
        )
        exporter_did_export_handler = exporter_hook_handler_factory(
            downstream_hook=cards_did_export, trigger_for_exporters=supported_exporters
        )

        exporter_will_export.append(exporter_will_export_handler)
        exporter_did_export.append(exporter_did_export_handler)

        # Legacy exporters

        from aqt.gui_hooks import (
            legacy_exporter_will_export,  # pyright: ignore[reportGeneralTypeIssues]
            legacy_exporter_did_export,  # pyright: ignore[reportGeneralTypeIssues]
        )

        from anki.exporting import AnkiExporter, TextCardExporter

        supported_legacy_exporters = (AnkiExporter, TextCardExporter)

        legacy_exporter_will_export_handler = legacy_exporter_hook_handler_factory(
            downstream_hook=cards_will_be_exported,
            trigger_for_exporters=supported_legacy_exporters,
        )
        legacy_exporter_did_export_handler = legacy_exporter_hook_handler_factory(
            downstream_hook=cards_did_export,
            trigger_for_exporters=supported_legacy_exporters,
        )

        legacy_exporter_will_export.append(legacy_exporter_will_export_handler)
        legacy_exporter_did_export.append(legacy_exporter_did_export_handler)

    except (ImportError, ModuleNotFoundError):
        _legacy_hook_into_anki_exporters()


def _legacy_hook_into_anki_exporters():
    from anki.hooks import wrap

    try:
        # limit to exporters that a.) export templates, b.) are used to share decks
        from anki.exporting import AnkiExporter, TextCardExporter
    except (ImportError, ModuleNotFoundError):
        safe_print("Warning: Could not import Anki exporters. Aborting hook.")
        return

    entrypoint_method_name = "exportInto"

    for exporter in (
        AnkiExporter,
        TextCardExporter,
    ):
        export_into_method = getattr(exporter, entrypoint_method_name, None)
        if not export_into_method:
            safe_print(
                f"Warning: Could not find '{entrypoint_method_name}' for exporter"
                f" {exporter}"
            )
            continue
        setattr(
            exporter,
            entrypoint_method_name,
            wrap(export_into_method, _hook_calling_wrapper, "around"),
        )


def _hook_calling_wrapper(*args, _old: Optional[Callable] = None, **kwargs):
    cards_will_be_exported()
    ret = _old(*args, **kwargs) if _old else None
    cards_did_export()
    return ret
