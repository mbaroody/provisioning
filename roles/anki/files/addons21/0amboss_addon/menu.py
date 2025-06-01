# AMBOSS Anki Add-on
#
# Copyright (C) 2019-2020 AMBOSS MD Inc. <https://www.amboss.com/us>
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

from aqt.qt import QMenu
from aqt.utils import openLink

from .about import AboutDialog
from .auth import AuthDialog, LoginHandler, LogoutDialog
from .config import AddonConfig, DisplaySettingName
from .hooks import amboss_did_login, amboss_did_logout, profile_will_close
from .reviewer import ReviewerCardPhraseUpdater
from .settings import SettingsDialogFactory
from .shared import _
from .sidepanel import SidePanelController
from .update import UpdateNotificationService

if TYPE_CHECKING:
    from aqt.main import AnkiQt


class Menu(QMenu):
    """Menu object in a menu bar. Note that aboutText cannot contain 'about', for some reason.
    """

    def __init__(self, *args):
        super().__init__(_("AMBOSS"), *args)
        """
        CAVE: some menu strings below contain invisible spaces,
        as there are already other 'About' and 'Settings' entries that
        would otherwise prevent our menu from showing up on macOS
        """
        self.settings_action = self.addAction(_("S​ettings..."))
        self.settings_separator = self.addSeparator()
        self.login_action = self.addAction(_("Log in..."))
        self.logout_action = self.addAction(_("Log out..."))
        self.addSeparator()
        self.update_action = self.addAction(_("Check for updates"))
        self.support_action = self.addAction(_("Support..."))
        self.about_action = self.addAction(_("A​bout..."))


class MenuHandler:
    """Adds Menu to menu bar and handles its actions."""

    def __init__(
        self,
        main_window: "AnkiQt",
        menu: Menu,
        auth_dialog: AuthDialog,
        logout_dialog: LogoutDialog,
        about_dialog: AboutDialog,
        settings_dialog_factory: SettingsDialogFactory,
        login_handler: LoginHandler,
        reviewer_card_phrase_updater: ReviewerCardPhraseUpdater,
        update_notification_service: UpdateNotificationService,
        side_panel_controller: SidePanelController,
        addon_config: AddonConfig,
        support_uri: str,
        login_uri: str,
    ):
        self._main_window = main_window
        self._menu = menu
        self._auth_dialog = auth_dialog
        self._logout_dialog = logout_dialog
        self._about_dialog = about_dialog
        self._settings_dialog_factory = settings_dialog_factory
        self._login_handler = login_handler
        self._reviewer_card_phrase_updater = reviewer_card_phrase_updater
        self._update_notification_service = update_notification_service
        self._side_panel_controller = side_panel_controller
        self._addon_config = addon_config
        self._support_uri = support_uri
        self._login_uri = login_uri

    def setup(self):
        self._setup_menu()
        self._on_logout_hook()  # set default menu state to logged out
        self._add_hooks()

    def _setup_menu(self):
        self._main_window.form.menubar.addMenu(self._menu)
        self._menu.login_action.triggered.connect(self._login_clicked)
        self._menu.logout_action.triggered.connect(self._logout_clicked)
        self._menu.about_action.triggered.connect(self._about_clicked)
        self._menu.settings_action.triggered.connect(self._settings_clicked)
        self._menu.support_action.triggered.connect(self._support_clicked)
        self._menu.update_action.triggered.connect(self._update_clicked)

    def _add_hooks(self):
        amboss_did_login.append(self._on_login_hook)
        amboss_did_logout.append(self._on_logout_hook)
        profile_will_close.append(self._destroy_hooks)

    def _destroy_hooks(self):
        amboss_did_login.remove(self._on_login_hook)
        amboss_did_login.remove(self._on_logout_hook)

    def _on_login_hook(self):
        self._menu.login_action.setVisible(False)
        self._menu.logout_action.setVisible(True)

    def _on_logout_hook(self):
        self._menu.login_action.setVisible(True)
        self._menu.logout_action.setVisible(False)

    def _login_clicked(self):
        if self._addon_config[DisplaySettingName.ENABLE_ARTICLE_VIEWER.value]:
            # logout state is correlated with article viewer enabled, but still worth checking
            # TODO: consider reusing show_login
            self._side_panel_controller.show_url(self._login_uri)
        else:
            self._auth_dialog.show_login()

    def _logout_clicked(self):
        if self._logout_dialog.confirmed():
            self._login_handler.logout()

    def _about_clicked(self):
        self._about_dialog.show()

    def _settings_clicked(self):
        self._settings_dialog_factory.create(parent=self._main_window).show_modal()

    def _update_clicked(self):
        self._update_notification_service.start(interactive=True)

    def _support_clicked(self):
        link = f"{self._support_uri}?utm_source=anki&utm_medium=anki&utm_campaign=anki"
        openLink(link)
