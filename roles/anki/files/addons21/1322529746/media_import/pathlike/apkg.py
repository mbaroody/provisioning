import json
import zipfile
from functools import cached_property
from hashlib import md5
from pathlib import Path
from typing import Dict, List, Union

from .base import FileLike, RootPath
from .errors import (IncompatibleApkgFormatError, IsADirectoryError,
                     MalformedURLError, RootNotFoundError)


class ApkgRoot(RootPath):
    raw: str
    name: str
    files: List["FileLike"]
    path: Path
    zip_file: zipfile.ZipFile

    def __init__(self, path: Union[str, Path]) -> None:
        self.raw = str(path)
        try:
            if isinstance(path, str):
                self.path = Path(path)
            else:
                self.path = path
            if not self.path.is_file():
                if self.path.is_dir():
                    raise IsADirectoryError()
                else:
                    raise RootNotFoundError()
            if not self.path.suffix == ".apkg":
                raise MalformedURLError()
        except OSError:
            raise MalformedURLError()
        self.name = self.path.name
        self.zip_file = zipfile.ZipFile(self.path, "r")
        self.files = self.list_files()

    def list_files(self) -> List["FileLike"]:
        # The media file contains a mapping from media filenames inside the zip file to the original filenames.
        old_to_new_name = self._media_dict()
        zip_file = zipfile.ZipFile(self.path, "r")
        files: List["FileLike"] = [
            FileInZip(new, zip_file=zip_file, name_in_zip=old)
            for old, new in old_to_new_name.items()
        ]
        return files

    def _media_dict(self) -> Dict[str, str]:
        try:
            # old media file format (json)
            result = json.loads(self.zip_file.read("media").decode("utf-8"))
        except UnicodeDecodeError:
            raise IncompatibleApkgFormatError()
        return result


class FileInZip(FileLike):
    name: str
    extension: str
    _name_in_zip: str
    _zip_file: zipfile.ZipFile

    def __init__(
        self,
        name: str,
        zip_file: zipfile.ZipFile,
        name_in_zip: str,
    ):
        self.name = name
        self.extension = name.split(".")[-1]
        self._zip_file = zip_file 
        self._name_in_zip = name_in_zip

    @cached_property
    def size(self) -> int:  # type: ignore
        return self._zip_file.getinfo(self._name_in_zip).file_size

    @cached_property
    def md5(self) -> str:
       return md5(self.read_bytes()).hexdigest()

    def read_bytes(self) -> bytes:
        return self._zip_file.read(self._name_in_zip)

    def is_identical(self, file: FileLike) -> bool:
        try:
            return file.size == self.size and file.md5 == self.md5 # type: ignore
        except AttributeError:
            return file.size == self.size
