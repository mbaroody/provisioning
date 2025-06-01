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

from dataclasses import dataclass, field
from typing import List

from ..model_qbank import QuestionDifficulty, QuestionOrder, QuestionStatus


@dataclass
class QuestionSelectionOptions:
    count: int = 10  # Number of questions to include in session
    statuses: List[QuestionStatus] = field(
        default_factory=lambda: [QuestionStatus.UNSEEN_OR_SKIPPED]
    )  # List of selected statuses, limit to new Qs by default
    difficulties: List[QuestionDifficulty] = field(
        default_factory=lambda: list(QuestionDifficulty)
    )  # List of selected difficulties, include all by default
    order: QuestionOrder = QuestionOrder.INITIAL  # Order of questions in session
