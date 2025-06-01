# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import enum
from typing import Optional

from aqt.qt import *

from .utils import ui_translate


class EnumSelectCombo(QComboBox):
    def __init__(
        self,
        enum_type: Optional[enum.EnumMeta] = None,
        initial_value: Union[enum.Enum, str, None] = None,
        show_values: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        if enum_type is None:
            assert isinstance(initial_value, enum.Enum)
            enum_type = type(initial_value)
        # Note: The python 3.9 version of Anki does not support enum.EnumType
        assert isinstance(enum_type, enum.EnumMeta)
        for item in enum_type:
            self.addItem(ui_translate(item.value if show_values else item.name), item)
        if initial_value is not None:
            self.setCurrentName(initial_value)

    def setCurrentName(self, name: Union[enum.Enum, str]) -> None:
        for index in range(self.count()):
            if self.itemData(index) == name or self.itemData(index).name == name:
                return self.setCurrentIndex(index)

    def currentName(self) -> str:
        return self.currentData().name

    def setCurrentText(self, text: str) -> None:
        raise NotImplementedError()

    def currentText(self) -> str:
        raise NotImplementedError()
