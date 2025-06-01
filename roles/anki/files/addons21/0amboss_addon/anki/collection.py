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

from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Literal,
    Optional,
    TypedDict,
    cast,
)

if TYPE_CHECKING:
    from anki.collection import Collection, OpChanges
    from anki.dbproxy import DBProxy
    from aqt.main import AnkiQt

from .errors import IMPORT_ERRORS

if TYPE_CHECKING:
    from anki.models import NotetypeId
else:
    try:
        from anki.models import NotetypeId  # 2.1.45+
    except IMPORT_ERRORS:
        NotetypeId = int


class FieldDict(TypedDict):
    """Abridged version of Anki type, limited to keys we use"""

    name: str


class TemplateDict(TypedDict):
    """Abridged version of Anki type, limited to keys we use"""

    name: str
    qfmt: str
    afmt: str


class NotetypeDict(TypedDict):
    """Abridged version of Anki type, limited to keys we use"""

    id: int
    name: str
    flds: List[FieldDict]
    tmpls: List[TemplateDict]


class CardSide(Enum):
    QUESTION = "qfmt"
    ANSWER = "afmt"


class AnkiCollectionException(Exception):
    pass


class AnkiCollectionService:
    db_separator = "\u001F"

    def __init__(self, main_window: "AnkiQt"):
        self._main_window = main_window

    @property
    def collection(self) -> "Collection":
        if self._main_window.col is None:
            raise AnkiCollectionException("Anki collection not available")
        return self._main_window.col

    @property
    def database(self) -> "DBProxy":
        if self.collection.db is None:
            raise AnkiCollectionException("Anki database not available")
        return self.collection.db

    @property
    def day_cutoff(self) -> int:
        scheduler = self.collection.sched
        try:
            return scheduler.day_cutoff  # type: ignore
        except AttributeError:
            return scheduler.dayCutoff


class AnkiNotetypeService:
    def __init__(self, collection_service: AnkiCollectionService):
        self._collection_service = collection_service

    @property
    def model_manager(self):
        return self._collection_service.collection.models

    def get_all_notetypes(self) -> List[NotetypeDict]:
        return [cast(NotetypeDict, d) for d in self.model_manager.all()]

    def get_all_notetype_ids(self) -> List[int]:
        model_manager = self.model_manager
        if not hasattr(model_manager, "all_names_and_ids"):  # <2.1.28
            return [int(item) for item in model_manager.models.keys()]
        return [item.id for item in model_manager.all_names_and_ids()]

    def update_notetype(self, notetype: NotetypeDict) -> Optional["OpChanges"]:
        untyped_notetype = cast(Dict[str, Any], notetype)
        try:  # 2.1.45+
            return self.model_manager.update_dict(untyped_notetype)  # OpChanges
        except AttributeError:
            return self.model_manager.save(untyped_notetype)  # None

    def get_notetype(self, notetype_id: int) -> Optional[NotetypeDict]:
        untyped_notetype = self.model_manager.get(NotetypeId(notetype_id))
        return cast(NotetypeDict, untyped_notetype)

    # NOTE: The following static methods are meant to provide some added API stability
    # to guard against changes in Anki's dictionary interface to concepts like
    # notetypes, as Anki is poised to move to custom DTOs for these in the future.
    # TODO: As this is not an ideal approach, we should evaluate switching to custom
    # DTOs rather than returning the underlying Anki dictionary-like objects directly,
    # and then having to process them using these getters.
    # When doing so, we need to consider the performance impact of instantiating the
    # objects in question on demand in performance-critical loops

    @staticmethod
    def get_templates(notetype: NotetypeDict) -> List[TemplateDict]:
        return notetype["tmpls"] or []

    @staticmethod
    def get_fields(notetype: NotetypeDict) -> List[FieldDict]:
        return notetype["flds"] or []

    @staticmethod
    def get_name(notetype: NotetypeDict) -> str:
        return notetype["name"] or ""

    @staticmethod
    def get_template_side(template: TemplateDict, card_side: CardSide) -> Optional[str]:
        key: Literal["afmt", "qfmt"] = card_side.value  # TypedDicts can be stupid
        return template.get(key)

    @staticmethod
    def set_template_side(template: TemplateDict, card_side: CardSide, content: str):
        template[card_side.value] = content
