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

# Qbank integration

import os
from typing import TYPE_CHECKING

from aqt import mw

if TYPE_CHECKING:
    assert mw is not None

from ..addon import (
    ANKI_VERSION,
    MODULE,
    activity_service,
    addon_config,
    amboss_controller,
    amboss_dashboard_uri,
    error_prompt_factory,
    graphql_query_resolver,
    local_login_url,
    local_url_resolver,
    profile_adapter,
    rest_http_client_factory,
    settings_dialog_factory,
    side_panel_controller,
    store_uri,
    study_objective_service,
    theme_manager,
    thread_pool,
    user_service,
)
from ..anki.cardbrowser import (
    CardBrowserPatcher,
    SearchLayoutExtender,
    SidebarContextMenuExtender,
)
from ..anki.collection import AnkiCollectionService
from ..anki.deckbrowser import DeckBrowserPatcher, DeckBrowserRouter
from ..anki.dialogs import dialog_manager
from ..anki.state import AnkiStateService
from ..anki.version import VersionChecker
from ..debug import QBANK_DEBUG_ACTIVE
from ..hooks import amboss_did_login, amboss_did_logout
from ..network import TokenAuth
from .config import QBankSettingName
from .controller import QBankController
from .data import DataProvider
from .launch import QBankSessionLauncher
from .model_qbank import QuestionStatus
from .selection import (
    QBankSelectionDialog,
    QBankSelectionUIFactory,
    QBankSelectionUIService,
)
from .service_mapper import MappingServiceHTTPClient, QBankMapperService
from .service_notes import AnkiNoteService
from .service_qbank import QBankSessionService
from .settings import QBankSettingsExtension
from .state import (
    LoggedInQBankStateResolver,
    LoggedOutQBankStateResolver,
    QBankStateService,
    QBankStateUpdateScheduler,
)
from .ui_browser import (
    QBankButtonFactory,
    QBankContextMenuProvider,
    QBankSelectionListener,
)
from .ui_home import QBankHomeWidget

qbank_mapping_service_url = (
    os.environ.get("AMBOSS_QBANK_MAPPER_URI")
    or "https://anki-qbank-mapper.us.staging.labamboss.com/questions"
)

qbank_mapper_max_widget_note_count = int(
    os.environ.get("AMBOSS_QBANK_MAPPER_MAX_WIDGET_NOTE_COUNT") or 2000
)
qbank_mapper_max_browser_note_count = int(
    os.environ.get("AMBOSS_QBANK_MAPPER_MAX_BROWSER_NOTE_COUNT") or 5000
)

qbank_settings_extension = QBankSettingsExtension()
settings_dialog_factory.register_extension(qbank_settings_extension)

qbank_session_service = QBankSessionService(
    graphql_query_resolver=graphql_query_resolver, base_url=amboss_dashboard_uri
)
qbank_home_widget = QBankHomeWidget(
    deck_browser=mw.deckBrowser,
    package_name=MODULE,
    login_url=local_login_url,
    user_service=user_service,
)
qbank_home_widget.set_visible(
    addon_config[QBankSettingName.ENABLE_QBANK_HOME_INTEGRATION.value]
)
addon_config.signals.changed.connect(qbank_home_widget.maybe_update_visibility)

anki_collection_service = AnkiCollectionService(main_window=mw)
data_provider = DataProvider(anki_collection_service=anki_collection_service)
anki_note_service = AnkiNoteService(data_provider=data_provider)

mapping_service_token_auth = TokenAuth(token="ambossLoveAnki666")
mapping_service_client = MappingServiceHTTPClient(
    url=qbank_mapping_service_url,
    token_auth=mapping_service_token_auth,
    http_client_factory=rest_http_client_factory,
)

qbank_mapper_service = QBankMapperService(mapping_service_client=mapping_service_client)

question_statuses = (
    [QuestionStatus.UNSEEN_OR_SKIPPED] if not QBANK_DEBUG_ACTIVE else None
)
qbank_loading_url = local_url_resolver.resolve("web/qbank-loading.html")
logged_out_qbank_state_resolver = LoggedOutQBankStateResolver()
logged_in_qbank_state_resolver = LoggedInQBankStateResolver(
    qbank_service=qbank_session_service,
    mapper_service=qbank_mapper_service,
    study_objective_service=study_objective_service,
    question_statuses=question_statuses,
)
qbank_state_service = QBankStateService(
    user_service=user_service,
    note_service=anki_note_service,
    logged_out_qbank_state_resolver=logged_out_qbank_state_resolver,
    logged_in_qbank_state_resolver=logged_in_qbank_state_resolver,
    activity_service=activity_service,
    max_widget_note_count=qbank_mapper_max_widget_note_count,
    qbank_widget=qbank_home_widget,
)
qbank_state_update_scheduler = QBankStateUpdateScheduler(
    thread_pool=thread_pool,
    qbank_state_service=qbank_state_service,
    activity_service=activity_service,
    parent=mw,
)
qbank_controller = QBankController(
    qbank_service=qbank_session_service,
    qbank_state_update_scheduler=qbank_state_update_scheduler,
    qbank_widget=qbank_home_widget,
    main_window=mw,
    side_panel_controller=side_panel_controller,
    activity_service=activity_service,
    dialog_manager=dialog_manager,
    profile=profile_adapter,
    error_prompt_factory=error_prompt_factory,
    store_url=store_uri,
    question_statuses=question_statuses,
)
qbank_selection_ui_factory = QBankSelectionUIFactory(
    dialog_factory=QBankSelectionDialog,
    ui_service_factory=QBankSelectionUIService,
    theme_manager=theme_manager,
    error_prompt_factory=error_prompt_factory,
    note_service=anki_note_service,
    mapper_service=qbank_mapper_service,
    session_service=qbank_session_service,
    study_objective_service=study_objective_service,
    profile=profile_adapter,
    thread_pool=thread_pool,
    loading_url=qbank_loading_url,
    launcher_factory=QBankSessionLauncher,
    store_url=store_uri,
    debug=QBANK_DEBUG_ACTIVE,
)
amboss_did_logout.append(qbank_state_update_scheduler.schedule_state_update)
amboss_did_login.append(qbank_state_update_scheduler.schedule_state_update)

deck_browser_patcher = DeckBrowserPatcher(stats_content_provider=qbank_home_widget.html)
deck_browser_router = DeckBrowserRouter()
deck_browser_router.connect_command(
    "start_qbank_session",
    lambda arg: qbank_controller.start_global_question_session(
        max_size=int(arg) if arg is not None else None
    ),
)
deck_browser_router.connect_command(
    "launch_card_browser",
    qbank_controller.launch_card_browser,
)
deck_browser_patcher.patch()

qbank_button_factory = QBankButtonFactory(
    qbank_selection_ui_factory=qbank_selection_ui_factory,
    max_note_count=qbank_mapper_max_browser_note_count,
    user_service=user_service,
    activity_service=activity_service,
    theme_manager=theme_manager,
)
search_layout_extender = SearchLayoutExtender(qbank_button_factory)

qbank_selection_listener = QBankSelectionListener()
sidebar_context_menu_extender = None
if VersionChecker.check(ANKI_VERSION, "2.1.45"):
    qbank_context_menu_provider = QBankContextMenuProvider(
        qbank_selection_ui_factory=qbank_selection_ui_factory,
        max_note_count=qbank_mapper_max_browser_note_count,
        user_service=user_service,
        activity_service=activity_service,
    )
    sidebar_context_menu_extender = SidebarContextMenuExtender(
        qbank_context_menu_provider
    )
card_browser_patcher = CardBrowserPatcher(
    sidebar_context_menu_extender, search_layout_extender, qbank_selection_listener
)
card_browser_patcher.patch()

# TODO: observe note additions and deletions without mw state changes
anki_state_service = AnkiStateService(main_window=mw)
anki_state_service.state_switched_to_deckbrowser.connect(
    qbank_state_update_scheduler.schedule_state_update
)

amboss_controller.add_router(key="deck_browser", router=deck_browser_router)
