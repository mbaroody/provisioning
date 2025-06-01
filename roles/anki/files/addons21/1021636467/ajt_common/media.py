# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import re

SOUND_TAG_REGEX = re.compile(r"\[sound:([^\[\]]+?\.[^\[\]]+?)]")
IMAGE_TAG_REGEX = re.compile(r'<img [^<>]*src="([^"<>\']+)"[^<>]*>')


def unquote_filenames(filenames: list[str]) -> list[str]:
    import urllib.parse

    return list(map(urllib.parse.unquote, filenames))


def find_sounds(html: str) -> list[str]:
    """Return a list of audio files referenced in html."""
    return unquote_filenames(re.findall(SOUND_TAG_REGEX, html))


def find_images(html: str) -> list[str]:
    """Return a list of images referenced in html."""
    return unquote_filenames(re.findall(IMAGE_TAG_REGEX, html))


def find_all_media(html: str) -> list[str]:
    """Return a list of image and audio files referenced in html."""
    return find_images(html) + find_sounds(html)
