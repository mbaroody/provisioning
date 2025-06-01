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


import json
from enum import Enum
from typing import NamedTuple, Optional

from aqt.qt import QObject, QThreadPool, QTimer

from .graphql import GraphQLClientException, GraphQLQueryResolver
from .hooks import (
    amboss_did_access_change,
    amboss_did_login,
    amboss_did_logout,
)
from .network import HTTPClientFactory, TokenAuth
from .profile import ProfileAdapter
from .qthreading import Worker
from .shared import safe_print

check_token_operation_name = "checkAnkiToken"
check_token_query = f"""\
query {check_token_operation_name} {{
  currentUser {{
    eid
  }}
}}
"""

study_objective_operation_name = "AnkiStudyObjective"
study_objective_query = f"""\
query {study_objective_operation_name} {{
  currentUser {{
    ... on User {{
      studyObjective {{
        superset
        label
      }}
    }}
  }}
}}
"""


class ArticleAccessTarget(Enum):
    platform_article = "platform_article"
    public_article = "public_article"
    no_article = "no_article"


class ArticleAccessHTTPClient:
    def __init__(
        self, url: str, token_auth: TokenAuth, http_client_factory: HTTPClientFactory
    ):
        self._token_auth = token_auth
        self._client = http_client_factory.create(url)

    def access_target(self) -> Optional[dict]:
        try:
            response = self._client.post(headers=self._token_auth.get_header())
            return json.loads(response.data.decode("utf-8"))
        except Exception:
            return None


class UserState(NamedTuple):
    is_logged_in: bool
    article_access_target: ArticleAccessTarget


class LoginStateResolver:
    def __init__(self, query_resolver: GraphQLQueryResolver):
        self._query_resolver = query_resolver

    def is_logged_in(self) -> bool:
        """Optimistic, i.e., if logged-in state can't be determined with certainty, assumes the user is logged in.
        """
        try:
            self._query_resolver.resolve(check_token_query, check_token_operation_name)
        except GraphQLClientException as e:
            if isinstance(e.message, dict):
                errors = e.message.get("errors")
                if not isinstance(errors, list):
                    return True
                for error in errors:
                    if (
                        isinstance(error, dict)
                        and error.get("message") == "permission.user_is_not_authorized"
                    ):
                        return False
        except:
            pass
        return True


class ArticleAccessResolver:
    def __init__(self, article_access_client: ArticleAccessHTTPClient):
        self._article_access_client = article_access_client

    def article_access(
        self,
        fallback_access: ArticleAccessTarget = ArticleAccessTarget.platform_article,
    ) -> ArticleAccessTarget:
        try:
            data = self._article_access_client.access_target()
            target = ArticleAccessTarget[data.get("target", fallback_access.value)]  # type: ignore[union-attr]
        except:
            return fallback_access
        return target


class UserStateResolver:
    def __init__(
        self,
        login_state_resolver: LoginStateResolver,
        article_access_resolver: ArticleAccessResolver,
    ):
        self._login_state_resolver = login_state_resolver
        self._article_access_resolver = article_access_resolver

    def user_state(self) -> UserState:
        """Optimistic, chooses conservative defaults if state can't be fully determined
        """
        is_logged_in = self._login_state_resolver.is_logged_in()
        return UserState(
            is_logged_in=is_logged_in,
            article_access_target=self._article_access_resolver.article_access(
                fallback_access=ArticleAccessTarget.platform_article
                if is_logged_in
                else ArticleAccessTarget.public_article
            ),
        )


class UserService:
    def __init__(
        self,
        profile: ProfileAdapter,
        token_auth: TokenAuth,
        login_state_resolver: LoginStateResolver,
    ):
        self._profile = profile
        self._token_auth = token_auth
        self._login_state_resolver = login_state_resolver
        self._article_access_target: ArticleAccessTarget = (
            ArticleAccessTarget.platform_article
        )
        amboss_did_login.append(self._on_amboss_did_login)
        amboss_did_logout.append(self._on_amboss_did_logout)

    def login(self, user_id: str, token: str) -> None:
        self._profile.id = user_id
        self._profile.token = token
        self.article_access_target = ArticleAccessTarget.platform_article
        amboss_did_login()

    def logout(self) -> None:
        self._profile.id = None
        self._profile.token = None
        self.article_access_target = ArticleAccessTarget.public_article
        amboss_did_logout()

    def is_logged_in(self, cached=True) -> bool:
        if not self._profile.id or not self._profile.token:
            return False
        if cached:
            return bool(self._profile.id and self._profile.token)
        return self._login_state_resolver.is_logged_in()

    def has_article_access(self):
        return (
            self.article_access_target
            == ArticleAccessTarget.platform_article
        )

    @property
    def article_access_target(self) -> ArticleAccessTarget:
        return self._article_access_target

    @article_access_target.setter
    def article_access_target(self, article_access_target) -> None:
        if article_access_target != self._article_access_target:
            self._article_access_target = article_access_target
            amboss_did_access_change()

    @property
    def user_id(self) -> Optional[str]:
        return self._profile.id

    @property
    def anon_id(self) -> str:
        return self._profile.anon_id

    def _on_amboss_did_login(self):
        self._token_auth.set_token(self._profile.token)
        self.article_access_target = ArticleAccessTarget.platform_article

    def _on_amboss_did_logout(self):
        self._token_auth.set_token(None)
        self.article_access_target = ArticleAccessTarget.public_article


class UserStateMutationObserver(QObject):
    def __init__(
        self,
        user_service: UserService,
        user_state_resolver: UserStateResolver,
        thread_pool: QThreadPool,
        parent: Optional[QObject] = None,
        poll_interval_ms: int = 60 * 1000,
    ):
        super().__init__(parent=parent)
        self._user_service = user_service
        self._user_state_resolver = user_state_resolver
        self._thread_pool = thread_pool
        self._timer = QTimer(parent=self)
        self._timer.setInterval(poll_interval_ms)

    def observe(self):
        amboss_did_login.append(self.start)
        amboss_did_logout.append(self.stop)

    def start(self):
        self._update()
        self._timer.start()
        self._timer.timeout.connect(self._update)

    def stop(self):
        self._timer.stop()

    def _update(self):
        worker = Worker(self._user_state_resolver.user_state)
        worker.signals.result.connect(self._callback)
        worker.signals.error.connect(lambda error: safe_print(f"{__file__}: {error}"))
        self._thread_pool.start(worker)

    def _callback(self, result: Optional[UserState], cancelled: bool) -> None:
        if not cancelled:
            if not isinstance(result, UserState):
                return
            if not result.is_logged_in:
                self._user_service.logout()
            if isinstance(result.article_access_target, ArticleAccessTarget):
                self._user_service.article_access_target = result.article_access_target


class StudyObjective(NamedTuple):
    value: Optional[str]
    label: Optional[str]


class StudyObjectiveService:
    def __init__(self, graphql_query_resolver: GraphQLQueryResolver):
        self._graphql_query_resolver = graphql_query_resolver

    def study_objective_value_and_label(self) -> StudyObjective:
        try:
            study_objective_response = self._graphql_query_resolver.resolve(
                query=study_objective_query,
                operation_name=study_objective_operation_name,
            )
            study_objective = (
                study_objective_response.data.get("data", {})
                .get("currentUser", {})
                .get("studyObjective", {})
            )
            superset = study_objective.get("superset")
            label = study_objective.get("label")
        except Exception as e:
            safe_print(f"Error fetching study objective: {e}")
            return StudyObjective(None, None)
        if superset == "step-1":
            return StudyObjective("step-1", "Step 1")
        if superset == "step-2" and label == "USMLE Step 3":
            return StudyObjective("step-2", "Step 3")
        if superset == "step-2":
            return StudyObjective("step-2", "Step 2 CK")
        return StudyObjective(None, None)
