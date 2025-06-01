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


from abc import ABC, abstractmethod
from typing import Optional

from .router import Router

CONTROLLER_PREFIX = "amboss"


class Controller(ABC):
    @abstractmethod
    def __call__(self, url: str, arg: Optional[str] = None):
        raise NotImplementedError


class AmbossController(Controller):
    def __init__(self, **amboss_routers: Router):
        self._amboss_routers = amboss_routers

    def add_router(self, key: str, router: Router):
        self._amboss_routers[key] = router

    def __call__(self, url: str, arg: Optional[str] = None):
        if not url.startswith(CONTROLLER_PREFIX):
            return False
        try:
            _, router_key, cmd, *arg = url.split(":", 3)  # type: ignore[assignment]
        except ValueError:
            return False
        if not cmd:
            return False
        router = self._amboss_routers.get(router_key)
        return (
            router(cmd, arg[0] if arg else None)
            if isinstance(router, Router)
            else False
        )
