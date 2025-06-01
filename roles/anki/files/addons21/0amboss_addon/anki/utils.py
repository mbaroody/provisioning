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

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # type checkers currently target 2.1.49
    from anki.utils import isMac as is_mac  # noqa: F401
    from anki.utils import isWin as is_win  # noqa: F401
    from anki.utils import versionWithBuild as version_with_build  # noqa: F401
else:
    try:
        from anki.utils import is_mac
    except ImportError:
        from anki.utils import isMac as is_mac  # noqa: F401

    try:
        from anki.utils import is_win
    except ImportError:
        from anki.utils import isWin as is_win  # noqa: F401

    try:
        from anki.utils import version_with_build
    except ImportError:
        from anki.utils import versionWithBuild as version_with_build  # noqa: F401

from aqt.utils import showText as anki_show_text  # noqa: F401
from aqt.utils import showInfo as anki_show_info  # noqa: F401
from aqt.utils import showWarning as anki_show_warning  # noqa: F401
from aqt.utils import openLink as anki_open_link  # noqa: F401
