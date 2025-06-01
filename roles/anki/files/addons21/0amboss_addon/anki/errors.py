# AMBOSS Anki Add-on
#
# Copyright (C) 2019-2022 AMBOSS MD Inc. <https://www.amboss.com/us>
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

from typing import Tuple, Type

IMPORT_ERRORS = (ImportError, ModuleNotFoundError)

try:
    from anki.errors import TemplateError  # 2.1.41+
except IMPORT_ERRORS:
    TemplateError = Exception  # type: ignore[misc, assignment]

try:
    from anki.errors import CardTypeError  # type: ignore  # 2.1.50+
except IMPORT_ERRORS:
    CardTypeError = TemplateError

try:  # 2.1.41+
    from anki.errors import InvalidInput
except IMPORT_ERRORS:  # 2.1.28+
    try:
        from anki.rsbackend import InvalidInput  # type: ignore  # noqa: F401
    except IMPORT_ERRORS:  # 2.1.26+
        from anki.rsbackend import (  # type: ignore # noqa:F401
            StringError as InvalidInput,  # type: ignore # noqa:F401
        )

NOTETYPE_ERRORS: Tuple[Type[Exception], ...] = (
    CardTypeError,  # 2.1.50+ (split off from older TemplateError)
    TemplateError,  # 2.1.41+
    InvalidInput,  # 2.1.26+ (overly broad until 2.1.28+)
)
