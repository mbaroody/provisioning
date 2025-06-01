import os
import re
from typing import Any, Callable, Generator, Iterable, List

import requests
from aqt.qt import QWebEnginePage, QWebEngineProfile
from aqt.webview import AnkiWebPage

from .base import FileLike, RootPath
from .errors import *

try:
    from ..google_api_key import get_google_api_key  # type: ignore

    API_KEY = get_google_api_key()
except:  # Not production?
    try:
        API_KEY = os.environ["GOOGLE_API_KEY"]
    except:
        API_KEY = None


class PrivateWebPage(AnkiWebPage):
    def __init__(self, profile: QWebEngineProfile, onBridgeCmd: Callable[[str], Any]):
        QWebEnginePage.__init__(self, profile, None)
        self._onBridgeCmd = onBridgeCmd
        self._setupBridge()
        self.open_links_externally = False


class GDrive:
    REGEXP = r"drive.google.com/drive/folders/([^?]*)(?:\?|$)"
    FILE_REGEXP = r"drive.google.com/drive/file/"
    URL_PATTERN = re.compile(REGEXP)
    FILE_URL_PATTERN = re.compile(FILE_REGEXP)

    BASE_URL = "https://www.googleapis.com/drive/v3/files"
    FIELDS_STR = ",".join(
        ["id", "name", "md5Checksum", "mimeType", "fileExtension", "size"]
    )

    def get_metadata(self, id: str) -> dict:
        url = f"{self.BASE_URL}/{id}"
        return self.make_request(
            url, params={"fields": self.FIELDS_STR, "key": API_KEY}
        ).json()

    def get_path_chunks(self, id: str) -> Iterable[List[dict]]:
        url = self.BASE_URL
        page_token = None
        while True:
            data = self.make_request(
                url,
                params={
                    "q": f"'{id}' in parents",
                    "fields": "nextPageToken,files({})".format(self.FIELDS_STR),
                    "key": API_KEY,
                    "pageSize": 1000,
                    "pageToken": page_token,
                },
            ).json()

            yield data["files"]

            if not "nextPageToken" in data:
                break

            page_token = data["nextPageToken"]

    def download_file(self, id: str) -> bytes:
        url = f"{self.BASE_URL}/{id}"
        res = self.make_request(url, params={"alt": "media", "key": API_KEY})
        return res.content

    def make_request(self, url: str, params: dict) -> requests.Response:
        res = requests.get(url, params)
        if res.ok:
            return res

        # Error occured!
        try:
            body = res.json()["error"]
            code = body["code"]
        except:
            raise RequestError(-1, res.text)
        try:
            error = body["errors"][0]
            message = error["message"]
            reason = error["reason"]
        except:
            message = body["message"]
            reason = ""
        if code == 404:
            raise RootNotFoundError(code, message)
        elif code in range(500, 505):
            raise ServerError(code, message)
        elif code in (403, 429) and reason in (
            "userRateLimitExceeded",
            "rateLimitExceeded",
            "dailyLimitExceeded",
        ):
            raise RateLimitError(code, message)
        raise RequestError(code, message)

    def is_folder(self, pathdata: dict) -> bool:
        return pathdata["mimeType"] == "application/vnd.google-apps.folder"

    def parse_url(self, url: str) -> str:
        """Format: https://drive.google.com/drive/folders/{gdrive_id}?params"""
        m = re.search(self.URL_PATTERN, url)
        if m:
            return m.group(1)
        m = re.search(self.FILE_URL_PATTERN, url)
        if m:
            raise IsAFileError()
        raise MalformedURLError()


gdrive = GDrive()


class GDriveRoot(RootPath):
    raw: str
    name: str
    files: List["FileLike"]

    id: str

    def __init__(self, url: str) -> None:
        if not API_KEY:
            raise Exception("No API Key Found!")
        self.raw = url
        self.id = gdrive.parse_url(url)
        data = gdrive.get_metadata(self.id)
        self.name = data["name"]
        if not gdrive.is_folder(data):
            raise IsAFileError

    def list_files(self, recursive: bool) -> Iterable["FileLike"]:
        files: List["FileLike"] = []
        for file in self.search_files(files, self.id, recursive):
            yield file

    def search_files(
        self, files: List["FileLike"], id: str, recursive: bool
    ) -> Iterable["FileLike"]:
        file_chunks = gdrive.get_path_chunks(id)
        for chunk in file_chunks:
            for file_info in chunk:
                if gdrive.is_folder(file_info):
                    if recursive:
                        self.search_files(files, file_info["id"], recursive=True)
                elif ("fileExtension" in file_info) and self.has_media_ext(
                    file_info["fileExtension"]
                ):
                    # Google docs files don't have file extensions
                    file = GDriveFile(file_info)
                    yield file


class GDriveFile(FileLike):
    key: str  # == id
    name: str
    extension: str
    size: int

    _md5: str
    id: str

    def __init__(self, data: dict) -> None:
        if not data:
            raise ValueError(
                "Either data or id should be passed when initializing GDrivePath."
            )
        self.path = data["id"]
        self.name = data["name"]
        self.extension = data["fileExtension"]
        self.size = int(data["size"])
        self.id = self.path
        self._md5 = data["md5Checksum"]

    def read_bytes(self) -> bytes:
        return gdrive.download_file(self.id)

    @property
    def md5(self) -> str:
        return self._md5

    def is_identical(self, file: "FileLike") -> bool:
        try:  # Calculating md5 is slow for local file.
            return file.size == self.size and file.md5 == self.md5  # type: ignore
        except AttributeError:
            return file.size == self.size
