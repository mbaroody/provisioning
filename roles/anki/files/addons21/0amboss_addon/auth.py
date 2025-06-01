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


"""
Handles user authentication.
"""

from typing import Any, List, NamedTuple, Optional, Union

from aqt.qt import QDialog, QUrl, QVBoxLayout
from aqt.utils import askUser
from bs4 import BeautifulSoup  # type: ignore[import]
from urllib3 import HTTPResponse

from .activity import ActivityService
from .anki_meta import MetaStorageAdapter
from .debug import ErrorPromptFactory
from .graphql import GraphQLErrorCode, GraphQLException, GraphQLQueryResolver
from .hooks import amboss_did_firstrun
from .network import TIMEOUT_ERRORS, HTTPClientFactory, MIMEType
from .shared import _
from .user import UserService
from .web import WebView


class FormRegisterResponse(NamedTuple):
    success: bool
    error: Optional[str]


class FormAuthErrorParser:
    def __init__(self, error_selector: str = ".error_list"):
        self._error_selector = error_selector

    def parse(self, response: str) -> Optional[str]:
        error_list = BeautifulSoup(response, "html.parser").select(self._error_selector)
        return (
            "\n".join(
                [error.text.split(".")[0].strip() for error in error_list if error]
            )
            if error_list
            else None
        )


class GraphQLLoginErrorParser:
    def __init__(self, fallback_message: Optional[str] = None):
        self._fallback_message = fallback_message or _(
            "Oops, something went wrong! Please try again later or contact support if"
            " the problem persists."
        )

    def parse(self, error: Optional[Union[GraphQLException, List, Any]]) -> str:
        if isinstance(error, GraphQLException):
            return self._parse_from_exception(error)
        if isinstance(error, list):
            return self._parse_from_list(error)
        return self._fallback_message

    def _parse_from_exception(self, error: GraphQLException) -> str:
        if not isinstance(error.message, list):
            return str(error)
        if not error.message:
            return str(error)
        return self._parse_from_list(error.message)

    def _parse_from_list(self, error: List) -> str:
        """
        Error message content is controlled by the server, so can in theory by arbitrary, so we have to parse carefully.
        In practice, we expect a certain set of message constants mapping to clear error states.
        """
        message = error[0]
        if not isinstance(message, dict):
            return self._fallback_message
        error_code = message.get("message")
        if not error_code:
            return self._fallback_message
        if error_code == GraphQLErrorCode.wrong_credentials.value:
            return _("Looks like you entered the wrong email or password.")
        if error_code == GraphQLErrorCode.not_authenticated.value:
            return _(
                "Looks like you entered the wrong email or password. (Error code: {})"
                .format(error_code)
            )
        else:
            return self._fallback_message


class FormRegisterClient:
    def __init__(
        self,
        uri: str,
        http_client_factory: HTTPClientFactory,
        url_fragment_register_success: str,
        error_parser: FormAuthErrorParser,
        error_prompt_factory: ErrorPromptFactory,
    ):
        self._http_client = http_client_factory.create(uri)
        self._url_fragment_register_success = url_fragment_register_success
        self._error_parser = error_parser
        self._error_prompt_factory = error_prompt_factory

    def register(self, username: str, password: str) -> FormRegisterResponse:
        try:
            response: HTTPResponse = self._http_client.post(
                data={
                    "sf_guard_user[email_address]": username,
                    "sf_guard_user[password]": password,
                    "sf_guard_user[password_again]": password,
                },
                mime_type=MIMEType.form,
            )
        except TIMEOUT_ERRORS:
            return FormRegisterResponse(
                success=False,
                error=_(
                    "This took longer than expected. Please check if you received a"
                    " confirmation email or try again later."
                ),
            )
        except Exception as e:
            self._error_prompt_factory.create_and_exec(
                exception=e,
                message_heading=_("Encountered an error during registration"),
            )
            return FormRegisterResponse(
                success=False,
                error=_(
                    "Something went wrong while connecting to AMBOSS. "
                    "Please try again later or contact us if the problem persists."
                ),
            )

        return (
            FormRegisterResponse(success=True, error=None)
            if (
                self._url_fragment_register_success
                in response.geturl()  # type: ignore[operator]
            )
            else FormRegisterResponse(
                success=False,
                error=self._error_parser.parse(response.data.decode("utf-8")),
            )
        )


class LoginHandler:
    def __init__(
        self,
        graphql_query_resolver: GraphQLQueryResolver,
        graphql_error_parser: GraphQLLoginErrorParser,
        user_service: UserService,
    ):
        self._graphql_query_resolver = graphql_query_resolver
        self._graphql_error_parser = graphql_error_parser
        self._user_service = user_service

    def login(self, username: str, password: str) -> dict:
        login_operation_name = "ankiLogin"
        try:
            graphql_response = self._graphql_query_resolver.resolve(
                f"""\
mutation {login_operation_name}($username: String!, $password: String!, $deviceId: String!) {{
  login(login: $username, password: $password, deviceId: $deviceId) {{
    token
    user {{
      eid
      firstName
    }}
  }}
}}""",
                login_operation_name,
                {"username": username, "password": password, "deviceId": "anki"},
            )
        except GraphQLException as e:
            return {"errors": self._graphql_error_parser.parse(e)}

        errors: Union[GraphQLException, List, None] = graphql_response.data.get(
            "errors"
        )
        if errors:
            return {"errors": self._graphql_error_parser.parse(errors)}

        graphql_data = graphql_response.data.get("data", {}) or {}
        login_data = graphql_data.get("login", {}) or {}
        user_data = login_data.get("user", {}) or {}

        user_id = user_data.get("eid")
        token = login_data.get("token")

        if not user_id or not token:
            return {"errors": self._graphql_error_parser.parse(None)}

        self._user_service.login(user_id=user_id, token=token)

        return graphql_data

    def logout(self) -> None:
        # NOTE: deprecated, use UserService.logout directly
        self._user_service.logout()


class RegisterHandler:
    def __init__(
        self,
        reviewer,
        form_client: FormRegisterClient,
    ):
        self._reviewer = reviewer
        self._form_client = form_client

    def register(
        self, username: str, password: str, password_again: str
    ) -> FormRegisterResponse:
        return (
            FormRegisterResponse(success=False, error=_("Passwords don't match."))
            if password != password_again
            else self._form_client.register(username, password)
        )


class AuthDialog(QDialog):  # noqa: F405
    def __init__(
        self,
        main_window,
        web_server,
        login_url: str,
        onboarding_url: str,
        web_view: WebView,
        activity_service: ActivityService,
        meta_storage_adapter: MetaStorageAdapter,
        force_onboarding: bool = False,
    ):
        super().__init__(parent=main_window)
        self.setObjectName("amboss_auth_dialog")
        self._web_server = web_server
        self._title = _("AMBOSS")
        self._login_url = login_url
        self._onboarding_url = onboarding_url
        self._force_onboarding = force_onboarding
        self._layout = QVBoxLayout(self)  # noqa: F405
        self._web_view = web_view
        self._activity_service = activity_service
        self._meta_storage_adapter = meta_storage_adapter
        self._setup()
        amboss_did_firstrun.append(self.show_greeting)

    def show_greeting(self) -> None:
        if (
            not self._meta_storage_adapter.greeting_onboarding_v1_shown
            or self._force_onboarding
        ):
            self.show_onboarding()
            self._meta_storage_adapter.greeting_onboarding_v1_shown = True
        else:
            self.show_login()

    def show_onboarding(self) -> None:
        self._web_view.load(QUrl(self._onboarding_url))
        self.exec()

    def show_login(self) -> None:
        self._web_view.load(QUrl(self._login_url))
        self.exec()

    def _setup(self) -> None:
        self._layout.addWidget(self._web_view)  # signature broken?
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.resize(600, 730)
        self.setWindowTitle(self._title)

    def closeEvent(self, *args) -> None:
        """
        Called when window is closed by title bar close window, not if close programmatically or by CTA.
        """
        self._activity_service.register_activity("greeting_screen_dismiss")
        super().closeEvent(*args)


class LogoutDialog:
    def __init__(self, main_window):
        self._main_window = main_window

    def confirmed(self) -> bool:
        return askUser(
            _("Are you sure you want to log out?"),
            title=_("AMBOSS - Logout"),
            parent=self._main_window,
            defaultno=True,
        )
