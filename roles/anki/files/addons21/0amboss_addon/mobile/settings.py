# AMBOSS Anki Add-on
#
# Copyright (C) 2019-2023 AMBOSS MD Inc. <https://www.amboss.com/us>
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

from typing import MutableMapping, cast

from aqt.qt import QCheckBox

from ..settings import ExtensibleDialog, SettingsExtension
from ..shared import _
from .config import MobileSettingName


class MobileSettingsExtension(SettingsExtension):
    _enable_mobile_support_name = "enable_mobile_support"

    def on_dialog_init(self, dialog: ExtensibleDialog):
        mobile_support_checkbox = QCheckBox(_("Enable mobile support"))
        dialog.add_extension_widget(
            object_name=self._enable_mobile_support_name,
            widget=mobile_support_checkbox,
        )

    def on_load_config(
        self,
        dialog: ExtensibleDialog,
        config: MutableMapping,
        logged_in: bool,
        article_access: bool,
    ):
        mobile_support_checkbox = cast(
            QCheckBox,
            dialog.get_extension_widget(self._enable_mobile_support_name),
        )
        if not logged_in or not article_access:
            mobile_support_checkbox.setEnabled(False)
            mobile_support_checkbox.setChecked(False)
        else:
            mobile_support_checkbox.setChecked(
                config[MobileSettingName.ENABLE_MOBILE_SUPPORT.value]
            )

    def on_save_config(
        self,
        dialog: ExtensibleDialog,
        config: MutableMapping,
        logged_in: bool,
        article_access: bool,
    ):
        mobile_support_checkbox = cast(
            QCheckBox,
            dialog.get_extension_widget(self._enable_mobile_support_name),
        )

        if not logged_in or not article_access:
            pass  # ignore visual state of disabled checkbox, preserve config value
        else:
            config[
                MobileSettingName.ENABLE_MOBILE_SUPPORT.value
            ] = mobile_support_checkbox.isChecked()
