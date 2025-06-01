# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import functools
import os
import shutil
from typing import Callable, Optional, Union

from aqt.qt import pyqtBoundSignal, pyqtSignal


def ui_translate(key: str) -> str:
    return key.capitalize().replace("_", " ").replace("Html", "HTML").replace("Svg", "SVG").replace("Url", "URL")


HARDCODED_PATHS = (
    "/usr/bin",
    "/opt/homebrew/bin",
    "/usr/local/bin",
    "/bin",
    os.path.join(os.getenv("HOME", "/home/user"), ".local", "bin"),
)


def find_executable_hardcoded(name: str) -> Optional[str]:
    for path_to_dir in HARDCODED_PATHS:
        if os.path.isfile(path_to_exe := os.path.join(path_to_dir, name)):
            return path_to_exe
    return None


@functools.cache
def find_executable(name: str) -> Optional[str]:
    """
    If possible, use the executable installed in the system.
    Otherwise, try fallback paths.
    """
    return shutil.which(name) or find_executable_hardcoded(name)


def clamp(min_val: int, val: int, max_val: int) -> int:
    return max(min_val, min(val, max_val))


MISSING = object()


def q_emit(signal: Union[Callable, pyqtSignal, pyqtBoundSignal], value=MISSING) -> None:
    """Helper to work around type checking not working with signal.emit(func)."""
    if value is not MISSING:
        signal.emit(value)  # type: ignore
    else:
        signal.emit()  # type: ignore


def main():
    print("distutils", shutil.which("anki"))
    print("hardcoded", find_executable_hardcoded("anki"))
    print("all", find_executable("anki"))


if __name__ == "__main__":
    main()
