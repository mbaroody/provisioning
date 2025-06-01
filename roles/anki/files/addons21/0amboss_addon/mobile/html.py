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

import re
from html.parser import HTMLParser
from typing import List, Optional, Tuple
from warnings import catch_warnings

import bs4  # type: ignore
from bs4 import Tag

from ..shared import safe_print


class HTMLParsingError(Exception):
    pass


class TagRemover(HTMLParser):
    def __init__(self, tag_id: str, preceding_newline_count: int = 2):
        # Config
        super().__init__(convert_charrefs=False)
        self._tag_id = tag_id
        self._preceding_newline_count = preceding_newline_count
        self._preceding_newline_pattern = re.compile(
            "(?:\r\n|\r|\n){" + str(self._preceding_newline_count) + "}"
        )
        # State
        self.reset()
        self._nesting = 0
        self._tag: Optional[str] = None
        self._lineno0: Optional[int] = None  # Line number of start tag (from 1)
        self._offset0: Optional[int] = None  # Column of start tag (from 0)
        self._lineno1: Optional[int] = None  # Line number of end tag (from 1)
        self._offset1: Optional[int] = None  # Column of end tag (from 0)
        self._error = False

    def remove(self, html: str) -> Optional[str]:
        if self._error:
            return None
        if self._lineno0 is None:
            # Nothing found
            return None
        if self._lineno1 is None and self._nesting != 0:
            # Only start tag found
            return None

        lines = html.splitlines(keepends=True)

        # Gather all lines that contain (parts of) the found tag
        hit_lines = lines[self._lineno0 - 1 : self._lineno1]
        hit = ""

        if (
            self._offset0 == 0
            and self._preceding_newline_count > 0
            and self._lineno0 - self._preceding_newline_count > 0
        ):
            preceding = "".join(
                lines[
                    self._lineno0
                    - 1
                    - self._preceding_newline_count : self._lineno0
                    - 1
                ]
            )
            preceding_newline_match = self._preceding_newline_pattern.search(preceding)
            if preceding_newline_match:
                hit += preceding_newline_match.group(0)

        hit += hit_lines[0][
            self._offset0 : self._offset1 if self._lineno0 == self._lineno1 else None
        ]

        for h in hit_lines[1:-1]:
            hit += h

        if len(hit_lines) > 1:
            hit += hit_lines[-1][: self._offset1 or None]

        whitespace_or_nothing_after_end_tag = (
            self._offset1 is not None and hit_lines[-1][self._offset1 :].rstrip() == ""
        )
        if whitespace_or_nothing_after_end_tag:
            hit += hit_lines[-1][
                self._offset1 :
            ]  # Add trailing whitespace to be removed

        add_buffer_space = not whitespace_or_nothing_after_end_tag

        return html.replace(hit, " " if add_buffer_space else "")

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        if ("id", self._tag_id) in attrs and self._lineno0 is None:
            # Start recording sweep on first match
            self._tag = tag
            self._lineno0, self._offset0 = self.getpos()
        if self._lineno0 is not None:
            # Increase nesting level with each start tag
            self._nesting += 1

    def handle_endtag(self, tag: str):
        if self._lineno0 is None or self._lineno1 is not None:
            # Nothing to do, sweep has not started, or is done
            return
        if self._nesting == 1 and self._tag != tag:
            # Closing end has the wrong type, abort
            safe_print("Trying to remove unbalanced tag")
            self._error = True
        if self._nesting == 0:
            # End position found
            self._lineno1, self._offset1 = self.getpos()
        # Decrease nesting level with each end tag
        self._nesting -= 1

    def handle_data(self, name: str):
        self._handle()

    def handle_entityref(self, name: str) -> None:
        self._handle()

    def handle_charref(self, name: str) -> None:
        self._handle()

    def handle_comment(self, data: str) -> None:
        self._handle()

    def handle_decl(self, decl: str) -> None:
        self._handle()

    def handle_pi(self, data: str) -> None:
        self._handle()

    def _handle(self):
        if self._lineno0 is None or self._lineno1 is not None:
            # Nothing to do, sweep has not started, or is done
            return
        if self._nesting == 0:
            # End position found
            self._lineno1, self._offset1 = self.getpos()


class TagUpdater:
    preceding_newline_count = 2
    preceding_newlines = preceding_newline_count * "\n"

    @classmethod
    def add_or_replace_tag(cls, tag: str, html: str) -> Optional[str]:
        html_soup, new_tag_node = cls._html_soup_and_tag_node(tag, html)
        tag_id = new_tag_node["id"]

        if existing_tag_node := html_soup.find(id=tag_id):
            # existing tag found
            if (
                isinstance(existing_tag_node, Tag)
                and existing_tag_node.attrs == new_tag_node.attrs
            ):
                # up-to-date
                return None

            # in need of update
            new_html = cls.remove_tag(tag, html)
            if new_html is None:  # this should never happen
                safe_print("Could not remove existing tag")
                return None

            html = new_html

        return f"{html}{cls.preceding_newlines}{tag}\n"

    @classmethod
    def remove_tag(cls, tag: str, html: str) -> Optional[str]:
        html_soup, tag_node = cls._html_soup_and_tag_node(tag, html)
        tag_id = tag_node["id"]
        html_tags = html_soup.find_all(id=tag_id)
        if not html_tags:
            return None
        for _ in html_tags:  # silly
            tag_remover = TagRemover(tag_id=tag_id, preceding_newline_count=cls.preceding_newline_count)  # type: ignore
            tag_remover.feed(html)
            html = tag_remover.remove(html)  # type: ignore
            if not html:
                return None
        return html

    @classmethod
    def _html_soup_and_tag_node(
        cls, tag: str, html: str
    ) -> Tuple[bs4.BeautifulSoup, bs4.element.Tag]:
        tag_soup = bs4.BeautifulSoup(tag, features="html.parser")
        tag_contents = [t for t in tag_soup.contents if isinstance(t, bs4.element.Tag)]
        assert len(tag_contents) == 1, "must have single tag"
        tag_node = tag_contents[0]
        return cls._parse_html(html), tag_node

    @classmethod
    def _parse_html(cls, html: str) -> bs4.BeautifulSoup:
        # Catching the exception is not sufficient to prevent Anki from creating an
        # error dialog, as bs4 also prints a warning (only if the html.parser exception
        # was caught)
        with catch_warnings(record=True) as warning_list:
            try:
                parsed = bs4.BeautifulSoup(html, features="html.parser")
            except Exception as e:
                raise HTMLParsingError("Could not parse template") from e
        if warning_list:
            safe_print(warning_list)
        return parsed
