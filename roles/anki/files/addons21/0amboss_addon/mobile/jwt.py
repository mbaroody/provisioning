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

import base64
import json
from typing import NamedTuple, Union


class JSONWebTokenClaims(NamedTuple):
    exp: int
    iss: str
    sub: str
    iat: int


class InvalidJSONWebTokenError(ValueError):
    pass


def extract_jwt_claims(token: str) -> JSONWebTokenClaims:
    fields = token.split(".")
    try:
        assert len(fields) == 3
    except AssertionError as e:
        raise InvalidJSONWebTokenError("Invalid JWT field length") from e

    encoded_claims_data = fields[1]
    try:
        claims_data = base64url_decode(encoded_claims_data).decode("utf-8")
        claims_dict: dict = json.loads(claims_data)
        claims = JSONWebTokenClaims(
            **{k: v for k, v in claims_dict.items() if k in JSONWebTokenClaims._fields}
        )
    except Exception as e:
        raise InvalidJSONWebTokenError("Could not decode claims data") from e

    return claims


def base64url_decode(input: Union[str, bytes]) -> bytes:
    # base64 utility, extracted from PyJWT
    #
    # Copyright (c) 2015-2022 José Padilla
    #
    # The following text is included pursuant to a condition of an upstream licence,
    # and does not represent the current licensing status of this code, which is
    # licensed under the license mentioned in the copyright header above.
    #
    # PyJWT license:
    #
    # The MIT License (MIT)
    #
    # Permission is hereby granted, free of charge, to any person obtaining a copy
    # of this software and associated documentation files (the "Software"), to deal
    # in the Software without restriction, including without limitation the rights
    # to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    # copies of the Software, and to permit persons to whom the Software is
    # furnished to do so, subject to the following conditions:
    #
    # The above copyright notice and this permission notice shall be included in all
    # copies or substantial portions of the Software.
    #
    # THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    # IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    # FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    # AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    # LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    # OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    # SOFTWARE.
    if isinstance(input, str):
        input = input.encode("ascii")

    rem = len(input) % 4

    if rem > 0:
        input += b"=" * (4 - rem)

    return base64.urlsafe_b64decode(input)
