from functools import cached_property
from hashlib import md5
from pathlib import Path
from typing import List, Union

from .base import FileLike, RootPath
from .errors import IsAFileError, MalformedURLError, RootNotFoundError


class LocalRoot(RootPath):
    raw: str
    name: str
    files: List["FileLike"]

    path: Path

    def __init__(self, path: Union[str, Path], recursive: bool = True) -> None:
        self.raw = str(path)
        try:
            if isinstance(path, str):
                self.path = Path(path)
            else:
                self.path = path
            if not self.path.is_dir():
                if self.path.is_file():
                    raise IsAFileError()
                else:
                    raise RootNotFoundError()
        except OSError:
            raise MalformedURLError()
        self.name = self.path.name
        self.files = self.list_files(recursive=recursive)

    def list_files(self, recursive: bool) -> List["FileLike"]:
        files: List["FileLike"] = []
        self.search_files(files, self.path, recursive)
        return files

    def search_files(self, files: List["FileLike"], src: Path, recursive: bool) -> None:
        for path in src.iterdir():
            if path.is_file():
                if len(path.suffix) > 1 and self.has_media_ext(path.suffix[1:]):
                    files.append(LocalFile(path))
            elif recursive and path.is_dir():
                self.search_files(files, path, recursive=True)


class LocalFile(FileLike):
    key: str  # == str(path)
    name: str
    extension: str

    path: Path

    def __init__(self, path: Path):
        self.key = str(path)
        self.name = path.name
        self.extension = path.suffix[1:]
        self.path = path

    @cached_property
    def size(self) -> int: # type: ignore
        return self.path.stat().st_size

    @cached_property
    def md5(self) -> str:
        return md5(self.read_bytes()).hexdigest()

    def read_bytes(self) -> bytes:
        return self.path.read_bytes()

    def is_identical(self, file: FileLike) -> bool:
        try:
            return file.size == self.size and file.md5 == self.md5  # type: ignore
        except AttributeError:
            return file.size == self.size
