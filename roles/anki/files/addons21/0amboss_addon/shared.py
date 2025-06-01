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

import gettext
import os
from pathlib import Path
from typing import Callable, Literal


def _sanitize_text(text: str):
    return text.encode("ascii", errors="xmlcharrefreplace").decode("ascii")


def safe_print(*args, **kwargs):
    """Temporary workaround for locale issues forcing ascii stdout"""
    try:
        return print(*args, **kwargs)
    except UnicodeEncodeError:
        try:
            new_args = [_sanitize_text(str(a)) for a in args]
            if "sep" in kwargs:
                kwargs["sep"] = _sanitize_text(kwargs["sep"])
            if "end" in kwargs:
                kwargs["end"] = _sanitize_text(kwargs["end"])
            print(*new_args, **kwargs)
        except:  # noqa: E722
            print("Error while trying to print.")


def string_to_boolean(val):
    """
    Convert a string representation of truth to true (True) or false (False).

    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    elif val in ("n", "no", "f", "false", "off", "0"):
        return False
    else:
        raise ValueError("invalid truth value %r" % (val,))


def translator(domain: str, locale_dir: str, locale: str) -> Callable[[str], str]:
    lang = gettext.translation(
        domain,
        localedir=(Path(__file__).parent / locale_dir).resolve(),
        languages=[locale],
    )
    lang.install()
    return lang.gettext


def set_locale(locale: Literal["en", "de"]):
    global _
    locale = locale if locale in ["en", "de"] else "en"
    _ = translator("messages", "locale", locale)


_ = translator("messages", "locale", os.environ.get("AMBOSS_LANGUAGE", "en"))
