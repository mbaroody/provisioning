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


from typing import Any, Dict, Optional

from ..anki_meta import MetaStorageAdapter
from ..shared import _, safe_print
from .service_time import TimeService
from .token import (
    TokenAuthorizationError,
    TokenError,
    TokenExpirationError,
    TokenTimeoutError,
)
from .ui_notifications import MobileNotificationService


class ErrorHandler:
    def __init__(
        self,
        ui_notification_service: MobileNotificationService,
        time_service: TimeService,
        meta_storage_adapter: MetaStorageAdapter,
        notification_interval_seconds: int = 86400,
    ):
        self._ui_notification_service = ui_notification_service
        self._time_service = time_service
        self._meta_storage_adapter = meta_storage_adapter
        self._notification_interval_seconds = notification_interval_seconds

    def handle_template_update_exception(
        self,
        exception: Exception,
        interactive: bool,
        suppress_token_errors: bool = False,
        debug_data: Optional[Dict[str, Any]] = None,
    ):
        """
        :param interactive: If True, treat exception as being caused by a direct, interactive user action.
        :param suppress_token_errors: If True, don't show tooltip notifications for token errors at all.
        """
        if isinstance(exception, TokenError):
            self.handle_token_error(
                error=exception,
                interactive=interactive,
                suppress_token_errors=suppress_token_errors,
            )
        else:
            self._ui_notification_service.show_error_dialog(
                title=_("Could not toggle AMBOSS mobile support."),
                message=_(
                    "Encountered an unexpected error while attempting to toggle mobile"
                    " support. Please contact support if the problem persists."
                ),
                exception=exception,
                debug_data=debug_data,
            )

    def handle_token_error(
        self,
        error: TokenError,
        interactive: bool,
        suppress_token_errors: bool = False,
    ):
        """
        :param interactive: If False, show token once during notification interval. If True, always show token errors.
        :param suppress_token_errors: If True, don't show tooltip notifications for token errors at all.
        """
        time_since_last_error = (
            self._time_service.system_time()
            - self._meta_storage_adapter.mobile_last_token_error_shown_time
        )

        show_error_tooltip = (not suppress_token_errors) and (
            interactive or time_since_last_error >= self._notification_interval_seconds
        )

        if isinstance(error, TokenExpirationError):
            message = _(
                "Could not renew AMBOSS mobile support.<br/>"
                "Please ensure you have AMBOSS access."
            )
        elif isinstance(error, TokenAuthorizationError):
            message = _(
                "Could not enable AMBOSS mobile support.<br/>"
                "Please ensure you have AMBOSS access."
            )
        elif isinstance(error, TokenTimeoutError):
            message = _(
                "Could not update AMBOSS mobile support due to a connection error."
            )
        else:
            message = _("Could not update AMBOSS mobile support.")

        safe_print(message)

        if not show_error_tooltip:
            return

        self._meta_storage_adapter.mobile_last_token_error_shown_time = (
            self._time_service.system_time()
        )

        self._ui_notification_service.show_anki_tooltip(
            message=message, lifetime_milliseconds=5000
        )
