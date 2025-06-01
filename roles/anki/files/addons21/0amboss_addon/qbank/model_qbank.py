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


from enum import Enum
from typing import List, NamedTuple, Optional

from ..graphql import GraphQLClientException, GraphQLErrorCode


class Tag(NamedTuple):
    namespace: str
    key: str
    value: str
    label: str

    def __repr__(self):
        return f"{self.label} ({self.namespace}:{self.key}={self.value})"


class Question(NamedTuple):
    id: str
    score: float
    preview_text: Optional[str]
    preview_url: Optional[str]
    tags: List[Tag]


class QuestionSessionError(Enum):
    empty_session = "empty_session"
    not_authenticated = "not_authenticated"
    not_authorized = "not_authorized"
    unknown = "unknown"


class QuestionSessionMeta(NamedTuple):
    error: Optional[QuestionSessionError]
    session_id: Optional[str]
    question_ids: List[str]

    @classmethod
    def from_graphql_client_exception(cls, exception: GraphQLClientException):
        message = exception.message
        if not isinstance(message, dict):
            return cls(
                error=QuestionSessionError.unknown, session_id=None, question_ids=[]
            )
        errors = message.get("errors", [])
        if len(errors) != 1:
            return cls(
                error=QuestionSessionError.unknown, session_id=None, question_ids=[]
            )
        message = errors[0].get("message")
        if message == GraphQLErrorCode.not_authenticated.value:
            return cls(
                error=QuestionSessionError.not_authenticated,
                session_id=None,
                question_ids=[],
            )
        if message == GraphQLErrorCode.not_authorized.value:
            return cls(
                error=QuestionSessionError.not_authorized,
                session_id=None,
                question_ids=[],
            )
        if message == GraphQLErrorCode.empty_session.value:
            return cls(
                error=QuestionSessionError.empty_session,
                session_id=None,
                question_ids=[],
            )
        return cls(error=QuestionSessionError.unknown, session_id=None, question_ids=[])

    @classmethod
    def from_data_dict(cls, data: dict):
        question_session_meta_data = data.get("data", {}).get(
            "createCustomQuestionSession", {}
        )
        session_id = question_session_meta_data.get("eid")
        question_ids = question_session_meta_data.get("questionIds", [])
        if not session_id or not question_ids:
            return cls(
                error=QuestionSessionError.unknown, session_id=None, question_ids=[]
            )
        return cls(
            error=None,
            session_id=session_id,
            question_ids=question_ids,
        )


class QuestionStatus(Enum):
    UNSEEN_OR_SKIPPED = "unseenOrSkipped"
    ANSWERED_INCORRECTLY = "answeredIncorrectly"
    ANSWERED_CORRECTLY_WITH_HELP = "answeredCorrectlyWithHelp"
    ANSWERED_CORRECTLY = "answeredCorrectly"


class QuestionDifficulty(Enum):
    DIFFICULTY0 = "difficulty0"
    DIFFICULTY1 = "difficulty1"
    DIFFICULTY2 = "difficulty2"
    DIFFICULTY3 = "difficulty3"
    DIFFICULTY4 = "difficulty4"


class QuestionOrder(Enum):
    RANDOM = "random"
    LATEST_FIRST = "latestFirst"
    OLDEST_FIRST = "oldestFirst"
    INITIAL = "initial"
