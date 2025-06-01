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
from .config import QBankSettingName


class QBankSettingsExtension(SettingsExtension):
    _enable_qbank_home_integration_name = "enable_qbank_home_integration"

    def on_dialog_init(self, dialog: ExtensibleDialog):
        qbank_home_integration_checkbox = QCheckBox(
            _("Enable Qbank widget on home screen")
        )
        dialog.add_extension_widget(
            object_name=self._enable_qbank_home_integration_name,
            widget=qbank_home_integration_checkbox,
        )

    def on_load_config(
        self,
        dialog: ExtensibleDialog,
        config: MutableMapping,
        logged_in: bool,
        article_access: bool,
    ):
        qbank_home_integration_checkbox = cast(
            QCheckBox,
            dialog.get_extension_widget(self._enable_qbank_home_integration_name),
        )
        if not logged_in or not article_access:
            qbank_home_integration_checkbox.setEnabled(False)

        qbank_home_integration_checkbox.setChecked(
            config[QBankSettingName.ENABLE_QBANK_HOME_INTEGRATION.value]
        )

    def on_save_config(
        self,
        dialog: ExtensibleDialog,
        config: MutableMapping,
        logged_in: bool,
        article_access: bool,
    ):
        qbank_home_integration_checkbox = cast(
            QCheckBox,
            dialog.get_extension_widget(self._enable_qbank_home_integration_name),
        )

        config[
            QBankSettingName.ENABLE_QBANK_HOME_INTEGRATION.value
        ] = qbank_home_integration_checkbox.isChecked()
