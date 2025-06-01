import os
import traceback
import unicodedata
from concurrent.futures import Future
from datetime import datetime, timedelta
from typing import Callable, Dict, List, NamedTuple, Optional, Sequence, Tuple

import aqt
from anki.media import media_paths_from_col_path
from aqt.utils import askUserDialog
from requests.exceptions import RequestException

from .pathlike import FileLike, LocalRoot, RootPath
from .pathlike.errors import AddonError
from .pathlike.gdrive import GDriveRoot, gdrive

# if there are at least so many files in a gdrive directory, it will be downloaded as a zip file
GDRIVE_DOWNLOAD_AS_ZIP_THRESHOLD = 5


class ImportResult(NamedTuple):
    logs: List[str]
    success: bool


class ImportInfo:
    """Handles files_list count and their size"""

    files: list
    tot: int
    prev: int

    tot_size: int
    size: int
    prev_time: datetime
    prev_file_size: int

    def __init__(self, files: list) -> None:
        self.files = files
        self.tot = len(files)
        self.prev = self.tot
        self.diff = 0
        self.calculate_size()
        self.tot_size = self.size

    def update_count(self) -> int:
        """Returns `prev - curr`, then updates prev to curr"""
        self.diff = self.prev - self.curr
        self.prev = self.curr
        return self.diff

    def calculate_size(self) -> None:
        self.size = 0
        for file in self.files:
            self.size += file.size
        self.prev_time = datetime.now()
        self.prev_file_size = 0

    def update_size(self, file: FileLike) -> None:
        self.size -= file.size
        self.prev_file_size = file.size
        self.prev_time = datetime.now()

    @property
    def remaining_time_str(self) -> str:
        if not self.prev_file_size and self.prev_time:
            return ""
        timedelta = datetime.now() - self.prev_time
        estimate = timedelta * self.size / self.prev_file_size
        return self._format_timedelta(estimate)

    @property
    def size_str(self) -> str:
        return self._size_str(self.tot_size - self.size)

    @property
    def tot_size_str(self) -> str:
        return self._size_str(self.tot_size)

    @property
    def curr(self) -> int:
        return len(self.files)

    @property
    def left(self) -> int:
        return self.tot - self.curr

    def _format_timedelta(self, timedelta: timedelta) -> str:
        tot_secs = timedelta.seconds
        units = [60, 60 * 60, 60 * 60 * 24]
        seconds = tot_secs % units[0]
        minutes = (tot_secs % units[1]) // units[0]
        hours = (tot_secs % units[2]) // units[1]
        days = tot_secs // units[2]

        if days:
            time_str = f"{days}d {hours}h"
        elif hours:
            time_str = f"{hours}h {minutes}m"
        elif minutes:
            time_str = f"{minutes}m {seconds}s"
        else:
            time_str = f"{seconds}s"
        return time_str

    def _size_str(self, size: float) -> str:
        """Prints size of imported files."""
        for unit in ["Bytes", "KB", "MB", "GB"]:
            if size < 1000:
                return "%3.1f%s" % (size, unit)
            size = size / 1000
        return "%.1f%s" % (size, "TB")
        
def import_media(src: RootPath, on_done: Callable[[ImportResult], None]) -> None:
    """Import media from a directory, and its subdirectories."""
    MediaImporter().import_media(src, on_done)

class MediaImporter:

    def __init__(self) -> None:
        self._logs: List[str] = []
        self._on_done: Optional[Callable[[ImportResult], None]] = None
        self._info: Optional[ImportInfo] = None
        self._src: Optional[RootPath] = None
        self._files_list: Optional[List[FileLike]] = None

    def import_media(self, src: RootPath, on_done: Callable[[ImportResult], None]) -> None:
        """Import media from a directory, and its subdirectories."""
        self._on_done = on_done
        self._src = src

        try:
            self._import_media_part_1()
        except Exception as err:
            tb = traceback.format_exc()
            print(tb)
            print(str(err))
            self._logs.append(tb)
            self._logs.append(str(err))
            self._finish_import("", success=False)

    def _import_media_part_1(self) -> None:

        # Get the name of all media files.
        self._files_list = self._src.files
        self._info = ImportInfo(self._files_list)
        self._log(f"{self._info.tot} media files found.")

        # Normalize file names
        unnormalized = find_unnormalized_name(self._files_list)
        if len(unnormalized):
            self._finish_import(
                f"{len(unnormalized)} files have invalid file names: {[x.name for x in unnormalized]}",
                success=False,
            )
            return

        # Make sure there isn't a name conflict within new files.
        if name_conflict_exists(self._files_list):
            self._finish_import("There are multiple files with same filename.", success=False)
            return

        if self._info.update_count():
            self._log(f"{self._info.diff} files were skipped because they are identical.")

        # Check collection.media if there is a file with same name in the background
        # and then continue with part 2 of the import. 
        # (Checking for file conflicts can take quite a while and we don't want to block the UI.)
        aqt.mw.taskman.with_progress(
            task=lambda: name_exists_in_collection(self._files_list),
            on_done=self._import_media_part_2,
            label="Analyzing media files",
        )

    def _import_media_part_2(self, future: Future) -> None:
        name_conflicts = future.result()

        if len(name_conflicts):
            msg = f"{len(name_conflicts)} files have the same name as existing media files:"
            self._log(msg)

            max_file_amount_in_msg = 10
            name_conflict_truncated = name_conflicts[:max_file_amount_in_msg]
            file_names_str = ""
            for file in name_conflict_truncated:
                file_names_str += file.name + "\n"
            file_names_str += "...\n" if len(name_conflicts) > max_file_amount_in_msg else ""

            self._log(file_names_str + "-" * 16)
            ask_msg = msg + "\nDo you want to import the rest of the files?"
            diag = askUserDialog(ask_msg, buttons=["Abort Import", "Continue Import"])
            if diag.run() == "Abort Import":
                self._finish_import(
                    "Aborted import due to name conflict with existing media", success=False
                )
                return

        if self._info.update_count():
            diff = self._info.diff - len(name_conflicts)
            self._log(f"{diff} files were skipped because they already exist in collection.")

        # remove name conflicting files from total file count
        self._info.tot = len(self._info.files)

        if self._info.curr == 0:
            self._finish_import(f"{self._info.tot} media files were imported", success=True)
            return

        # Add media files in chunk in background.
        self._log(f"{self._info.curr} media files will be processed.")
        self._info.calculate_size()

        if (
            isinstance(self._src, GDriveRoot)
            and len(self._files_list) > GDRIVE_DOWNLOAD_AS_ZIP_THRESHOLD
        ):
            gdrive.download_folder_zip(self._src.id, self._finish_import)
        else:
            aqt.mw.taskman.with_progress(
                task=self._import_files_list, 
                on_done=self._on_import_done, 
                label="Importing"
            )
        

    def _import_files_list(self) -> Tuple[bool, str]:
        """returns (is_success, result msg)"""
        MAX_ERRORS = 5
        error_cnt = 0  # Count of errors in succession

        while True:
            # Last file was added
            if len(self._files_list) == 0:
                return (True, f"{self._info.tot} media files were imported.")

            # Abort import
            if aqt.mw.progress.want_cancel():
                return (
                    False,
                    f"Import aborted.\n{self._info.left} / {self._info.tot} media files were imported.",
                )

            progress_msg = (
                f"Adding media files ({self._info.left} / {self._info.tot})\n"
                f"{self._info.size_str}/{self._info.tot_size_str} "
                f"({self._info.remaining_time_str} left)"
            )
            aqt.mw.taskman.run_on_main(
                lambda: aqt.mw.progress.update(
                    label=progress_msg, value=self._info.left, max=self._info.tot
                )
            )

            file = self._files_list.pop(0)
            self._info.update_size(file)

            try:
                add_media(file)
                error_cnt = 0  # reset error_cnt on success
            except (AddonError, RequestException) as err:
                error_cnt += 1
                self._log("-" * 16 + "\n" + str(err) + "\n" + "-" * 16)
                if error_cnt > MAX_ERRORS:
                    self._log(f"{self._info.left} files were not imported.")
                    if self._info.left < 10:
                        for file in self._files_list:
                            self._log(file.name)
                    return (
                        False,
                        f"{self._info.left} / {self._info.tot} media files were imported.",
                    )
                else:
                    self._files_list.append(file)

    def _on_import_done(self, future: Future) -> None:
        try:
            (success, msg) = future.result()
            self._finish_import(msg, success)
        except Exception as err:
            raise err

    def _finish_import(self, msg: str, success: bool) -> None:
        self._log(msg)
        result = ImportResult(self._logs, success)
        aqt.mw.progress.finish()
        aqt.mw.col.media.check()
        self._on_done(result)

    def _log(self, msg: str) -> None:
        print(f"Media Import: {msg}")
        self._logs.append(msg)




def find_unnormalized_name(files: Sequence[FileLike]) -> List[FileLike]:
    """Returns list of files whose names are not normalized."""
    unnormalized = []
    for file in files:
        name = file.name
        normalized_name = unicodedata.normalize("NFC", name)
        if name != normalized_name:
            unnormalized.append(file)
    return unnormalized


def name_conflict_exists(files_list: List[FileLike]) -> bool:
    """Returns True if there are different files with the same name.
    And removes identical files from files_list so only one remains."""
    file_names: Dict[str, FileLike] = {}  # {file_name: file_path}
    identical: List[int] = []

    for idx, file in enumerate(files_list):
        name = file.name
        if name in file_names:
            if file.is_identical(file_names[name]):
                identical.append(idx)
            else:
                return True
        else:
            file_names[name] = file
    for idx in sorted(identical, reverse=True):
        files_list.pop(idx)
    return False


def name_exists_in_collection(files_list: List[FileLike]) -> List[FileLike]:
    """Returns list of files whose names conflict with existing media files.
    And remove files if identical file exists in collection."""
    media_dir = LocalRoot(media_paths_from_col_path(aqt.mw.col.path)[0], recursive=False)
    collection_file_paths = media_dir.files
    collection_files = {file.name: file for file in collection_file_paths}

    name_conflicts: List[FileLike] = []
    to_pop: List[int] = []

    for idx, file in enumerate(files_list):
        if file.name in collection_files:
            to_pop.append(idx)
            if not file.is_identical(collection_files[file.name]):
                name_conflicts.append(file)

    for idx in sorted(to_pop, reverse=True):
        files_list.pop(idx)
    return name_conflicts


def add_media(file: FileLike) -> bool:
    """
    Returns true if file was added.
    col.media.check() should be called at the end.
    """
    file_path = os.path.join(aqt.mw.col.media.dir(), file.name)
    if os.path.exists(file_path):
        return False
    with open(file_path, "wb") as f:
        data = file.read_bytes()
        f.write(data)
        return True
