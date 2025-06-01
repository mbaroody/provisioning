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

import os
from typing import TYPE_CHECKING, Callable, Tuple

from ..anki_meta import MetaStorageAdapter
from ..config import AddonConfig
from ..shared import safe_print
from ..user import ArticleAccessResolver, ArticleAccessTarget, UserService
from .config import MobileSettingName
from .handler import ErrorHandler
from .notetypes import NotetypesProcessingResult
from .onboarding import MobileOnboardingDialogFactory
from .snippet import ModificationType, SnippetData, SnippetManager
from .token import TokenError, TokenRefreshService
from .ui_notifications import MobileNotificationService

if TYPE_CHECKING:
    from aqt.main import AnkiQt


class MobileSupportController:
    def __init__(
        self,
        template_snippet_manager: SnippetManager,
        user_service: UserService,
        token_refresh_service: TokenRefreshService,
        article_access_resolver: ArticleAccessResolver,
        meta_storage_adapter: MetaStorageAdapter,
        addon_config: AddonConfig,
        ui_notification_service: MobileNotificationService,
        onboarding_dialog_factory: MobileOnboardingDialogFactory,
        main_window: "AnkiQt",
        error_handler: ErrorHandler,
        ankiweb_sync_handler: Callable[[], None],
    ):
        self._snippet_manager = template_snippet_manager
        self._user_service = user_service
        self._token_refresh_service = token_refresh_service
        self._article_access_resolver = article_access_resolver
        self._meta_storage_adapter = meta_storage_adapter
        self._addon_config = addon_config
        self._ui_notification_service = ui_notification_service
        self._onboarding_dialog_factory = onboarding_dialog_factory
        self._main_window = main_window
        self._error_handler = error_handler
        self._ankiweb_sync_handler = ankiweb_sync_handler
        self._update_in_progress = False
        self._force_snippet_removal = False

    def maybe_show_opt_in_prompt(self):
        if not self.should_show_opt_in_dialog():
            return

        onboarding_dialog = self._onboarding_dialog_factory.create(
            parent=self._main_window
        )
        onboarding_dialog.load_onboarding_page()
        onboarding_dialog.show_non_blocking(self._on_opt_in_dialog_return)

    def should_show_opt_in_dialog(self) -> bool:
        if os.environ.get("AMBOSS_FORCE_MOBILE_PROMPT"):
            return True
        if self._meta_storage_adapter.mobile_experiment_prompt_v1_shown:
            return False

        if (
            self._article_access_resolver.article_access(
                fallback_access=ArticleAccessTarget.public_article
            )
            != ArticleAccessTarget.platform_article
        ):
            return False
        return True

    def _on_opt_in_dialog_return(self, return_code: int):
        enable_mobile_support = return_code == 1

        self._meta_storage_adapter.mobile_experiment_prompt_v1_shown = True

        # will trigger interactive update_templates:
        self.toggle_mobile_support(enabled=enable_mobile_support, signal_changes=True)

    def maybe_update_templates_on_sync(self):
        """Defensive wrapper method that catches all exceptions during template updates

        NOTE: This method exists to protect against errors on our side blocking users
        from syncing to AnkiWeb, which would fundamentally break their Anki workflow.
        """
        if not self._meta_storage_adapter.mobile_experiment_prompt_v1_shown:
            return  # Do not attempt to update templates until opt-in prompt shown

        if self._update_in_progress:
            return
        self._update_in_progress = True
        try:
            self.update_templates(interactive=False)
        except Exception as exception:
            self._error_handler.handle_template_update_exception(
                exception=exception, interactive=False
            )
        finally:
            self._update_in_progress = False

    def maybe_update_templates_on_config_changed(self, changes: dict):
        if MobileSettingName.ENABLE_MOBILE_SUPPORT.value not in changes:
            return

        if self._update_in_progress:
            return
        self._update_in_progress = True
        try:
            self.update_templates(interactive=True)
        finally:
            self._update_in_progress = False

    def maybe_remove_snippet(self):
        try:
            self._remove_snippet()
        except Exception as exception:
            self._error_handler.handle_template_update_exception(
                exception=exception, interactive=False
            )

    def toggle_mobile_support(self, enabled: bool, signal_changes: bool = True):
        self._addon_config[MobileSettingName.ENABLE_MOBILE_SUPPORT.value] = enabled
        self._addon_config.save(emit_signal=signal_changes)

    def update_templates(
        self, interactive: bool = False, suppress_token_errors: bool = False
    ):
        safe_print("updating templates")

        try:
            modification_type, result = self._perform_template_updates()
        except Exception as exception:
            self._error_handler.handle_template_update_exception(
                exception=exception,
                interactive=interactive,
                suppress_token_errors=suppress_token_errors,
            )
            return

        if result.success is False:
            assert result.exception
            self._error_handler.handle_template_update_exception(
                exception=result.exception,
                interactive=interactive,
                debug_data=result.debug_data,
            )
            return

        if not interactive:
            return

        self._ankiweb_sync_handler()

        self._ui_notification_service.show_results_dialog(
            modification_type=modification_type,
            skipped_notetype_names=result.skipped_notetypes,
        )

    def handle_addon_disabled_or_deleted(self):
        self.maybe_remove_snippet()
        # and schedule forced removal on next update_templates call, i.e. when
        # closing Anki and prompting a sync with AnkiWeb
        self._force_snippet_removal = True

    def _perform_template_updates(
        self,
    ) -> Tuple[ModificationType, NotetypesProcessingResult]:
        if (
            self._force_snippet_removal
            or not self._user_service.is_logged_in()
            or not self._user_service.user_id
            or not self._addon_config[MobileSettingName.ENABLE_MOBILE_SUPPORT.value]
            or self._user_service.article_access_target
            != ArticleAccessTarget.platform_article
        ):
            # remove snippet when user is logged out or mobile support disabled by user
            return (
                ModificationType.SNIPPET_REMOVED,
                self._snippet_manager.remove_snippet(),
            )

        try:
            token_data = self._token_refresh_service.get_token()
        except TokenError:
            raise
        except Exception as e:
            raise TokenError("Could not get valid token data") from e

        addon_data = SnippetData(
            anonId=self._user_service.anon_id,
            userId=self._user_service.user_id,
            token=token_data.token,
        )

        return (
            ModificationType.SNIPPET_INSERTED,
            self._snippet_manager.insert_snippet(data=addon_data),
        )

    def _remove_snippet(self):
        result = self._snippet_manager.remove_snippet()
        if result.success:
            return
        assert result.exception
        self._error_handler.handle_template_update_exception(
            exception=result.exception,
            interactive=False,
            debug_data=result.debug_data,
        )
