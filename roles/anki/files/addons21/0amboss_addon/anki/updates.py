# AMBOSS Anki Add-on
#
# Copyright (C) 2019-2023 AMBOSS MD Inc. <https://www.amboss.com/us>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version, with the additions
# listed at the end of the license file that accompanied this program.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Handles suppressing AnkiWeb updates by modifying add-on metadata files.

Anki API assumptions:

- Add-on metadata files are stored in the add-on package directory as `meta.json`,
  are encoded in UTF-8, are valid JSON, and can be read and written to by
  add-ons at Anki startup
- The metadata file contains a `mod` key with a value that is an integer
- The `mod` value is a timestamp in seconds since the epoch
- The local `mod` value is compared with a remote timestamp value to determine
  whether an add-on update is available on AnkiWeb

TODO: Assert these assumptions in functional tests against Anki
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import IO, Any, Dict, NewType, Optional, Union

MetaData = NewType("MetaData", Dict[str, Any])


class AddonUpdateSuppressionError(Exception):
    prefix = "Could not suppress AnkiWeb updates for add-on"

    def __init__(self, msg: Optional[str] = None, *args, **kwargs):
        msg = f"{self.prefix}: {msg}" if msg is not None else self.prefix
        super().__init__(msg, *args, **kwargs)


def read_metadata(file: IO) -> MetaData:
    try:
        metadata: MetaData = json.load(file)
    except Exception as e:
        raise AddonUpdateSuppressionError("Could not read add-on metadata file") from e

    if (
        not isinstance(metadata, dict)
        or metadata.get("mod") is None
        or not isinstance(metadata["mod"], int)
    ):
        raise AddonUpdateSuppressionError("Unsupported add-on metadata file")

    return metadata


def write_metadata(file: IO, metadata: MetaData):
    try:
        json.dump(metadata, file)
    except Exception as e:
        raise AddonUpdateSuppressionError("Could not write add-on metadata file") from e


def is_32_bit_platform() -> bool:
    """Check whether the current platform is 32-bit"""

    return sys.maxsize <= 2**31 - 1


def get_max_timestamp() -> int:
    """
    Get the maximum timestamp supported by the current platform's time_t type
    implementation.

    Returns:
        Timestamp in seconds since the epoch
    """

    if is_32_bit_platform():  # only relevant for Anki 2.1.35-alternate
        # 32-bit C time_t implementations can represent dates up to 2038-01-19
        dt = datetime(year=2037, month=1, day=1, tzinfo=timezone.utc)
    else:
        # Windows C time_t can represent dates up to 3000-12-31:
        # https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/
        # localtime-localtime32-localtime64?view=msvc-170#return-value
        dt = datetime(year=2999, month=1, day=1, tzinfo=timezone.utc)

    return int(dt.timestamp())


def suppress_ankiweb_updates(addon_path: Union[str, Path]):
    """
    Suppress AnkiWeb updates for a specific add-on

    Increases the `mod` value in the add-on metadata file to a future date,
    thereby suppressing AnkiWeb updates for the add-on.

    Args:
        addon_path: Path to the add-on package directory

    Raises:
        AddonUpdateSuppressionError: If the add-on metadata file could not be
            found or read, or if the add-on metadata file is invalid.
    """

    metadata_path = Path(addon_path) / "meta.json"

    if not metadata_path.is_file():
        raise AddonUpdateSuppressionError(
            f"Could not find add-on metadata file: {metadata_path}"
        )

    with metadata_path.open("r", encoding="utf-8") as f:
        metadata = read_metadata(f)

    max_timestamp = get_max_timestamp()
    if metadata["mod"] >= max_timestamp:
        return

    metadata["mod"] = max_timestamp

    with metadata_path.open("w", encoding="utf-8") as f:
        write_metadata(f, metadata)
