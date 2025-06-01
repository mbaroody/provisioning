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

style_button_primary = """
QPushButton {
    background: #0FA980;
    color: white;
    border-radius: 4px;
    padding-left: 8px;
    padding-right: 8px;
    padding-top: 4px;
    padding-bottom: 4px;
    border: none;
    outline: none;
}
QPushButton:focus, QPushButton:active {
    border: none;
    outline: none;
}
QPushButton:hover:!pressed {
    background-color: #0B8363;
}
QPushButton:pressed {
    background-color: #0A5C45;
}
QPushButton:disabled {
    background-color: #FFFFFF;
    border: 1px solid #A3B2BD;
    color: #40515E;
}
QPushButton[night_mode="True"] {
    background: #28816b;
    color: #d8dade;
}
QPushButton[night_mode="True"]:hover:!pressed {
    background-color: #41a48a;
}
QPushButton[night_mode="True"]:pressed {
    background-color: #233d3d;
}
QPushButton[night_mode="True"]:disabled {
    background-color: #213e3a;
    border: none;
    color: rgba(216, 218, 222, 0.3);
}
"""

style_separator = """
QFrame[frameShape="4"][night_mode="True"],
QFrame[frameShape="5"][night_mode="True"]
{
    border: none;
    background: #252525;
}
"""
