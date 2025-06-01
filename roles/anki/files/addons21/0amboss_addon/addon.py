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

import os
import sys
from collections import deque

from aqt import mw

# Make vendorized packages available to importer
MODULE = __name__.split(".")[0]
ADDON_PATH = os.path.join(mw.pm.addonFolder(), MODULE)  # type: ignore[union-attr]

sys.path.insert(0, os.path.join(ADDON_PATH, "_vendor"))

# typing is potentially vendored, so we import it after the sys.path hack
from typing import TYPE_CHECKING, Deque, Dict, Optional, Literal, cast

if TYPE_CHECKING:
    assert mw is not None

from dotenv import load_dotenv

# Environment

if os.path.isfile(os.path.join(ADDON_PATH, ".env")):
    load_dotenv(dotenv_path=os.path.join(ADDON_PATH, ".env"))
else:
    raise Exception("Missing `.env` file")

from .shared import set_locale

set_locale(cast(Literal["en", "de"], os.environ.get("AMBOSS_LANGUAGE", "en")))

from aqt.qt import QThreadPool

from ._version import __version__
from .about import AboutDialog
from .activity import ActivityCookieService, ActivityService
from .anki.version import ANKI_VERSION, VersionChecker
from .anki_meta import MetaStorageAdapter
from .auth import (
    AuthDialog,
    FormAuthErrorParser,
    FormRegisterClient,
    GraphQLLoginErrorParser,
    LoginHandler,
    LogoutDialog,
    RegisterHandler,
)
from .config import AddonConfig, AnkiJSONConfigProvider, ConfigSignals
from .controller import AmbossController
from .debug import (
    DEBUG_ACTIVE,
    DebugService,
    ErrorCounter,
    ErrorPromptFactory,
    ErrorSubmitter,
)
from .graphql import GraphQLQueryResolver
from .hooks import amboss_did_login, amboss_did_logout
from .hotkeys import HotkeyManager
from .indicator import Indicator
from .links import ExternalLinkHandler, MediaLinkHandler
from .menu import Menu, MenuHandler
from .network import (
    HTTPClientFactory,
    HTTPConnectionPoolFactory,
    RateLimitParser,
    TokenAuth,
)
from .notification import NotificationService
from .patch import MultiPatcher
from .patch.toolbar import TopToolbarHookPatcher, TopToolbarMonkeyPatcher
from .patch.view import MainViewHookPatcher, ReviewerHTMLPatcher
from .phrases import (
    DestinationMapper,
    MediaMapper,
    PhraseFinder,
    PhraseFinderCacheClient,
    PhraseFinderHTTPClient,
    PhraseGroupClient,
    PhraseGroupMapper,
    PhraseGroupResolver,
    PhraseMapper,
    PhraseRepository,
)
from .profile import ProfileAdapter
from .reviewer import (
    ReviewerCardPhraseUpdater,
    ReviewerErrorHandler,
    ReviewerScheduleService,
    ReviewerStyler,
    ReviewerTooltipManagerAdapter,
    ReviewerTooltipUpdater,
)
from .router import (
    AboutRouter,
    AuthRouter,
    ProfileRouter,
    ReviewerRouter,
    SidePanelRouter,
    VersionRouter,
)
from .settings import SettingsDialogFactory, create_config_action
from .shared import string_to_boolean
from .sidepanel import (
    SidePanel,
    SidePanelActivityRegistry,
    SidePanelController,
)
from .sidepanel_web import SidePanelURLRedirector
from .theme import ThemeManager
from .tooltip import (
    PhraseGroupTooltipMapper,
    PhraseTooltipMapper,
    TooltipDestinationLabelFactory,
    TooltipFactory,
    TooltipQueryFactory,
    TooltipRenderer,
    TooltipRenderService,
    TooltipService,
    TooltipURLService,
)
from .update import (
    AddonInstaller,
    AnkiWebUpdateHandler,
    UpdateNotificationService,
)
from .update_ui import UpdateUIHandler
from .user import (
    ArticleAccessHTTPClient,
    ArticleAccessResolver,
    LoginStateResolver,
    StudyObjectiveService,
    UserService,
    UserStateMutationObserver,
    UserStateResolver,
)
from .user_agent import UserAgentService
from .web import (
    LocalURLResolver,
    LocalWebPage,
    WebProfile,
    WebProfileAuthHandler,
    WebView,
)

# Make vendorized packages available to importer
# Prepares and registers web elements with Anki.
# Bypasses Anki's security policy to enable loading of our web elements.
mw.addonManager.setWebExports(__name__, r"web(\\|/).*")

# Properties

DISTRIBUTION_CHANNEL = os.environ.get("AMBOSS_DISTRIBUTION_CHANNEL", "download")

recommended_anki_version = "2.1.35"
stage = os.environ.get("AMBOSS_STAGE") or "production"

# Values without default
meta_key = os.environ["AMBOSS_META_KEY"]
token_key = os.environ["AMBOSS_TOKEN_KEY"]

graphql_uri = (
    os.environ.get("AMBOSS_GRAPHQL_URI")
    or "https://content-gateway.us.production.amboss.com"
)
rest_phrase_uri = (
    os.environ.get("AMBOSS_RESTPHRASE_URI")
    or "https://anki.production.amboss.com/anki_evaluate_flashcard/us/v1/"
)
article_access_uri = (
    os.environ.get("AMBOSS_ACCESS_URI")
    or "https://anki.production.amboss.com/v1/access/article/"
)
tooltip_notification_uri = (
    os.environ.get("AMBOSS_TOOLTIP_NOTIFICATION_URI")
    or "https://anki.production.amboss.com/us/v1/notification/"
)
update_notification_uri = (
    os.environ.get("AMBOSS_UPDATE_NOTIFICATION_URI")
    or "https://anki.production.amboss.com/us/v1/update/"
)
token_exchange_uri = (
    os.environ.get("AMBOSS_TOKEN_EXCHANGE_URI")
    or "https://anki.production.amboss.com/us/v1/token/"
)
update_overwrite_enabled = string_to_boolean(
    os.environ.get("AMBOSS_UPDATE_ENABLED", "false")
)
firstrun_forced = string_to_boolean(os.environ.get("AMBOSS_FORCE_FIRSTRUN", "false"))
onboarding_forced = string_to_boolean(
    os.environ.get("AMBOSS_FORCE_ONBOARDING", "false")
)
amboss_library_uri = (
    os.environ.get("AMBOSS_LIBRARY_URI") or "https://www.amboss.com/us/library"
)
timeout = int(os.environ.get("AMBOSS_TIMEOUT") or 10)
retries = int(os.environ.get("AMBOSS_RETRIES") or 2)
feedback_uri = (
    os.environ.get("AMBOSS_FEEDBACK_URI")
    or "https://docs.google.com/forms/d/e/1FAIpQLSe6CNC3XIvqs9nhZ93OevEEbAUR-XKQHcmk74BSN7gD5buKEg/viewform"
)
amboss_dashboard_uri = (
    os.environ.get("AMBOSS_DASHBOARD_URI") or "https://next.amboss.com/us"
)
media_viewer_with_access_url_template = (
    os.environ.get("AMBOSS_MEDIA_VIEWER_WITH_ACCESS_URL_TEMPLATE")
    or "https://next.amboss.com/us/search/{phrase_title}?q={phrase_title}&v=overview&m={media_id}"
)
media_viewer_without_access_url_template = (
    os.environ.get("AMBOSS_MEDIA_VIEWER_WITHOUT_ACCESS_URL_TEMPLATE")
    or "https://next.amboss.com/us?m={media_id}"
)
auth_token_cookie_name = (
    os.environ.get("AMBOSS_AUTH_TOKEN_COOKIE_NAME") or "next_auth_amboss_us"
)
auth_token_cookie_domain = (
    os.environ.get("AMBOSS_AUTH_TOKEN_COOKIE_DOMAIN") or ".amboss.com"
)
support_uri = (
    os.environ.get("AMBOSS_SUPPORT_URI")
    or "https://support.amboss.com/hc/en-us/sections/360007443911-Anki"
)
store_uri = os.environ.get("AMBOSS_STORE_URI") or "https://www.amboss.com/us/pricing"
membership_url = (
    os.environ.get("AMBOSS_MEMBERSHIP_URI")
    or "https://next.amboss.com/us/access-overview"
)
form_register_uri = (
    os.environ.get("AMBOSS_FORM_REGISTER_URI")
    or "https://www.amboss.com/us/account/register"
)
# TODO: set production default
sentry_dsn = (
    os.environ.get("AMBOSS_SENTRY_DSN")
    or "https://39cc2d0c71fd43d3ae1c19607c7b6937:ab93eecf0e054b429d07c61f13307665@sentry.miamed.de/31"
)
server_notification_polling_interval = int(
    os.environ.get("AMBOSS_NOTIFICATION_POLLING_INTERVAL") or 300
)
url_fragment_login = "/account/login"
url_fragment_logout = "/account/logout"
url_fragment_register = "/account/register"
url_fragment_register_success = "/account/registerSuccess"
url_fragment_index = "/app/index"

# Token auth

token_auth = TokenAuth()

# Meta storage

meta_storage_adapter = MetaStorageAdapter(profile_manager=mw.pm, storage_key=meta_key)

# Profile

profile_adapter = ProfileAdapter(
    mw.pm,
    token_key=token_key,
    force_first_run=firstrun_forced,
)

# Activity

activity_service = ActivityService(mw.toolbar.web, profile_adapter)

# Local URLs

local_url_resolver = LocalURLResolver(MODULE, mw.mediaServer)
local_onboarding_url = local_url_resolver.resolve(
    "web/auth.html?route=onboarding&modal="
)
local_login_url = local_url_resolver.resolve("web/auth.html?route=login")
local_register_url = local_url_resolver.resolve("web/auth.html?route=register")
local_login_url_auto_close = local_url_resolver.resolve(
    "web/auth.html?route=login&modal="
)
local_media_wall_url = local_url_resolver.resolve("web/auth.html?route=mediaWall")
local_url_fragment_auth = "web/auth.html"

# Config

anki_json_config_provider = AnkiJSONConfigProvider(
    addon_package=MODULE, addon_manager=mw.addonManager
)
addon_config_signals = ConfigSignals(parent=mw)
addon_config = AddonConfig(
    config_provider=anki_json_config_provider,
    config_signals=addon_config_signals,
    profile_adapter=profile_adapter,
)
addon_config.signals.saved.connect(
    lambda: activity_service.register_activity("config.change", dict(addon_config))
)
# Legacy: The previous settings dialog implementation caused a settings save
# on log-in and log-out, triggering subsequent slots connected to the config.saved
# signal. We imitate this behavior here to preserve parity with the previous
# implementation.
amboss_did_login.append(addon_config.save)
amboss_did_logout.append(addon_config.save)

# Debug

# Workaround: Avoid truncating problem descriptions submitted by users
SENTRY_MAX_STRING_LENGTH = 5000

debug_service = DebugService(
    main_window=mw, addon_config=addon_config, version=__version__
)
error_submitter = ErrorSubmitter(
    profile=profile_adapter,
    sentry_dsn=sentry_dsn,
    version=__version__,
    stage=stage,
    max_string_length=SENTRY_MAX_STRING_LENGTH,
)
error_prompt_factory = ErrorPromptFactory(
    main_window=mw,
    debug_service=debug_service,
    error_submitter=error_submitter,
    max_message_chars=SENTRY_MAX_STRING_LENGTH,
)
proxy_error_counter = ErrorCounter(interval=300, overflow=5)
connection_error_counter = ErrorCounter(interval=300, overflow=10)
timeout_error_counter = ErrorCounter(interval=150, overflow=10)


# Network

user_agent_service = UserAgentService(
    debug_service=debug_service, anki_version=ANKI_VERSION
)
cookie_service = ActivityCookieService(
    profile=profile_adapter, domain=auth_token_cookie_domain
)
rest_http_connection_pool_factory = HTTPConnectionPoolFactory(
    timeout=timeout, retries=retries, maxsize=8, block=True
)
rest_http_client_factory = HTTPClientFactory(
    connection_pool_factory=rest_http_connection_pool_factory,
    user_agent=user_agent_service.user_agent(),
    cookie_service=cookie_service,
)
rate_limit_parser = RateLimitParser()

# Thread pool

thread_pool = QThreadPool.globalInstance()

# GraphQL

graphql_http_connection_pool_factory = HTTPConnectionPoolFactory(
    timeout=timeout,
    retries=retries,
    maxsize=8,
    block=True,
    retry_statuses=frozenset([429, 502, 503]),
    retry_methods=frozenset(
        [
            "HEAD",
            "DELETE",
            "TRACE",
            "OPTIONS",
            "GET",
            "PUT",
            "POST",
        ]
    ),
)
graphql_http_client_factory = HTTPClientFactory(
    connection_pool_factory=graphql_http_connection_pool_factory,
    user_agent=user_agent_service.user_agent(),
    cookie_service=cookie_service,
)
graphql_query_resolver = GraphQLQueryResolver(
    uri=graphql_uri,
    token_auth=token_auth,
    http_client_factory=graphql_http_client_factory,
    rate_limit_parser=rate_limit_parser,
)

# User

article_access_http_client = ArticleAccessHTTPClient(
    url=article_access_uri,
    token_auth=token_auth,
    http_client_factory=rest_http_client_factory,
)
login_state_resolver = LoginStateResolver(query_resolver=graphql_query_resolver)
article_access_resolver = ArticleAccessResolver(
    article_access_client=article_access_http_client
)
user_state_resolver = UserStateResolver(
    login_state_resolver=login_state_resolver,
    article_access_resolver=article_access_resolver,
)
user_service = UserService(
    profile=profile_adapter,
    token_auth=token_auth,
    login_state_resolver=login_state_resolver,
)
user_state_mutation_observer = UserStateMutationObserver(
    user_service=user_service,
    user_state_resolver=user_state_resolver,
    thread_pool=thread_pool,
    parent=mw,
)
study_objective_service = StudyObjectiveService(
    graphql_query_resolver=graphql_query_resolver
)
user_state_mutation_observer.observe()
history: Deque[str] = deque([], 1)

# Theme

theme_manager = ThemeManager(MODULE)

# Phrases

phrase_mapper = PhraseMapper()
destination_mapper = DestinationMapper()
media_mapper = MediaMapper()
phrase_group_mapper = PhraseGroupMapper(destination_mapper, media_mapper)
phrase_finder_http_client = PhraseFinderHTTPClient(
    rest_phrase_uri, token_auth, rest_http_client_factory
)
phrase_finder_client = PhraseFinderCacheClient(phrase_finder_http_client)
phrase_repository = PhraseRepository()
phrase_finder = PhraseFinder(phrase_finder_client, phrase_repository, phrase_mapper)
phrase_group_client = PhraseGroupClient(graphql_query_resolver, profile_adapter)
phrase_group_resolver = PhraseGroupResolver(phrase_group_client, phrase_group_mapper)

# Version

version_check_result = VersionChecker.get_result(ANKI_VERSION, recommended_anki_version)

# Auth

graphql_login_error_parser = GraphQLLoginErrorParser()
form_auth_error_parser = FormAuthErrorParser()

form_register_client = FormRegisterClient(
    uri=form_register_uri,
    http_client_factory=rest_http_client_factory,
    url_fragment_register_success=url_fragment_register_success,
    error_parser=form_auth_error_parser,
    error_prompt_factory=error_prompt_factory,
)

login_handler = LoginHandler(
    graphql_query_resolver=graphql_query_resolver,
    graphql_error_parser=graphql_login_error_parser,
    user_service=user_service,
)
register_handler = RegisterHandler(mw.reviewer, form_register_client)

auth_page = LocalWebPage()  # custom bridge controller set in later step
auth_web_view = WebView(theme_manager=theme_manager, object_name="amboss_auth_webview")
auth_web_view.setPage(auth_page)
auth_dialog = AuthDialog(
    main_window=mw,
    web_server=mw.mediaServer,
    login_url=local_login_url_auto_close,
    onboarding_url=local_onboarding_url,
    web_view=auth_web_view,
    activity_service=activity_service,
    meta_storage_adapter=meta_storage_adapter,
    force_onboarding=onboarding_forced,
)

logout_dialog = LogoutDialog(mw)

# Notification

notification_service = NotificationService(
    tooltip_notification_uri,
    update_notification_uri,
    token_auth,
    rest_http_client_factory,
    server_notification_polling_interval,
    __version__,
    ANKI_VERSION,
)

# Tooltip

phrase_tooltip_mapper = PhraseTooltipMapper()
tooltip_query_factory = TooltipQueryFactory(profile_adapter)
tooltip_url_service = TooltipURLService(tooltip_query_factory)
phrase_group_tooltip_mapper = PhraseGroupTooltipMapper(
    tooltip_url_service, store_uri, local_register_url, user_service
)
tooltip_factory = TooltipFactory(phrase_tooltip_mapper, phrase_group_tooltip_mapper)
tooltip_destination_label_factory = TooltipDestinationLabelFactory()
tooltip_renderer = TooltipRenderer(
    destination_label_factory=tooltip_destination_label_factory,
    debug_service=debug_service,
    user_service=user_service,
    library_uri=amboss_library_uri,
    feedback_uri=feedback_uri,
    amboss_dashboard_uri=amboss_dashboard_uri,
    media_viewer_with_access_url_template=media_viewer_with_access_url_template,
    media_viewer_without_access_url_template=media_viewer_without_access_url_template,
    tooltip_url_service=tooltip_url_service,
    addon_module=MODULE,
)
tooltip_service = TooltipService(
    phrase_repository, phrase_group_resolver, tooltip_factory, notification_service
)
tooltip_render_service = TooltipRenderService(
    tooltip_service, tooltip_renderer, mw.reviewer
)

# Reviewer

reviewer_styler = ReviewerStyler(addon_config)
reviewer_html_patcher = ReviewerHTMLPatcher(
    f"/_addons/{MODULE}/web",
    (
        "analytics.js",
        "tooltip.js",
    ),
    (
        "css/global.css",
        "css/tippy.css",
        "css/highlight.css",
    ),
    (reviewer_styler.get_highlights_style,),
)
reviewer_error_handler = ReviewerErrorHandler(
    error_prompt_factory,
    proxy_error_counter,
    connection_error_counter,
    timeout_error_counter,
    3000,
)
reviewer_schedule_service = ReviewerScheduleService(mw.reviewer)
reviewer_card_phrase_updater = ReviewerCardPhraseUpdater(
    mw.reviewer,
    phrase_finder,
    reviewer_schedule_service,
    thread_pool,
    reviewer_error_handler,
    addon_config,
    reviewer_styler,
    activity_service,
)
reviewer_tooltip_updater = ReviewerTooltipUpdater(
    mw.reviewer, tooltip_render_service, thread_pool, reviewer_error_handler
)
reviewer_tooltip_manager_adapter = ReviewerTooltipManagerAdapter(mw.reviewer)

reviewer_card_phrase_updater.register_hooks()
reviewer_html_patcher.patch()
reviewer_card_phrase_updater.register_hooks()

# Side panel and indicator

side_panel_anon_redirects: Dict[str, Optional[str]] = {
    url_fragment_login: local_login_url,
    url_fragment_logout: local_login_url,
    url_fragment_register: local_register_url,
    url_fragment_index: None,
}

side_panel_user_redirects: Dict[str, Optional[str]] = {
    url_fragment_login: membership_url,
    url_fragment_logout: local_login_url,
    url_fragment_register: membership_url,
    url_fragment_index: amboss_dashboard_uri,
}

amboss_web_profile = WebProfile(
    storage_name="amboss",
    meta_storage_adapter=meta_storage_adapter,
    user_agent=user_agent_service.user_agent(),
)
side_panel_url_redirector = SidePanelURLRedirector(
    user_service=user_service,
    anon_redirects=side_panel_anon_redirects,
    user_redirects=side_panel_user_redirects,
)
side_panel = SidePanel(
    web_profile=amboss_web_profile,
    home_uri=amboss_dashboard_uri,
    login_uri=local_login_url,
    url_redirector=side_panel_url_redirector,
    theme_manager=theme_manager,
    main_window=mw,
    anki_version=ANKI_VERSION,
)
side_panel_controller = SidePanelController(
    main_window=mw,
    side_panel=side_panel,
    user_service=user_service,
    history=history,
    local_url_fragment_auth=local_url_fragment_auth,
    theme_manager=theme_manager,
    error_prompt_factory=error_prompt_factory,
)

side_panel_auth_handler = WebProfileAuthHandler(
    web_profile=amboss_web_profile,
    profile_adapter=profile_adapter,
    auth_token_cookie_name=auth_token_cookie_name,
    auth_token_cookie_domain=auth_token_cookie_domain,
)
side_panel_auth_handler.subscribe_to_auth_events()

side_panel_auth_handler.logged_in.connect(side_panel_controller.set_logged_in)
side_panel_auth_handler.logged_out.connect(side_panel_controller.set_logged_out)
side_panel_auth_handler.error.connect(side_panel_controller.on_login_error)

# Routers

external_link_handler = ExternalLinkHandler(
    addon_config=addon_config,
    side_panel_controller=side_panel_controller,
    history=history,
)
media_link_handler = MediaLinkHandler(
    external_link_handler=external_link_handler,
    side_panel_controller=side_panel_controller,
    user_service=user_service,
    media_wall_url=local_media_wall_url,
    history=history,
)
reviewer_router = ReviewerRouter(
    reviewer_tooltip_updater=reviewer_tooltip_updater,
    external_link_handler=external_link_handler,
    media_link_handler=media_link_handler,
)
auth_router = AuthRouter(login_handler, auth_dialog, register_handler)
about_router = AboutRouter(error_prompt_factory)
version_router = VersionRouter(version_check_result, __version__)
profile_router = ProfileRouter(profile_adapter)
side_panel_router = SidePanelRouter(side_panel_controller)

# Amboss controller

amboss_controller = AmbossController(
    reviewer=reviewer_router,
    about=about_router,
    version=version_router,
    profile=profile_router,
    side_panel=side_panel_router,
)

auth_controller = AmbossController(
    reviewer=reviewer_router,
    auth=auth_router,
    version=version_router,
    profile=profile_router,
    side_panel=side_panel_router,
)

# Indicator

indicator_widget = Indicator(
    mw,
    theme_manager,
    addon_config,
)

indicator_widget.clicked.connect(
    lambda: side_panel_controller.toggle(origin="indicator")
)

side_panel_activity_adapter = SidePanelActivityRegistry(
    activity_service, side_panel_controller, side_panel
)
side_panel_controller.toggled.connect(side_panel_activity_adapter.register_toggled)
side_panel_controller.toggled.connect(lambda state, _: indicator_widget.toggle(state))
side_panel_controller.resized.connect(side_panel_activity_adapter.register_resized)
side_panel.navigated.connect(side_panel_activity_adapter.register_navigated)

# About

about_page = LocalWebPage(amboss_controller)
about_web_view = WebView(
    theme_manager=theme_manager, object_name="amboss_about_webview"
)
about_web_view.setPage(about_page)
about_dialog = AboutDialog(
    mw,
    mw.mediaServer,
    local_url_resolver.resolve(f"web/about.html?version={__version__}"),
    about_web_view,
)

# Auth controller

auth_page.setBridgeCommand(auth_controller)

# Side panel controller

side_panel.set_bridge_command(auth_controller)

# Main window view controller patcher

main_view_hook_patcher = MainViewHookPatcher(controller=amboss_controller)
main_view_patcher = MultiPatcher(main_view_hook_patcher)
main_view_patcher.defer_patch_once()

# Toolbar controller patcher

top_toolbar_hook_patcher = TopToolbarHookPatcher(
    amboss_controller, MODULE, indicator_widget, ("analytics.js", "indicator.js")
)
top_toolbar_monkey_patcher = TopToolbarMonkeyPatcher(
    amboss_controller, MODULE, indicator_widget, ("analytics.js", "indicator.js")
)
top_toolbar_patcher = MultiPatcher(top_toolbar_hook_patcher, top_toolbar_monkey_patcher)
top_toolbar_patcher.patch_once()

# Update

if DISTRIBUTION_CHANNEL == "ankiweb" or DEBUG_ACTIVE:
    AnkiWebUpdateHandler.disable_updates(addon_path=ADDON_PATH)

addon_installer = AddonInstaller(mw.addonManager, update_overwrite_enabled)
update_notification_service = UpdateNotificationService(
    notification_service=notification_service, version=__version__
)
update_ui_handler = UpdateUIHandler(
    main_window=mw, addon_installer=addon_installer, support_uri=support_uri
)
update_notification_service.result.connect(update_ui_handler.start)
update_notification_service.blocked.connect(update_ui_handler.block)
# attach to mw to protect qt objects from garbage collection
mw._amboss_update_ui_handler = update_ui_handler  # type: ignore[attr-defined]
mw._amboss_update_notification_service = (  # type: ignore[attr-defined]
    update_notification_service
)
update_notification_service.deferred_run()

# Settings

settings_dialog_factory = SettingsDialogFactory(
    config=addon_config,
    user_service=user_service,
)
config_action = create_config_action(
    settings_dialog_factory=settings_dialog_factory,
    parent=mw,
)

mw.addonManager.setConfigAction(MODULE, config_action)

# Menu

menu = Menu()
menu_handler = MenuHandler(
    main_window=mw,
    menu=menu,
    auth_dialog=auth_dialog,
    logout_dialog=logout_dialog,
    about_dialog=about_dialog,
    settings_dialog_factory=settings_dialog_factory,
    login_handler=login_handler,
    reviewer_card_phrase_updater=reviewer_card_phrase_updater,
    update_notification_service=update_notification_service,
    side_panel_controller=side_panel_controller,
    addon_config=addon_config,
    support_uri=support_uri,
    login_uri=local_login_url,
)
menu_handler.setup()

# Hotkeys

hotkey_manager = HotkeyManager(mw, addon_config)

hotkey_manager.hotkeyClosePopup.connect(reviewer_tooltip_manager_adapter.close_tooltips)
hotkey_manager.hotkeyOpenPreviousPopup.connect(
    reviewer_tooltip_manager_adapter.open_previous_tooltip
)
hotkey_manager.hotkeyOpenNextPopup.connect(
    reviewer_tooltip_manager_adapter.open_next_tooltip
)
hotkey_manager.hotkeyToggleSidePanel.connect(side_panel_controller.toggle)
