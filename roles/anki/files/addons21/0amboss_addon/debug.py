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


"""
Based in parts on anki.utils (Copyright: Ankitects Pty Ltd and contributors)
"""

import html
import json
import os
import ssl
import time
import traceback
from collections import deque
from typing import (
    TYPE_CHECKING,
    Any,
    Deque,
    Dict,
    Optional,
    Sequence,
    Tuple,
    Union,
)

import certifi
from aqt.qt import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QTextBrowser,
    QTextCursor,
    QVBoxLayout,
    QWidget,
    pyqtSignal,
    pyqtSlot,
)
from aqt.utils import showWarning, tooltip

from .config import AddonConfig
from .profile import ProfileAdapter
from .shared import _, safe_print, string_to_boolean

if TYPE_CHECKING:
    from anki.collection import Collection
    from aqt.main import AnkiQt
    from aqt.reviewer import Reviewer

DEBUG_ACTIVE = string_to_boolean(os.environ.get("AMBOSS_DEBUG", "false"))
QBANK_DEBUG_ACTIVE = string_to_boolean(os.environ.get("AMBOSS_DEBUG_QBANK", "false"))


class ErrorSubmitter:
    def __init__(
        self,
        profile: ProfileAdapter,
        sentry_dsn: str,
        version: str,
        stage: str,
        max_string_length: int,
    ):
        self._profile = profile
        self._sentry_dsn = sentry_dsn
        self._version = version
        self._stage = stage
        self._max_string_length = max_string_length

    def submit(self, data: dict, exception: Optional[Exception]) -> bool:
        """
        Temporarily enables sentry integration to send error and then disables it again.
        """
        import sentry_sdk
        import sentry_sdk.utils
        from sentry_sdk import (
            capture_exception,
            capture_message,
            configure_scope,
        )

        # Workaround: Avoid truncating problem descriptions submitted by users
        sentry_sdk.utils.MAX_STRING_LENGTH = self._max_string_length

        # NOTE: type ignores on sentry init calls can be fixed by upgrading vendored
        # sentry sdk to >=1.5.11 https://github.com/getsentry/sentry-python/issues/1415
        try:
            sentry_sdk.init(  # type: ignore[abstract]
                self._sentry_dsn,
                release=self._version,
                attach_stacktrace=True,
                with_locals=True,
                environment=self._stage,
            )
            with configure_scope() as scope:  # type: ignore # TODO: understand
                scope.level = "error"
                scope.user = {"id": self._profile.id, "anonId": self._profile.anon_id}
                if "debug" in data and type(data["debug"]) is dict:
                    for k, v in data["debug"].items():
                        scope.set_extra(k, v)
                if "message" in data:
                    scope.set_extra("message", data["message"])
            if isinstance(exception, Exception):
                capture_exception(exception)
            elif "message" in data:
                capture_message(data["message"], "error")
            sentry_sdk.flush()
            return True
        except Exception as e:
            # something went wrong
            safe_print(e)
            return False
        finally:
            # Calling init with empty string disables sentry again
            # Otherwise we would log other Anki exceptions
            sentry_sdk.init("")  # type: ignore[abstract]


class DebugInfo:
    """
    Utility class for gathering debug info on various aspects of our add-on and Anki
    """

    _reviewer_attrs = {
        "card": ("id",),
        "note": ("guid", "tags", "fields"),
        "model": ("name", "css"),
        "template": ("qfmt", "afmt"),
    }

    # all environment variables used by Anki that could be relevant to us
    _anki_env = (
        "ANKI_NOVERIFYSSL",
        "ANKI_BASE",
        "ANKI_NOHIGHDPI",
        "ANKI_SOFTWAREOPENGL",
        "ANKI_WEBSCALE",
        "DEBUG",
        "QT_XCB_FORCE_SOFTWARE_OPENGL",
        "QT_OPENGL",
    )

    _amboss_env = ("AMBOSS_GRAPHQL_URI", "AMBOSS_RESTPHRASE_URI", "AMBOSS_LIBRARY_URI")

    def __init__(self, main_window: "AnkiQt", addon_config: AddonConfig, version: str):
        self._main_window = main_window
        self._addon_config = addon_config
        self._version = version

    def all(self) -> dict:
        return {
            "amboss": self.amboss(),
            "anki": self.anki(),
            "reviewer": self.reviewer(),
            "addons": self.addons(),
        }

    def amboss(self) -> dict:
        return {
            "version": self._version,
            "channel": os.environ.get("AMBOSS_DISTRIBUTION_CHANNEL"),
            "language": os.environ.get("AMBOSS_LANGUAGE"),
            "stage": os.environ.get("AMBOSS_STAGE"),
            "package": __name__.split(".")[0],
            "env": self._get_environment(self._amboss_env),
            "config": dict(self._addon_config),
        }

    def anki(self) -> dict:
        import locale
        import platform
        import re
        import sys

        from aqt.qt import PYQT_VERSION_STR, QT_VERSION_STR, QWebEngineProfile

        from .anki.utils import is_mac, is_win, version_with_build

        if is_win:
            platname = "Windows " + platform.win32_ver()[0]
        elif is_mac:
            platname = "Mac " + platform.mac_ver()[0]
        else:
            platname = "Linux"

        def sched_ver() -> str:
            if not self._main_window.col:
                return "?"

            try:
                if self._main_window.col.v3_scheduler():
                    return "3"
                else:
                    return str(self._main_window.col.sched_ver())
            except AttributeError:
                return self._main_window.col.schedVer()  # type: ignore[attr-defined]
            except Exception:
                return "?"

        def anki_flavor() -> str:
            try:
                qt_version_parts = [int(p) for p in QT_VERSION_STR.split(".")]
                if qt_version_parts[0] <= 5 and qt_version_parts[1] <= 9:
                    return "alternate"
                return "standard"
            except Exception:
                return "unknown"

        def locales() -> Sequence[Optional[str]]:
            try:
                return locale.getlocale()
            except Exception:
                return ["unknown", "unknown"]

        def q_web_engine_user_agent() -> str:
            try:
                return QWebEngineProfile.defaultProfile().httpUserAgent()
            except Exception as e:
                safe_print(e)
                return "unknown"

        def chromium() -> str:
            user_agent = q_web_engine_user_agent()
            try:
                return re.findall(r"(?:Chrome|Chromium)/(\S+?)\s", user_agent)[0]
            except IndexError:
                return "unknown"

        return {
            "version": version_with_build(),
            "flavor": anki_flavor(),
            "python": platform.python_version(),
            "qt": QT_VERSION_STR,
            "pyqt": PYQT_VERSION_STR,
            "chromium": chromium(),
            "platform": platname,
            "frozen": getattr(sys, "frozen", False),  # source build or binary build?
            "addonsLoaded": self._main_window.addonManager.dirty,
            "scheduler": sched_ver(),
            "env": self._get_environment(self._anki_env),
            "locale": locales(),
            "cacert": certifi.where(),
            "sslVersion": ssl.OPENSSL_VERSION,
            "QWebEngineUserAgent": q_web_engine_user_agent(),
        }

    def reviewer(self) -> Optional[dict]:
        reviewer: Optional["Reviewer"] = getattr(self._main_window, "reviewer", None)
        if not reviewer or not reviewer.card or not self._main_window.col:
            # collection might be unloaded if full sync is in progress
            return None

        collection: "Collection" = self._main_window.col

        card = reviewer.card
        note = card.note()
        template = card.template()
        try:
            model = card.note_type()
        except AttributeError:
            model = card.model()  # type: ignore[attr-defined]

        try:  # 2.1.45+
            deck_name = collection.decks.name_if_exists(card.did)
        except AttributeError:
            deck_name = collection.decks.nameOrNone(  # type: ignore[attr-defined]
                card.did
            )
        data = {"deck": {"name": deck_name}}

        for obj, obj_name in (
            (card, "card"),
            (note, "note"),
            (template, "template"),
            (model, "model"),
        ):
            attrs = self._reviewer_attrs[obj_name]

            obj_data = {}

            for attr in attrs:
                if obj_name in ("template", "model"):
                    obj_data[attr] = obj.get(attr, None)  # type: ignore[attr-defined]
                else:
                    obj_data[attr] = getattr(obj, attr, None)

            data[obj_name] = obj_data

        try:  # 2.1.45+
            field_names = collection.models.field_names(model)
        except AttributeError:
            field_names = collection.models.fieldNames(  # type: ignore[attr-defined]
                model
            )

        data["model"]["flds"] = field_names  # type: ignore[assignment]

        return data

    def addons(self) -> Optional[Tuple[str, ...]]:
        addon_manager = getattr(self._main_window, "addonManager", None)
        if not addon_manager:
            return None
        # annotated name provides us with info on activation state:
        return tuple(addon_manager.annotatedName(d) for d in addon_manager.allAddons())

    def _get_environment(self, names: Tuple[str, ...]) -> dict:
        return {name: os.environ.get(name, None) for name in names}


class DebugService:
    def __init__(self, main_window, addon_config: AddonConfig, version: str):
        self._main_window = main_window
        self._addon_config = addon_config
        self._version = version

    def get_for_machine(self) -> dict:
        return DebugInfo(self._main_window, self._addon_config, self._version).all()


class ErrorPromptFactory:
    _default_message_heading = _("Encountered an unexpected error in the AMBOSS add-on")
    _default_window_title = _("AMBOSS - Unexpected error")

    def __init__(
        self,
        main_window: "AnkiQt",
        debug_service: DebugService,
        error_submitter: ErrorSubmitter,
        max_message_chars: int,
    ):
        self._main_window = main_window
        self._debug_service = debug_service
        self._error_submitter = error_submitter
        self._max_message_chars = max_message_chars

    def create_and_exec(
        self,
        exception: Optional[Exception],
        message_heading: Optional[str] = None,
        message_body: Optional[str] = None,
        window_title: Optional[str] = None,
        extra_debug_data: Optional[Dict[str, Any]] = None,
        parent: Optional[QWidget] = None,
    ):
        def create_and_exec():
            ErrorPrompt(
                main_window=self._main_window,
                debug_service=self._debug_service,
                error_submitter=self._error_submitter,
                exception=exception,
                window_title=window_title or self._default_window_title,
                message_heading=message_heading or self._default_message_heading,
                message_body=message_body or "",
                max_message_chars=self._max_message_chars,
                extra_debug_data=extra_debug_data,
                parent=parent,
            )

        # Error prompts might be generated in background threads. As dialogs
        # need to be executed in the main thread, use Anki's task manager to
        # guarantee main thread execution.
        self._main_window.taskman.run_on_main(create_and_exec)


class ErrorTextEdit(QPlainTextEdit):
    char_count_updated = pyqtSignal(int)

    def __init__(self, max_chars: int, parent: QWidget):
        super().__init__(parent=parent)
        self.textChanged.connect(self.on_text_changed)
        self._max_chars = max_chars

    def on_text_changed(self) -> None:
        current_text = self.toPlainText()
        new_length = len(current_text)
        self.char_count_updated.emit(new_length)
        if len(self.toPlainText()) <= self._max_chars:
            return
        self.setPlainText(current_text[: self._max_chars])
        self.moveCursor(QTextCursor.MoveOperation.End)


class ErrorPrompt(QDialog):
    _json_indent = 4

    def __init__(
        self,
        main_window: "AnkiQt",
        debug_service: DebugService,
        error_submitter: ErrorSubmitter,
        exception: Optional[Exception],
        window_title: str,
        message_heading: str,
        message_body: str,
        max_message_chars: int,
        parent: Optional[QWidget] = None,
        extra_debug_data: Optional[Dict[str, Any]] = None,
    ):
        parent = parent or main_window
        super().__init__(parent=parent)
        self.setObjectName("amboss_error_dialog")
        self._main_window = main_window
        self._error_submitter = error_submitter
        self._exception = exception
        self._message_heading = message_heading
        self._message_body = message_body
        self._window_title = window_title
        self._max_user_message_chars = max_message_chars
        self._user_message_label_string = (
            _("Please describe the issue you encountered")
            + ": <i>({chars} "
            + _("characters remaining")
            + ")</i>"
        )
        self.text_browser = QTextBrowser(self)
        self.text_edit = ErrorTextEdit(self._max_user_message_chars, self)
        self.text_edit.char_count_updated.connect(self._on_message_char_count_updated)
        self.button_box = QDialogButtonBox(self)

        debug_data = debug_service.get_for_machine()
        if debug_data and extra_debug_data:
            debug_data.update(extra_debug_data)
        elif extra_debug_data:
            debug_data = extra_debug_data
        self._debug_data = debug_data

        self._setup_ui()
        self.exec()

    def _setup_ui(self):
        self.setWindowTitle(self._window_title)
        self.text_browser.setHtml(self._compose_html())

        self.setLayout(QVBoxLayout(self))

        message_body = "" if not self._message_body else f"<p>{self._message_body}</p>"
        submit_prompt = _(
            'Please consider using the "Submit" button below to let us know about'
            " the issue you encountered. Thanks!"
        )

        info_label_content = f"""
<h2>{self._message_heading}</h2>
{message_body}
<p><i>{submit_prompt}</i></p>
"""

        info_label = QLabel(info_label_content)
        info_label.setWordWrap(True)
        self.layout().addWidget(info_label)
        self.layout().addWidget(self.text_browser)
        self._user_message_label = QLabel(
            self._user_message_label_string.format(chars=self._max_user_message_chars)
        )
        self.layout().addWidget(self._user_message_label)
        self.layout().addWidget(self.text_edit)
        self.layout().addWidget(self.button_box)

        submit_button = self.button_box.addButton(
            _("Submit bug report"), QDialogButtonBox.ButtonRole.AcceptRole
        )
        close_button = self.button_box.addButton(QDialogButtonBox.StandardButton.Close)
        copy_button = self.button_box.addButton(
            _("Copy to clipboard"), QDialogButtonBox.ButtonRole.ActionRole
        )

        submit_button.clicked.connect(self._on_submit_button)
        close_button.clicked.connect(self.reject)
        copy_button.clicked.connect(self._on_copy_button)

        self.setMinimumWidth(800)
        self.setMinimumHeight(600)

    @pyqtSlot(int)
    def _on_message_char_count_updated(self, char_count: int):
        self._user_message_label.setText(
            self._user_message_label_string.format(
                chars=self._max_user_message_chars - char_count
            )
        )

    def _compose_html(self) -> str:
        return f"""
        {self._error_message()}
        {self._debug_message()}
        """

    def _error_message(self) -> str:
        error_msg_title = _("Error message")
        error_msg_html = """<h3>{}:</h3>
        <div style='white-space: pre-wrap; font-family: monospace; font-size: 10pt;'>
          <div>{}</div>
        </div>""".format(
            error_msg_title, html.escape(self._stringify_exception(self._exception))
        )
        return error_msg_html if isinstance(self._exception, Exception) else ""

    def _debug_message(self) -> str:
        debug_msg_title = _("Debug info")
        debug_msg_html = """<h3>{}:</h3>
    <div style='white-space: pre-wrap; font-family: monospace; font-size: 10pt;'>
        <div>{}</div>
    </div>""".format(
            debug_msg_title,
            html.escape(json.dumps(self._debug_data, indent=self._json_indent)),
        )
        return debug_msg_html

    def _stringify_exception(self, exception: Optional[Exception]):
        if not isinstance(exception, Exception):
            return _("Debug")
        stringified = (
            f"{type(exception).__name__}: {exception}\n\n{traceback.format_exc()}"
        )
        safe_print(stringified)
        return stringified

    def _on_copy_button(self):
        QApplication.clipboard().setText(
            json.dumps(self._get_submission_data(), indent=self._json_indent)
        )
        tooltip(_("Copied to clipboard"), parent=self)

    def _get_submission_data(self):
        return {
            "traceback": self._stringify_exception(self._exception),
            "debug": self._debug_data,
            "message": self.text_edit.toPlainText(),
        }

    def _on_submit_button(self):
        self._main_window.progress.start(label=_("Submitting bug report..."))
        ret = self._error_submitter.submit(self._get_submission_data(), self._exception)
        self._main_window.progress.finish()

        if ret:
            tooltip(_("Successfully submitted bug report"), parent=self._main_window)
            self.accept()
        else:
            showWarning(
                _(
                    "Was not able to submit debug info. Please check your network"
                    " connection and try again.\n\nShould things still not work, then"
                    " please use the 'Copy' button to send us the error message"
                    " directly. Thanks!"
                ),
                title=_("Error while submitting debug info"),
                parent=self,
            )


class ErrorCounterOverflowException(Exception):
    def __init__(self, message=None):
        self.message = message

    def __repr__(self):
        return str(self.message)


class ErrorCounter:
    """
    Leaky bucket error counter. Leaks errors at rate_leak = overflow/interval.
    If errors are added at a rate_incr > rate_leak, `ErrorCounterOverflowException is raised.
    The counter is reset after an overflow.
    """

    def __init__(self, interval: Union[int, float], overflow: int):
        self._interval = interval
        self._overflow = overflow
        self._last_time = 0
        self._queue: Deque[float] = deque(maxlen=self._overflow)

    def increase(self):
        """Throws `ErrorCounterOverflowException` if leaky bucket counter overflows."""
        now = time.time()
        self._queue.append(now)
        if (
            len(self._queue) >= self._overflow
            and now - self._queue[0] < self._interval < now - self._last_time
        ):
            self._queue.clear()
            self._last_time = now

            raise ErrorCounterOverflowException(
                _("Reached {} errors in the last {} seconds").format(
                    self._overflow, self._interval
                )
            )
