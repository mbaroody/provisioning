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

from typing import Dict, List, Optional, Union

from ..graphql import GraphQLClientException, GraphQLQueryResolver
from ..shared import _
from .model_qbank import (
    QuestionDifficulty,
    QuestionOrder,
    QuestionSessionMeta,
    QuestionStatus,
)
from .performance import RequestOrigin

question_session_size_name = "AnkiQuestionSessionSize"
question_session_size_query = f"""\
query {question_session_size_name}(
  $questionIds: [ID!]!,
  $statusCriterion: QuestionStatusCriterion,
  $difficulties: [Difficulty!],
  $maxSize: Int
) {{
  questionSessionCustomSize(
    criteria: {{
      questionIds: $questionIds
      statusCriterion: $statusCriterion
      difficulties: $difficulties
      maxSize: $maxSize
    }}
  )
}}"""

question_session_name = "AnkiQuestionSession"
question_session_query = f"""\
mutation {question_session_name}(
  $title: String!,
  $questionIds: [ID!]!,
  $statusCriterion: QuestionStatusCriterion,
  $difficulties: [Difficulty!],
  $maxSize: Int,
  $order: QuestionOrder!
) {{
  createCustomQuestionSession(
    title: $title
    mode: guidance
    criteria: {{
      questionIds: $questionIds
      statusCriterion: $statusCriterion
      difficulties: $difficulties
      maxSize: $maxSize
      order: $order
    }}
    type: anki
  ) {{
    ...on  QuestionSession {{
      eid
      questionIds
    }}
  }}
}}"""


def get_question_status_criterion(
    statuses: Optional[List[QuestionStatus]] = None,
) -> Optional[Dict[str, Union[List[str], str]]]:
    return (
        {"resultSet": "all", "statuses": [status.value for status in statuses]}
        if statuses is not None
        else None
    )


def get_question_difficulties(
    difficulties: Optional[List[QuestionDifficulty]] = None,
) -> Optional[List[str]]:
    return (
        [difficulty.value for difficulty in difficulties]
        if difficulties is not None
        else None
    )


def get_title(
    request_origin: Optional[RequestOrigin], note_count: Optional[int]
) -> str:
    if request_origin == RequestOrigin.anki_home_qbank_widget:
        return _("Anki home screen session")
    if request_origin in (
        RequestOrigin.anki_card_browser_toolbar_button,
        RequestOrigin.anki_card_browser_sidebar_menu,
    ):
        if not note_count:
            return _("Anki browser session")
        if note_count == 1:
            return _("Anki browser session, based on 1 note")
        return _("Anki browser session, based on {note_count} notes").format(
            note_count=note_count,
        )
    return _("Anki session")


class QBankSessionService:
    def __init__(
        self,
        graphql_query_resolver: GraphQLQueryResolver,
        base_url: str = "https://next.amboss.com/us",
    ):
        self._graphql_query_resolver = graphql_query_resolver
        self._base_url = base_url

    def get_question_session_size(
        self,
        question_ids: List[str],
        max_size: Optional[int] = None,
        statuses: Optional[List[QuestionStatus]] = None,
        difficulties: Optional[List[QuestionDifficulty]] = None,
    ) -> Optional[int]:
        response = self._graphql_query_resolver.resolve(
            question_session_size_query,
            question_session_size_name,
            {
                "questionIds": question_ids,
                "maxSize": max_size,
                "statusCriterion": get_question_status_criterion(statuses=statuses),
                "difficulties": get_question_difficulties(difficulties=difficulties),
            },
        )
        size = response.data.get("data", {}).get("questionSessionCustomSize")
        # FIXME: size=0 both signals no remaining questions and possibly internal error?
        return int(size) if size is not None else None

    def get_question_session_meta(
        self,
        question_ids: List[str],
        order: QuestionOrder = QuestionOrder.INITIAL,
        max_size: Optional[int] = None,
        statuses: Optional[List[QuestionStatus]] = None,
        difficulties: Optional[List[QuestionDifficulty]] = None,
        request_origin: Optional[RequestOrigin] = None,
        note_count: Optional[int] = None,
    ) -> QuestionSessionMeta:
        try:
            response = self._graphql_query_resolver.resolve(
                question_session_query,
                question_session_name,
                {
                    "title": get_title(
                        request_origin=request_origin, note_count=note_count
                    ),
                    "questionIds": question_ids,
                    "maxSize": max_size,
                    "order": order.value,
                    "statusCriterion": get_question_status_criterion(statuses=statuses),
                    "difficulties": get_question_difficulties(
                        difficulties=difficulties
                    ),
                },
            )
        except GraphQLClientException as e:
            return QuestionSessionMeta.from_graphql_client_exception(e)
        return QuestionSessionMeta.from_data_dict(response.data)

    def get_question_session_url(
        self, question_session_id: str, request_origin: RequestOrigin
    ) -> str:
        return (
            f"{self._base_url}/questions/{question_session_id}/1"
            f"?utm_source=anki&utm_medium={request_origin.value}"
        )
