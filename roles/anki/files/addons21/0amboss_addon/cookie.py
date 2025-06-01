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


from typing import NamedTuple, Optional, TYPE_CHECKING

from aqt import QDateTime, qtmajor

# QtNetwork is not exposed via aqt.qt
if TYPE_CHECKING or qtmajor < 6:  # 2.1.49 is dev target, thus type-checking assumes Qt5
    from PyQt5.QtNetwork import QNetworkCookie
else:
    from PyQt6.QtNetwork import QNetworkCookie  # type: ignore


class Cookie(NamedTuple):
    """
    Custom data exchange format for cookies
    Fully typed and easier to handle than QNetworkCookie
    """

    name: str
    value: str
    domain: str
    path: str
    expires: Optional[int]
    secure: bool
    http_only: bool


class _CookieTranslator:
    @staticmethod
    def cookie_from_qcookie(qcookie: QNetworkCookie) -> Cookie:
        # TODO: bytearray typing below should be fixable (decode arr directly to str?)
        return Cookie(
            name=bytearray(qcookie.name()).decode(),  # type: ignore[call-overload]
            value=bytearray(qcookie.value()).decode(),  # type: ignore[call-overload]
            domain=qcookie.domain(),
            path=qcookie.path(),
            expires=qcookie.expirationDate().toSecsSinceEpoch()
            if qcookie.expirationDate()
            else None,
            secure=qcookie.isSecure(),
            http_only=qcookie.isHttpOnly(),
        )

    @staticmethod
    def qcookie_from_cookie(cookie: Cookie) -> QNetworkCookie:
        qcookie = QNetworkCookie(
            name=cookie.name.encode("utf-8"), value=cookie.value.encode("utf-8")
        )
        qcookie.setDomain(cookie.domain)
        qcookie.setPath(cookie.path)
        qcookie.setHttpOnly(cookie.http_only)
        qcookie.setSecure(cookie.secure)
        if cookie.expires:
            qcookie.setExpirationDate(QDateTime.fromSecsSinceEpoch(cookie.expires))
        return qcookie
