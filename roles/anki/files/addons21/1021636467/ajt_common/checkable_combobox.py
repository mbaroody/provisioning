# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import enum
from collections.abc import Iterable, Sequence
from typing import Any

from aqt.qt import *

# Implementations
# https://gis.stackexchange.com/questions/350148/qcombobox-multiple-selection-pyqt5
# https://www.geeksforgeeks.org/pyqt5-checkable-combobox-showing-checked-items-in-textview/


MISSING = object()


class CheckableComboBox(QComboBox):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Initial state
        self._opened = False

        # Make the combo editable to set a custom text, but readonly
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)

        # Make the lineedit the same color as QPushButton
        palette = QApplication.palette()
        palette.setBrush(QPalette.ColorRole.Base, palette.button())
        self.lineEdit().setPalette(palette)

        # Use custom delegate and model
        self.setItemDelegate(QStyledItemDelegate())
        self.setModel(QStandardItemModel(self))

        # when any item get pressed
        qconnect(self.view().pressed, self.handle_item_pressed)

        # Update the text when an item is toggled
        qconnect(self.model().dataChanged, self.updateText)

        # Hide and show popup when clicking the line edit
        self.lineEdit().installEventFilter(self)

        # Prevent popup from closing when clicking on an item
        self.view().viewport().installEventFilter(self)

    def handle_item_pressed(self, index) -> None:
        """Check the pressed item if unchecked and vice-versa"""
        item: QStandardItem = self.model().itemFromIndex(index)
        if item.checkState() == Qt.CheckState.Checked:
            # reverse checked state on click.
            return item.setCheckState(Qt.CheckState.Unchecked)
        return item.setCheckState(Qt.CheckState.Checked)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Recompute text to elide as needed"""
        self.updateText()
        super().resizeEvent(event)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.MouseButtonRelease:
            if obj == self.lineEdit():
                self.togglePopup()
                return True
            if obj == self.view().viewport():
                return True
        return False

    def togglePopup(self) -> None:
        return self.hidePopup() if self._opened else self.showPopup()

    def showPopup(self) -> None:
        """When the popup is displayed, a click on the lineedit should close it"""
        super().showPopup()
        self._opened = True

    def hidePopup(self) -> None:
        super().hidePopup()
        self._opened = False
        # Used to prevent immediate reopening when clicking on the lineEdit
        self.startTimer(100)
        # Refresh the display text when closing
        self.updateText()

    def timerEvent(self, event):
        """After timeout, kill timer, and re-enable click on line-edit"""
        self.killTimer(event.timerId())
        self._opened = False

    def updateText(self):
        self.lineEdit().setText(", ".join(self.checkedTexts()))

    def addCheckableText(self, text: str):
        return self.addCheckableItem(text)

    def addCheckableItem(self, text: str, data: Any = MISSING) -> None:
        item = QStandardItem()
        item.setText(text)
        item.setCheckable(True)
        item.setEnabled(True)
        item.setCheckState(Qt.CheckState.Unchecked)
        if data is not MISSING:
            item.setData(data)
        self.model().appendRow(item)

    def setCheckableTexts(self, texts: Iterable[str]) -> None:
        self.clear()
        for text in texts:
            self.addCheckableText(text)

    def items(self) -> Iterable[QStandardItem]:
        return (self.model().item(i) for i in range(self.model().rowCount()))

    def checkedItems(self) -> Sequence[QStandardItem]:
        return tuple(item for item in self.items() if item.checkState() == Qt.CheckState.Checked)

    def checkedData(self) -> Sequence[Any]:
        return tuple(item.data() for item in self.checkedItems())

    def checkedTexts(self) -> Sequence[str]:
        return tuple(item.text() for item in self.checkedItems())

    def setCheckedTexts(self, texts: Sequence[str]):
        for item in self.items():
            item.setCheckState(Qt.CheckState.Checked if (item.text() in texts) else Qt.CheckState.Unchecked)

    def setCheckedData(self, data_items: Union[Sequence[Any], enum.Flag]):
        for item in self.items():
            item.setCheckState(Qt.CheckState.Checked if (item.data() in data_items) else Qt.CheckState.Unchecked)


class ChkComboTryWindow(QDialog):
    items = (
        "Milk",
        "Eggs",
        "Butter",
        "Cheese",
        "Yogurt",
        "Chicken",
        "Fish",
        "Potatoes",
        "Carrots",
        "Onions",
        "Garlic",
        "Sugar",
        "Salt",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle("Test playground")
        self.setLayout(main_layout := QVBoxLayout())
        combo_box = CheckableComboBox()
        print_button = QPushButton("Print Values")
        main_layout.addWidget(combo_box)
        main_layout.addWidget(print_button)
        combo_box.setCheckableTexts(self.items)
        combo_box.setCheckedTexts(self.items[3:6])
        qconnect(print_button.clicked, lambda: print("\n".join(combo_box.checkedTexts())))


def main():
    app = QApplication(sys.argv)
    window = ChkComboTryWindow()
    window.show()
    window.resize(480, 320)
    app.exit(app.exec())


if __name__ == "__main__":
    main()
