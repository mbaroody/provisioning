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

import os
from typing import TYPE_CHECKING

from aqt import mw

if TYPE_CHECKING:
    assert mw is not None

from ..addon import (
    MODULE,
    addon_config,
    article_access_resolver,
    error_prompt_factory,
    local_url_resolver,
    meta_storage_adapter,
    profile_adapter,
    profile_router,
    rest_http_client_factory,
    settings_dialog_factory,
    theme_manager,
    token_auth,
    token_exchange_uri,
    user_service,
    version_router,
)
from ..anki.addons import (
    hook_into_addon_manager_events,
    our_addon_will_be_deleted,
    our_addon_will_be_disabled,
)
from ..anki.collection import AnkiCollectionService, AnkiNotetypeService
from ..anki.exporting import (
    cards_did_export,
    cards_will_be_exported,
    hook_into_anki_exporters,
)
from ..anki.startup import anki_did_load_and_sync, setup_startup_hooks
from ..anki.sync import do_sync, hook_into_sync_system, sync_will_start
from ..controller import AmbossController
from ..web import LocalWebPage, WebView, WebViewFactory
from .controller import MobileSupportController
from .handler import ErrorHandler as MobileErrorHandler
from .notetypes import NotetypesProcessor, NotetypeUpdater
from .onboarding import MobileOnboardingDialog, MobileOnboardingDialogFactory
from .service_time import TimeService
from .settings import MobileSettingsExtension
from .snippet import SnippetManager
from .templates import TemplateUpdater
from .token import (
    TokenFetcher,
    TokenFetcherHTTPClient,
    TokenRefreshService,
    TokenService,
)
from .ui_notifications import MobileNotificationService

mobile_script_uri = os.environ.get("AMBOSS_MOBILE_SCRIPT_URI", "")

mobile_settings_extension = MobileSettingsExtension()
settings_dialog_factory.register_extension(mobile_settings_extension)

anki_collection_service = AnkiCollectionService(main_window=mw)
anki_notetype_service = AnkiNotetypeService(collection_service=anki_collection_service)

notetypes_processor = NotetypesProcessor(
    notetype_service=anki_notetype_service,
    template_updater=TemplateUpdater(anki_notetype_service),
    notetype_updater=NotetypeUpdater(anki_notetype_service),
)
mobile_snippet_manager = SnippetManager(
    notetypes_processor=notetypes_processor, script_uri=mobile_script_uri
)

mobile_time_service = TimeService()

mobile_token_fetcher_http_client = TokenFetcherHTTPClient(
    url=token_exchange_uri,
    long_term_token_auth=token_auth,
    http_client_factory=rest_http_client_factory,
)
mobile_token_fetcher = TokenFetcher(http_client=mobile_token_fetcher_http_client)
mobile_token_service = TokenService(
    token_fetcher=mobile_token_fetcher, profile_adapter=profile_adapter
)
mobile_token_refresh_service = TokenRefreshService(
    token_service=mobile_token_service, time_service=mobile_time_service
)

mobile_notification_service = MobileNotificationService(
    main_window=mw, error_prompt_factory=error_prompt_factory
)

webview_factory = WebViewFactory(web_view_type=WebView, theme_manager=theme_manager)
mobile_web_bridge_controller = AmbossController(
    version=version_router, profile=profile_router
)
local_mobile_onboarding_url = local_url_resolver.resolve(
    "web/mobile.html?route=onboarding"
)

mobile_onboarding_dialog_factory = MobileOnboardingDialogFactory(
    MobileOnboardingDialog,
    web_view_factory=webview_factory,
    web_page_factory=LocalWebPage,
    web_bridge_controller=mobile_web_bridge_controller,
    onboarding_url=local_mobile_onboarding_url,
)

mobile_error_handler = MobileErrorHandler(
    ui_notification_service=mobile_notification_service,
    time_service=mobile_time_service,
    meta_storage_adapter=meta_storage_adapter,
)

mobile_support_controller = MobileSupportController(
    template_snippet_manager=mobile_snippet_manager,
    user_service=user_service,
    token_refresh_service=mobile_token_refresh_service,
    article_access_resolver=article_access_resolver,
    meta_storage_adapter=meta_storage_adapter,
    addon_config=addon_config,
    ui_notification_service=mobile_notification_service,
    onboarding_dialog_factory=mobile_onboarding_dialog_factory,
    main_window=mw,
    error_handler=mobile_error_handler,
    ankiweb_sync_handler=lambda: do_sync(main_window=mw),  # type: ignore
)

hook_into_anki_exporters()
# NOTE: IMPORTANT – on Anki versions prior to 2.1.55, the hooks below are executed
# in a background thread. Please be careful when adding calls that create Qt UIs.
cards_will_be_exported.append(mobile_support_controller.maybe_remove_snippet)
cards_did_export.append(
    lambda: mobile_support_controller.update_templates(suppress_token_errors=True)
)

hook_into_addon_manager_events(our_package_name=MODULE)
our_addon_will_be_deleted.append(
    mobile_support_controller.handle_addon_disabled_or_deleted
)
our_addon_will_be_disabled.append(
    mobile_support_controller.handle_addon_disabled_or_deleted
)

hook_into_sync_system()
sync_will_start.append(mobile_support_controller.maybe_update_templates_on_sync)

addon_config.signals.changed.connect(
    mobile_support_controller.maybe_update_templates_on_config_changed
)

setup_startup_hooks(main_window=mw)

anki_did_load_and_sync.append(mobile_support_controller.maybe_show_opt_in_prompt)
