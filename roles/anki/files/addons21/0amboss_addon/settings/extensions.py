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

from typing import Optional, Protocol, MutableMapping

from aqt.qt import QWidget


class ExtensibleDialog(Protocol):
    def add_extension_widget(self, object_name: str, widget: QWidget):
        ...

    def get_extension_widget(self, object_name: str) -> Optional[QWidget]:
        ...


class SettingsExtension(Protocol):
    # NOTE: defining the protocol methods as static methods would be preferable, but
    # does not work well with mypy atm: https://github.com/python/mypy/issues/4536

    def on_dialog_init(self, dialog: ExtensibleDialog):
        ...

    def on_load_config(
        self,
        dialog: ExtensibleDialog,
        config: MutableMapping,
        logged_in: bool,
        article_access: bool,
    ):
        ...

    def on_save_config(
        self,
        dialog: ExtensibleDialog,
        config: MutableMapping,
        logged_in: bool,
        article_access: bool,
    ):
        ...
