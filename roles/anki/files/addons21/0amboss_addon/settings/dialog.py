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

from typing import TYPE_CHECKING, Dict, List, Optional, Union

from aqt.qt import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QKeySequence,
    QKeySequenceEdit,
    QWidget,
)

from ..config import (
    AddonConfig,
    ColorSettingName,
    DisplaySettingName,
    HotkeySettingName,
)
from ..shared import _
from .color_button import QColorButton
from .extensions import SettingsExtension

if TYPE_CHECKING:  # 2.1.49 is dev target, thus type-checking assumes Qt5
    from ..gui.forms.qt5 import settings
else:
    from ..gui.forms import settings


class SettingsDialog(QDialog):
    def __init__(
        self,
        config: AddonConfig,
        logged_in: bool,
        article_access: bool,
        extensions: Optional[List[SettingsExtension]] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent=parent)
        self.setObjectName("amboss_settings_dialog")
        self._config = config
        self._logged_in = logged_in
        self._article_access = article_access
        self._extensions = extensions or []

        self._form = settings.Ui_Settings()
        self._form.setupUi(self)
        self._highlight_color_button = QColorButton(self)
        self._highlight_color_button.setObjectName("style_color_highlights")
        self._form.layout_color_button.addWidget(self._highlight_color_button)
        self._translate_form_ui()

        self._hotkey_setting_widgets: Dict[HotkeySettingName, QKeySequenceEdit] = {
            HotkeySettingName.OPEN_NEXT_POPUP: self._form.hotkey_open_next_popup,
            HotkeySettingName.OPEN_PREVIOUS_POPUP: self._form.hotkey_open_previous_popup,
            HotkeySettingName.CLOSE_POPUP: self._form.hotkey_close_popup,
            HotkeySettingName.TOGGLE_SIDE_PANEL: self._form.hotkey_toggle_side_panel,
        }
        self._display_setting_widgets: Dict[DisplaySettingName, QCheckBox] = {
            DisplaySettingName.ENABLE_GENERAL: self._form.enable_popup_definitions,
            DisplaySettingName.ENABLE_QUESTION: self._form.enable_popup_definitions_on_questions,
            DisplaySettingName.ENABLE_ARTICLE_VIEWER: self._form.enable_article_viewer,
        }
        self._color_setting_widgets: Dict[ColorSettingName, QColorButton] = {
            ColorSettingName.HIGHLIGHTS: self._highlight_color_button,
        }

        restore_defaults_button = self._form.button_box.button(
            QDialogButtonBox.StandardButton.RestoreDefaults
        )
        restore_defaults_button.setObjectName("restore_defaults_button")
        restore_defaults_button.clicked.connect(self._restore_defaults)
        cancel_button = self._form.button_box.button(
            QDialogButtonBox.StandardButton.Cancel
        )
        cancel_button.setObjectName("cancel_button")
        save_button = self._form.button_box.button(QDialogButtonBox.StandardButton.Save)
        save_button.setObjectName("save_button")

        self._form.label_upgrade_access.setVisible(
            not (self._logged_in and self._article_access)
        )

        self._form.widget_extension_section_wrapper.setVisible(bool(extensions))
        for extension in self._extensions:
            extension.on_dialog_init(self)

        self._load_config(self._config)

    def show_modal(self):
        self._form.enable_popup_definitions.setFocus()
        self.exec()

    def accept(self):
        super().accept()
        self._save_config()

    def add_extension_widget(self, object_name: str, widget: QWidget):
        widget.setParent(self._form.widget_extension_section)
        widget.setObjectName(object_name)
        self._form.widget_extension_section.layout().addWidget(widget)

    def get_extension_widget(self, object_name: str) -> Optional[QWidget]:
        return self._form.widget_extension_section.findChild(QWidget, object_name)

    def _load_config(self, config: Union[dict, AddonConfig]):
        for hotkey_setting, key_widget in self._hotkey_setting_widgets.items():
            key_widget.setKeySequence(QKeySequence(config[hotkey_setting.value]))
            key_widget.setEnabled(self._logged_in)

        for display_setting, checkbox in self._display_setting_widgets.items():
            checkbox.setChecked(config[display_setting.value])

        if not self._logged_in:  # always open links inside Anki when logged out
            self._form.enable_article_viewer.setChecked(True)
            self._form.enable_article_viewer.setEnabled(False)

        for color_setting, color_button in self._color_setting_widgets.items():
            color_button.set_color(config[color_setting.value])
            color_button.setEnabled(self._logged_in)

        for extension in self._extensions:
            extension.on_load_config(
                self,
                config=config,
                logged_in=self._logged_in,
                article_access=self._article_access,
            )

    def _save_config(self):
        config = self._config

        for hotkey_setting, key_widget in self._hotkey_setting_widgets.items():
            config[hotkey_setting.value] = key_widget.keySequence().toString()

        for display_setting, checkbox in self._display_setting_widgets.items():
            config[display_setting.value] = checkbox.isChecked()

        if not self._logged_in:  # always open links inside Anki when logged out
            config[DisplaySettingName.ENABLE_ARTICLE_VIEWER.value] = True

        for color_setting, color_picker in self._color_setting_widgets.items():
            config[color_setting.value] = color_picker.color()

        for extension in self._extensions:
            extension.on_save_config(
                self,
                config=config,
                logged_in=self._logged_in,
                article_access=self._article_access,
            )

        self._config.save()

    def _restore_defaults(self):
        self._load_config(self._config.defaults())

    def _translate_form_ui(self):
        self.setWindowTitle(_("AMBOSS - Settings"))
        self._form.label_title.setText(_("AMBOSS Add-on Settings"))
        self._form.label_general.setText(_("General"))
        self._form.label_extension_section.setText(_("Beta Features"))
        self._form.label_upgrade_access.setText(
            _(
                "For all available features, please <a"
                ' href="https://www.amboss.com/us/pricing?utm_source=anki&utm_medium=anki_settings_upgrade">upgrade'
                " your access</a>."
            )
        )
        self._form.label_upgrade_access.setToolTip(
            _("Enable pop-up definitions on mobile and web")
        )
        self._form.label_styling.setText(_("Styling"))
        self._form.label_highlight_color.setText(_("Highlight color"))
        self._form.label_keyboard_shortcuts.setText(_("Keyboard Shortcuts"))
        self._form.label_open_next_popup.setText(_("Open next pop-up"))
        self._form.label_open_previous_popup.setText(_("Open previous pop-up"))
        self._form.label_close_popup.setText(_("Close pop-up"))
        self._form.label_toggle_sidepanel.setText(_("Toggle side panel"))

        self._form.enable_popup_definitions.setToolTip(
            _(
                "Underline important phrases on your cards and provide hover"
                " definitions for them"
            )
        )
        self._form.enable_popup_definitions.setText(_("&Enable pop-up definitions"))
        self._form.enable_popup_definitions_on_questions.setToolTip(
            _(
                "Toggle between showing definitions on both card sides or on the answer"
                " side only"
            )
        )
        self._form.enable_popup_definitions_on_questions.setText(
            _("Show pop-up definitions on &questions")
        )
        self._form.enable_article_viewer.setToolTip(
            _("Whether to open AMBOSS articles within Anki or an external web browser")
        )
        self._form.enable_article_viewer.setText(_("Open &articles in Anki"))

        self._form.button_box.button(
            QDialogButtonBox.StandardButton.RestoreDefaults
        ).setText(_("Restore Defaults"))
        self._form.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText(
            _("Cancel")
        )
        self._form.button_box.button(QDialogButtonBox.StandardButton.Save).setText(
            _("Save")
        )
