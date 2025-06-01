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

import json
from typing import List, Optional

from urllib3.exceptions import HTTPError, HTTPWarning  # type: ignore[import]

from ..network import HTTPClientFactory, TokenAuth
from .model_notes import Notes
from .model_qbank import Question
from .performance import RequestOrigin


class MappingServiceHTTPClient:
    def __init__(
        self, url: str, token_auth: TokenAuth, http_client_factory: HTTPClientFactory
    ):
        self._token_auth = token_auth
        self._client = http_client_factory.create(url)

    def post(
        self,
        notes: Notes,
        max_question_count: Optional[int],
        study_objective: Optional[str],
        request_id: str,
        request_origin: RequestOrigin,
    ) -> Optional[dict]:
        data = {
            "notes": [n.dict() for n in notes],
            "max_question_count": max_question_count,
            "study_objective": study_objective,
            "request_origin": request_origin.value,
        }
        headers = {"Anki-Request-Id": request_id}
        auth_header = self._token_auth.get_header()
        if auth_header is not None:
            headers.update(auth_header)
        try:
            response = self._client.post(
                data=data,
                headers=headers,
                timeout=30,
            )
        except (HTTPError, HTTPWarning) as e:
            raise e
        try:
            return json.loads(response.data.decode("utf-8"))
        except ValueError as e:
            print(e)
            return None


class QBankMapperService:
    def __init__(self, mapping_service_client: MappingServiceHTTPClient):
        self._mapping_service_client = mapping_service_client

    def fetch_matching_questions(
        self,
        notes: Notes,
        request_id: str,
        request_origin: RequestOrigin,
        max_question_count: Optional[int] = None,
        study_objective: Optional[str] = None,
    ) -> List[Question]:
        if not notes:
            return []
        result = self._mapping_service_client.post(
            notes=notes,
            max_question_count=max_question_count,
            study_objective=study_objective,
            request_id=request_id,
            request_origin=request_origin,
        )
        if result is None:
            return []
        questions = result.get("questions")
        if questions is None:
            return []
        return [Question(**question) for question in questions]
