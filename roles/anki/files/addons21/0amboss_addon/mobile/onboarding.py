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

from typing import Any, Type

from aqt.qt import QUrl, QWidget

from ..controller import AmbossController
from ..gui.simple_web_dialog import SimpleWebDialog
from ..shared import _
from ..web import LocalWebPage, WebViewFactory


class MobileOnboardingDialog(SimpleWebDialog):
    def __init__(
        self,
        parent: QWidget,
        web_view_factory: WebViewFactory,
        web_page_factory: Type[LocalWebPage],
        web_bridge_controller: AmbossController,
        onboarding_url: str,
    ):
        super().__init__(
            parent=parent,
            object_name="amboss_mobile_dialog",
            web_view_factory=web_view_factory,
            web_page_factory=web_page_factory,
            title=_("AMBOSS - Mobile Support"),
        )

        self._web_bridge_controller = web_bridge_controller
        self._onboarding_url = onboarding_url

        self.web_page.setBridgeCommand(self._handle_js_message)

        self.resize(480, 740)

    def load_onboarding_page(self):
        self.load_url(QUrl(self._onboarding_url))

    def _handle_js_message(self, message: str) -> Any:
        if message == "amboss:dialog:accept":
            self.accept()
        elif message == "amboss:dialog:reject":
            self.reject()
        else:
            return self._web_bridge_controller(message)


class MobileOnboardingDialogFactory:
    def __init__(
        self,
        dialog_type: Type[MobileOnboardingDialog],
        web_view_factory: WebViewFactory,
        web_page_factory: Type[LocalWebPage],
        web_bridge_controller: AmbossController,
        onboarding_url: str,
    ):
        self._dialog_type = dialog_type
        self._web_view_factory = web_view_factory
        self._web_page_factory = web_page_factory
        self._web_bridge_controller = web_bridge_controller
        self._onboarding_url = onboarding_url

    def create(self, parent: QWidget) -> MobileOnboardingDialog:
        return self._dialog_type(
            parent=parent,
            web_view_factory=self._web_view_factory,
            web_page_factory=self._web_page_factory,
            web_bridge_controller=self._web_bridge_controller,
            onboarding_url=self._onboarding_url,
        )
