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

import html
import json
from typing import TYPE_CHECKING, List, NamedTuple, Optional

if TYPE_CHECKING:
    from aqt.deckbrowser import DeckBrowser

from ..user import UserService
from .config import QBankSettingName


class QBankHomeWidgetState(NamedTuple):
    logged_in: bool = True
    matured_count_total: Optional[int] = None
    unlocked_total: Optional[int] = None
    question_ids: Optional[List[str]] = None
    study_objective: Optional[str] = None


class QBankHomeWidget:
    _div_id = "amboss-qbank-widget"
    _script_name = "amboss-anki-qbank-widget"
    _js_object_name = "ambossQBankWidget"

    def __init__(
        self,
        deck_browser: "DeckBrowser",
        package_name: str,
        login_url: str,
        user_service: UserService,
    ):
        self._deck_browser = deck_browser
        self._package_name = package_name
        self._login_url = login_url

        self._widget_state = QBankHomeWidgetState(logged_in=user_service.is_logged_in())
        self._visible: bool = True

    def html(self) -> str:
        if not self._visible:
            return ""
        return f"""
<script src="/_addons/{self._package_name}/web/{self._script_name}.js"></script>
<amboss-component-wrapper
  data-widget-state="{html.escape(json.dumps(self._widget_state._asdict()))}"
  data-anki-settings="{html.escape(json.dumps({"login_url": self._login_url}))}"
  id="amboss-qbank-widget"
>
</amboss-component-wrapper>
"""

    def set_visible(self, visible: bool):
        self._visible = visible

    def is_visible(self) -> bool:
        return self._visible

    def maybe_update_visibility(self, config_changes: dict):
        if QBankSettingName.ENABLE_QBANK_HOME_INTEGRATION.value not in config_changes:
            return

        self.set_visible(
            config_changes[QBankSettingName.ENABLE_QBANK_HOME_INTEGRATION.value]
        )

        try:
            self._deck_browser.refresh()
        except Exception:
            pass

    def update(
        self,
        widget_state: QBankHomeWidgetState,
    ):
        if not self._visible:
            return
        command = f"""\
document.getElementById("{self._div_id}").dataset.widgetState = {json.dumps(json.dumps(widget_state._asdict()))};\
"""
        self._deck_browser.web.eval(command)
        self._widget_state = widget_state

    @property
    def question_ids(self) -> Optional[List[str]]:
        return self._widget_state.question_ids

    @property
    def state(self) -> QBankHomeWidgetState:
        return self._widget_state
