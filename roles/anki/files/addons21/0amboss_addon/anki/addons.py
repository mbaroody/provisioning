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

from typing import TYPE_CHECKING, Any, Callable, List, Optional

from ..shared import safe_print
from .hooks import SimpleHook

our_addon_will_be_deleted = SimpleHook()
our_addon_will_be_disabled = SimpleHook()

if TYPE_CHECKING:
    from aqt.addons import AddonManager


def _addon_deletion_handler_factory(
    target_package_name: str,
) -> Callable[[Any, List[str]], None]:
    def fire_hook_if_addon_deleted(_, deleted_packages: List[str]):
        if target_package_name in deleted_packages:
            our_addon_will_be_deleted()

    return fire_hook_if_addon_deleted


def _addon_disabling_handler_factory(
    target_package_name: str,
) -> Callable[["AddonManager", str], None]:
    def fire_hook_if_addon_disabled(addon_manager: "AddonManager", package: str):
        if package != target_package_name:
            return

        try:
            enabled = addon_manager.isEnabled(package)
        except Exception:
            enabled = addon_manager.addon_meta(package).enabled

        if not enabled:
            our_addon_will_be_disabled()

    return fire_hook_if_addon_disabled


def hook_into_addon_manager_events(our_package_name: str):
    # Uninstall

    deletion_handler = _addon_deletion_handler_factory(
        target_package_name=our_package_name
    )

    try:  # 2.1.45+
        from aqt.gui_hooks import addons_dialog_will_delete_addons

        addons_dialog_will_delete_addons.append(deletion_handler)
    except (ImportError, ModuleNotFoundError):
        from anki.hooks import wrap
        from aqt.addons import AddonManager

        def on_delete_addon(_, package: str, *args, **kwargs):
            deletion_handler(None, [package])

        # NOTE: Execution order matters. Has to fire before!
        AddonManager.deleteAddon = wrap(  # type: ignore[assignment]
            AddonManager.deleteAddon, on_delete_addon, "before"
        )

    # Disabling

    # TODO: File PR to introduce hook

    disabling_handler = _addon_disabling_handler_factory(
        target_package_name=our_package_name
    )

    try:
        from anki.hooks import wrap
        from aqt.addons import AddonManager

        def on_toggle_enabled_addon(
            addon_manager: "AddonManager",
            package: str,
            *args,
            enable: Optional[bool] = None,
            **kwargs,
        ):
            disabling_handler(addon_manager, package)

        # NOTE: Execution order matters. Has to fire after!
        AddonManager.toggleEnabled = wrap(  # type: ignore[assignment]
            AddonManager.toggleEnabled, on_toggle_enabled_addon, "after"
        )

    except Exception as e:
        safe_print(f"Warning: Could not hook into AddonManager.toggleEnabled: {e}")
