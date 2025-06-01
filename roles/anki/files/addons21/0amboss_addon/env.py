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

import os
from .shared import string_to_boolean
from enum import Enum, auto

IS_AMBOSS_TEST_ENV_VAR = "IS_AMBOSS_TEST"


class AmbossFeature(Enum):
    anki_to_qbank = auto()
    mobile = auto()


def is_addon_test_environment() -> bool:
    return string_to_boolean(os.environ.get(IS_AMBOSS_TEST_ENV_VAR, "false"))


def is_feature_enabled(feature: AmbossFeature) -> bool:
    return string_to_boolean(
        os.environ.get(f"AMBOSS_FEATURE_{feature.name.upper()}_ENABLED", "false")
    )
