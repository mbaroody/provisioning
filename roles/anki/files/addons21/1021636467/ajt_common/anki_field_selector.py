# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from collections.abc import Iterable

from aqt import mw
from aqt.qt import *


def gather_all_field_names() -> Iterable[str]:
    for model in mw.col.models.all_names_and_ids():
        for field in mw.col.models.get(model.id)["flds"]:
            yield field["name"]


class AnkiFieldSelector(QComboBox):
    """
    An editable combobox prepopulated with all field names
    present in Note Types in the Anki collection.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setEditable(True)
        try:
            self.addItems(dict.fromkeys(gather_all_field_names()))
        except AttributeError:
            assert mw is None, "Anki can't be running."
            self.addItems(["Anki is not running"] * 5)
