# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from typing import Optional

from aqt.qt import *


def mod_mask_qt5():
    return Qt.Modifier.CTRL | Qt.Modifier.ALT | Qt.Modifier.SHIFT | Qt.Modifier.META


def mod_mask_qt6():
    return (
        Qt.KeyboardModifier.ControlModifier
        | Qt.KeyboardModifier.AltModifier
        | Qt.KeyboardModifier.ShiftModifier
        | Qt.KeyboardModifier.MetaModifier
    )


def forbidden_keys():
    return (
        Qt.Key.Key_Shift,
        Qt.Key.Key_Alt,
        Qt.Key.Key_Control,
        Qt.Key.Key_Meta,
    )


def modifiers_allowed(modifiers) -> bool:
    try:
        return modifiers & mod_mask_qt5() == modifiers
    except TypeError:
        return modifiers & mod_mask_qt6() == modifiers  # Qt6


def to_int(modifiers) -> int:
    try:
        return int(modifiers)
    except TypeError:
        return int(modifiers.value)  # Qt6


class KeyPressDialog(QDialog):
    value_accepted = pyqtSignal(str)

    def __init__(self, parent: QWidget = None, initial_value: str = None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self._shortcut = initial_value
        self.setMinimumSize(380, 64)
        self.setWindowTitle("Grab key combination")
        self.setLayout(self._make_layout())

    @staticmethod
    def _make_layout() -> QLayout:
        label = QLabel(
            "Please press the key combination you would like to assign.\n"
            "Supported modifiers: CTRL, ALT, SHIFT or META.\n"
            "Press ESC to delete the shortcut."
        )
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout = QVBoxLayout()
        layout.addWidget(label)
        return layout

    def _accept_value(self, value: Optional[str]) -> None:
        self.set_value(value)
        self.accept()

    def set_value(self, value: Optional[str]) -> None:
        self._shortcut = value
        self.value_accepted.emit(value)  # type: ignore

    def keyPressEvent(self, event: QKeyEvent) -> None:
        # https://stackoverflow.com/questions/35033116
        key = int(event.key())
        modifiers = event.modifiers()

        if key == Qt.Key.Key_Escape:
            self._accept_value(None)
        elif modifiers and modifiers_allowed(modifiers) and key > 0 and key not in forbidden_keys():
            self._accept_value(QKeySequence(to_int(modifiers) + key).toString())

    def value(self) -> Optional[str]:
        return self._shortcut


class ShortCutGrabButton(QPushButton):
    _placeholder = "[Not assigned]"

    def __init__(self, initial_value: str = None):
        super().__init__(initial_value or self._placeholder)
        self._dialog = KeyPressDialog(self, initial_value)
        qconnect(self.clicked, self._dialog.exec)
        qconnect(
            self._dialog.value_accepted,
            lambda value: self.setText(value or self._placeholder),
        )

    def setValue(self, value: str):
        self._dialog.set_value(value)

    def value(self) -> str:
        return self._dialog.value() or ""


def detect_keypress():
    app = QApplication(sys.argv)
    w = QDialog()
    w.setWindowTitle("Test")
    w.setLayout(layout := QVBoxLayout())
    layout.addWidget(b := ShortCutGrabButton())
    w.show()
    code = app.exec()
    print(f"{'Accepted' if w.result() else 'Rejected'}. Code: {code}, shortcut: \"{b.value()}\"")
    sys.exit(code)


if __name__ == "__main__":
    detect_keypress()
