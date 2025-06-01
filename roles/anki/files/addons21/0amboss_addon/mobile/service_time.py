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

import datetime
import time


class TimeService:
    @classmethod
    def time(cls) -> float:
        """Used to return time from remote server. Now returns system time under
        the assumption that Anki takes care of asserting that system time does
        not drift too far apart from standard time."""
        # NOTE: When connected to the internet, on each launch, Anki asserts that
        # system time deviates no more than five minutes from the actual time.
        # If the deviation is greater, Anki will refuse to launch.
        # Given that, and the fact that we only need to be accurate in the realm
        # of days to weeks, it seems reasonable to rely on Anki's authority when
        # it comes to time.
        return cls.system_time()

    @staticmethod
    def system_time() -> float:
        return time.time()

    @classmethod
    def days_until(cls, timestamp: int) -> float:
        today = datetime.date.today()
        other_day = datetime.date.fromtimestamp(timestamp)
        return (other_day - today) / datetime.timedelta(days=1)
