from concurrent.futures import Future
import time
from typing import List, Callable, Any, TYPE_CHECKING, Tuple
import requests
import re
import os
from zipfile import ZipFile
from tempfile import TemporaryDirectory

from aqt import mw
from aqt.webview import AnkiWebView, AnkiWebPage
from aqt.qt import QWebEngineProfile, QWebEnginePage, QUrl

from .base import FileLike, RootPath
from .local import LocalRoot
from .errors import *

if TYPE_CHECKING:
    from ..importing import ImportResult

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


importer: Optional["FolderAsZipImporter"]


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

    def list_paths(self, id: str) -> List[dict]:
        url = self.BASE_URL
        result = []
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
            result += data["files"]
            if not "nextPageToken" in data:
                break

            page_token = data["nextPageToken"]

        return result

    def download_file(self, id: str) -> bytes:
        url = f"{self.BASE_URL}/{id}"
        res = self.make_request(url, params={"alt": "media", "key": API_KEY})
        return res.content

    def download_folder_zip(
        self, id: str, on_done: Callable[[str, bool], None]
    ) -> None:
        global importer
        importer = FolderAsZipImporter(id, on_done)

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


class FolderAsZipImporter:
    ZIP_NAME = "media.zip"

    id: str
    # on_done: Callable[[str, bool], None]
    web: AnkiWebView
    zip_dir: str
    unzip_dir: str
    # qt6: QWebEngineDownloadRequest, qt5: QWebEngineDownloadItem
    request: Any = None
    error_msg: Optional[str] = None

    def __init__(self, id: str, on_done: Callable[[str, bool], None]) -> None:
        self.id = id
        self.on_done = on_done  # type: ignore
        with TemporaryDirectory() as zip_dir, TemporaryDirectory() as unzip_dir:
            self.zip_dir = zip_dir
            self.unzip_dir = unzip_dir
            self.setup_web()
            mw.taskman.run_in_background(
                task=lambda: self.poll_download_progress(),
                on_done=self.on_finish_download_zip,
            )

    def setup_web(self) -> None:
        web = AnkiWebView(mw)
        self.web = web
        profile = QWebEngineProfile(web)
        profile.setHttpAcceptLanguage("en")
        profile.setDownloadPath(self.zip_dir)
        profile.downloadRequested.connect(self.on_download)  # type: ignore
        backgroundColor = web.page().backgroundColor()
        page = PrivateWebPage(profile, web._onBridgeCmd)
        page.setBackgroundColor(backgroundColor)
        web.setPage(page)
        web._page = page
        web.set_bridge_command(self.on_cmd, self)
        web.load_url(QUrl(f"https://drive.google.com/drive/folders/{self.id}?hl=en"))
        web.eval(
            """
        window.AnkiHub = {};
        window.AnkiHub.GetZipProgress = () => {
            const elem = document.querySelector("[data-progress]");
            if (elem) {
                return parseFloat(elem.dataset.progress);
            } else {
                return 0;
            }
        }
        (() => {
            const onload = () => {
                try {
                    const elem = document.evaluate("//div[text()='Download all']", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE).singleNodeValue;
                    if (elem) {
                        elem.dispatchEvent(new MouseEvent("mousedown"));elem.dispatchEvent(new MouseEvent("mouseup"));elem.dispatchEvent(new MouseEvent("click")); 
                    } else {
                        setTimeout(onload, 2000);
                    }
                } catch (e) {
                    pycmd("gdriveError!" + e.toString());
                }
            }
            // There seems to be some delay between document load and event listener attaching
            if (document.readyState === "complete") {
                setTimeout(onload, 5000);
            } else {
                window.addEventListener("load", () => {setTimeout(onload, 5000)});
            }
        })()
            """
        )

    def on_download(self, req: Any) -> None:
        self.request = req
        req.setDownloadFileName(self.ZIP_NAME)
        req.accept()

    def on_cmd(self, cmd: str) -> None:
        if cmd.startswith("gdriveError!"):
            self.error_msg = cmd[len("gdriveError!") :]

    def poll_download_progress(self) -> Tuple[bool, str]:
        while True:
            time.sleep(0.5)
            if mw.progress.want_cancel():
                if self.request:
                    self.request.cancel()
                return (False, "Cancelled")
            if self.request is None:
                if self.error_msg is not None:
                    return (
                        False,
                        f"JS error while downloading folder:\n{self.error_msg}",
                    )
                self.web.evalWithCallback(
                    "AnkiHub.GetZipProgress()",
                    lambda progress: mw.taskman.run_on_main(
                        lambda: mw.progress.update(
                            label=f"Zipping folder ({progress}%)",
                            value=progress + 1,  # value must not be 0
                            max=101,
                        ),
                    ),
                )
                continue

            request = self.request
            if request.isFinished():
                return (True, "Finished")

            # calculating percent to prevent overflow errors in mw.progress.update
            percent_received = int(request.receivedBytes() / request.totalBytes() * 100)
            mw.taskman.run_on_main(
                lambda: mw.progress.update(
                    label="Downloading folder",
                    value=percent_received,
                    max=100,
                )
            )

    def on_finish_download_zip(self, future: Future) -> None:
        self.web.setParent(None)
        self.web.page().deleteLater()
        self.web.deleteLater()
        self.web = None

        try:
            (success, msg) = future.result()
            if success:
                self.unzip_and_install()
            else:
                self.on_done(msg, success)
        except Exception as err:
            self.on_done(str(err), False)

    def unzip_and_install(self) -> None:
        from ..importing import import_media

        zip_path = os.path.join(self.zip_dir, self.ZIP_NAME)
        with ZipFile(zip_path) as zfile:
            zfile.extractall(self.unzip_dir)
            inner_dir = [d for d in os.scandir(self.unzip_dir) if d.is_dir()][0]
            root = LocalRoot(inner_dir.path)
            import_media(root, self.on_finish)

    # TODO: refactor logs mechanism and progress dialog
    def on_finish(self, result: "ImportResult") -> None:
        self.on_done("Successfully imported media files", result.success)


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
        self.files = self.list_files(recursive=True)

    def list_files(self, recursive: bool) -> List["FileLike"]:
        files: List["FileLike"] = []
        self.search_files(files, self.id, recursive)
        return files

    def search_files(self, files: List["FileLike"], id: str, recursive: bool) -> None:
        paths = gdrive.list_paths(id)
        for path in paths:
            if gdrive.is_folder(path):
                if recursive:
                    self.search_files(files, path["id"], recursive=True)
            elif ("fileExtension" in path) and self.has_media_ext(
                path["fileExtension"]
            ):
                # Google docs files don't have file extensions
                file = GDriveFile(path)
                files.append(file)


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
