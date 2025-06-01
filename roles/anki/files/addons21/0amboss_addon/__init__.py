# AMBOSS Anki Add-on
#
# Copyright (C) 2019-2020 AMBOSS MD Inc. <https://www.amboss.com/us>
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

from .env import is_addon_test_environment, is_feature_enabled, AmbossFeature

if not is_addon_test_environment():
    from .addon import *  # noqa: F401, F403

if is_feature_enabled(AmbossFeature.anki_to_qbank):
    from . import qbank  # noqa: F401

if is_feature_enabled(AmbossFeature.mobile):
    from . import mobile  # noqa: F401
