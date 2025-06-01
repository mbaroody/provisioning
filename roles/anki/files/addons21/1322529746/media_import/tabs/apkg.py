from typing import Optional, TYPE_CHECKING

try:
    from anki.utils import is_win, is_lin
except ImportError:
    from anki.utils import isWin as is_win  # type: ignore
    from anki.utils import isLin as is_lin  # type: ignore

from aqt.qt import *
from aqt.utils import tooltip

from ..pathlike.apkg import ApkgRoot
from .base import ImportTab

if TYPE_CHECKING:
    from .base import ImportDialog


class ApkgTab(ImportTab):
    def __init__(self, dialog: "ImportDialog"):
        self.define_texts()
        ImportTab.__init__(self, dialog)

    def define_texts(self) -> None:
        self.button_text = "Browse"
        self.import_not_valid_tooltip = "Check if your path is correct"
        self.empty_input_msg = "Input a path"
        self.while_create_rootpath_msg = "Calculating number of files..."
        self.malformed_url_msg = "Invalid Path"
        self.root_not_found_msg = "File doesn't exist."
        self.is_a_directory_msg = "Path is a directory."

    def create_root_file(self, url: str) -> ApkgRoot:
        return ApkgRoot(url)

    def on_btn(self) -> None:
        path = self.get_apkg_path()
        if path is not None:
            self.path_input.setText(path)
            self.update_root_file()

    def on_input_change(self) -> None:
        self.update_root_file()

    # File Browse Dialog
    def file_name_filter(self) -> str:
        return f"Anki Deck Package (*.apkg)"

    def file_dialog(self) -> QFileDialog:
        dialog = QFileDialog(self)
        dialog.setNameFilter(self.file_name_filter())
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, False)
        if is_win or is_lin:
            dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        return dialog

    def get_apkg_path(self) -> Optional[str]:
        dialog = self.file_dialog()
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        if dialog.exec():
            # This can return multiple paths onccasionally. Qt bug?
            if not len(dialog.selectedFiles()) == 1:
                tooltip("Something went wrong. Please select the folder again.")
                return None
            path = dialog.selectedFiles()[0]
            return path
        else:
            return None
