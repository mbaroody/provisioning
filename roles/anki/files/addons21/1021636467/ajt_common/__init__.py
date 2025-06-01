# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from anki.utils import int_version

if int_version() < 231000:
    raise RuntimeError("This Anki version is not supported.")
