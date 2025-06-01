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

from typing import Dict, Final, List, NamedTuple, Optional

import qtawesome as qta  # type: ignore[import]
from aqt.qt import (
    QCheckBox,
    QHBoxLayout,
    QIcon,
    QLabel,
    QSize,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
    pyqtSignal,
)

from ...shared import _
from ..icons import get_amboss_pixmap, get_composite_pixmap
from ..model_qbank import QuestionDifficulty, QuestionStatus
from .shared import create_checkbox_selection_state_guard


class QuestionStatusProperties(NamedTuple):
    label: str
    color: str


class QuestionDifficultyProperties(NamedTuple):
    hammers: int


QUESTION_STATUS_PROPERTIES: Final[Dict[QuestionStatus, QuestionStatusProperties]] = {
    QuestionStatus.UNSEEN_OR_SKIPPED: QuestionStatusProperties(
        label=_("Not yet answered"), color="#aeb9c6"
    ),
    QuestionStatus.ANSWERED_CORRECTLY_WITH_HELP: QuestionStatusProperties(
        label=_("Answered correctly using hints"), color="#f1d56b"
    ),
    QuestionStatus.ANSWERED_INCORRECTLY: QuestionStatusProperties(
        label=_("Answered incorrectly"), color="#ee6160"
    ),
    QuestionStatus.ANSWERED_CORRECTLY: QuestionStatusProperties(
        label=_("Answered correctly"), color="#0dbf8f"
    ),
}

QUESTION_DIFFICULTY_PROPERTIES: Final[
    Dict[QuestionDifficulty, QuestionDifficultyProperties]
] = {
    QuestionDifficulty.DIFFICULTY0: QuestionDifficultyProperties(hammers=1),
    QuestionDifficulty.DIFFICULTY1: QuestionDifficultyProperties(hammers=2),
    QuestionDifficulty.DIFFICULTY2: QuestionDifficultyProperties(hammers=3),
    QuestionDifficulty.DIFFICULTY3: QuestionDifficultyProperties(hammers=4),
    QuestionDifficulty.DIFFICULTY4: QuestionDifficultyProperties(hammers=5),
}


class QuestionCriteriaWidget(QWidget):
    criteria_changed = pyqtSignal()

    def __init__(
        self,
        question_statuses: List[QuestionStatus],
        question_difficulties: List[QuestionDifficulty],
        night_mode: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        layout_main = QHBoxLayout()
        layout_main.setContentsMargins(0, 0, 0, 0)
        layout_status = QVBoxLayout()
        layout_difficulty = QVBoxLayout()

        layout_main.addLayout(layout_status)
        layout_main.addSpacerItem(
            QSpacerItem(20, 32, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        )
        layout_main.addLayout(layout_difficulty)
        self.setLayout(layout_main)

        font_label = self.font()
        font_label.setPointSize(10)

        label_status = QLabel(text=_("Status").upper(), parent=self)
        label_status.setFont(font_label)
        layout_status.addWidget(label_status)
        self._question_status_map: Dict[QuestionStatus, QCheckBox] = {}

        for status in QuestionStatus:
            status_props = QUESTION_STATUS_PROPERTIES[status]
            checkbox = QCheckBox(status_props.label, parent=self)
            checkbox.setIcon(qta.icon("mdi.circle", color=status_props.color))
            checkbox.setObjectName(f"checkbox_{status.name.lower()}")
            layout_status.addWidget(checkbox)
            self._question_status_map[status] = checkbox

        layout_status.addSpacerItem(
            QSpacerItem(20, 32, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        )

        label_difficulty = QLabel(text=_("Difficulty").upper(), parent=self)
        label_difficulty.setFont(font_label)
        layout_difficulty.addWidget(label_difficulty)
        hammer_pixmap = get_amboss_pixmap(
            "hammer.png" if not night_mode else "hammer_dark.png"
        )
        self._question_difficulty_map: Dict[QuestionDifficulty, QCheckBox] = {}

        for difficulty in QuestionDifficulty:
            difficulty_props = QUESTION_DIFFICULTY_PROPERTIES[difficulty]
            checkbox = QCheckBox(self)
            checkbox.setIconSize(QSize(100, 16))
            checkbox.setIcon(
                QIcon(
                    get_composite_pixmap([hammer_pixmap] * difficulty_props.hammers, 8)
                )
            )
            checkbox.setObjectName(f"checkbox_{difficulty.name.lower()}")
            layout_difficulty.addWidget(checkbox)
            self._question_difficulty_map[difficulty] = checkbox

        for group in [
            self._question_status_map.values(),
            self._question_difficulty_map.values(),
        ]:
            for checkbox in group:
                checkbox.clicked.connect(
                    create_checkbox_selection_state_guard(
                        checkbox, group, signal_on_change=self.criteria_changed
                    )
                )

        self.set_question_statuses(question_statuses)
        self.set_question_difficulties(question_difficulties)

    def set_question_statuses(self, question_statuses: List[QuestionStatus]):
        for status, checkbox in self._question_status_map.items():
            checkbox.setChecked(status in question_statuses)

    def set_question_difficulties(
        self, question_difficulties: List[QuestionDifficulty]
    ):
        for difficulty, checkbox in self._question_difficulty_map.items():
            checkbox.setChecked(difficulty in question_difficulties)

    def get_question_statuses(self) -> List[QuestionStatus]:
        return [
            status
            for status, checkbox in self._question_status_map.items()
            if checkbox.isChecked()
        ]

    def get_question_difficulties(self) -> List[QuestionDifficulty]:
        return [
            difficulty
            for difficulty, checkbox in self._question_difficulty_map.items()
            if checkbox.isChecked()
        ]
