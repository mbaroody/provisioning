import os
from concurrent.futures import Future
from pathlib import Path
from typing import List, Tuple

from aqt import mw
from aqt.qt import *
from aqt.utils import getText, tooltip

from .api_key import get_google_api_key
from .constants import ADDON_NAME
from .exporter import MediaExporter

os.environ["GOOGLE_API_KEY"] = get_google_api_key()
from .pathlike.gdrive import GDriveRoot


def get_export_folder() -> str:
    "Get the export folder from the user."
    return QFileDialog.getExistingDirectory(
        mw, caption="Choose the folder where you want to export the files to"
    )


def get_gdrive_files_in_background(on_done: Callable) -> None:
    url, succeded = getText("Enter the path to the GDrive folder")
    if not succeded:
        return

    def get_gdrive_file_list(url: str) -> Tuple[List[str], bool]:
        # Returns a list of files in the GDrive folder and if the user cancelled
        result: List[str] = []

        ctr = 0
        progress_step = 100
        for file in GDriveRoot(url).list_files(recursive=True):
            if mw.progress.want_cancel():
                return [], True

            ctr += 1
            if ctr % progress_step == 0:
                mw.taskman.run_on_main(
                    lambda ctr=ctr: mw.progress.update(  # type: ignore
                        label=(
                            "Looking up files in Google drive...<br>"
                            f"Found {ctr} files..."
                        )
                    )
                )

            result.append(file.name)
        return result, False

    mw.taskman.with_progress(
        label="Looking up files in Google drive...",
        task=lambda: get_gdrive_file_list(url),
        on_done=on_done,
    )


def export_media(exporter: MediaExporter) -> None:

    export_path = get_export_folder()
    if not export_path:
        tooltip("Cancelled Media Export.")
        return

    want_cancel = False

    def export_task() -> int:
        note_count = exporter.note_count()
        progress_step = min(2500, max(2500, note_count))
        total_file_count = 0
        for notes_i, (total_file_count, _) in enumerate(
            exporter.export(Path(export_path))
        ):
            if notes_i % progress_step == 0:
                mw.taskman.run_on_main(
                    lambda notes_i=notes_i + 1, media_i=total_file_count: update_progress(  # type: ignore
                        notes_i, note_count, media_i
                    )
                )
                if want_cancel:
                    break
        return total_file_count

    def update_progress(notes_i: int, note_count: int, media_i: int) -> None:
        nonlocal want_cancel
        mw.progress.update(
            label=f"Processed {notes_i} notes and exported {media_i} files",
            max=note_count,
            value=notes_i,
        )
        want_cancel = mw.progress.want_cancel()

    def on_done(future: Future) -> None:
        try:
            count = future.result()
        finally:
            mw.progress.finish()
        tooltip(f"Exported {count} media files.")

    mw.progress.start(label="Exporting media...")
    mw.progress.set_title(ADDON_NAME)
    mw.taskman.run_in_background(export_task, on_done=on_done)
