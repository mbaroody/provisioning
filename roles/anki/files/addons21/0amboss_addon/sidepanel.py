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

import time
from typing import (
    TYPE_CHECKING,
    Callable,
    Deque,
    Iterable,
    List,
    Optional,
    Union,
)
from urllib.parse import ParseResult, parse_qs, urlencode, urlparse

import qtawesome as qta  # type: ignore[import]
from aqt.qt import (
    QEvent,
    QMouseEvent,
    QObject,
    QSplitter,
    QSplitterHandle,
    Qt,
    QTimer,
    QUrl,
    QWidget,
    pyqtSignal,
    pyqtSlot,
)
from aqt.utils import openLink

from .activity import ActivityService
from .anki.utils import is_mac
from .debug import ErrorPromptFactory
from .shared import _
from .sidepanel_web import SidePanelURLRedirector, SidePanelWebPage
from .theme import ThemeManager
from .user import UserService
from .web import URI_BLANK, WebProfile, WebView

if TYPE_CHECKING:
    from aqt.main import AnkiQt

    # 2.1.49 is dev target, thus type-checking assumes Qt5:
    from .gui.forms.qt5 import navbar, sidepanel
else:
    from .gui.forms import navbar, sidepanel

_URI_FRAGMENT_LOGIN = "account/login"
_URI_FRAGMENT_LOGOUT = "account/logout"


class _MainViewSplitter(QSplitter):
    resized = pyqtSignal(int, int)  # custom_widget_size: int

    def __init__(self, theme_manager: ThemeManager, parent: QWidget):
        super().__init__(parent=parent)
        self.setHandleWidth(8)
        self.setStyleSheet(
            f"""
QSplitter::handle {{
    background: {theme_manager.color("splitter-bg")};
    border: none;
}}
QSplitter::handle::hover {{
    background: {theme_manager.color("splitter-hover-bg")};
}}
QSplitter::handle::pressed {{
    background: {theme_manager.color("splitter-pressed-bg")};
}}
"""
        )
        self.setOpaqueResize(False)
        self.setContentsMargins(0, 0, 0, 0)
        self._last_sizes: Optional[List[int]] = None

    def toggle_custom_widget_maximized(self):
        if self._is_main_view_collapsed():
            if self._last_sizes:
                self._restore_sizes()
            else:
                self.equalize_panes()
        else:
            self._last_sizes = self.sizes()
            self.maximize_custom_widget()

    def toggle_equalize_panes(self):
        if self._is_equalized() and self._last_sizes:
            self._restore_sizes()
        else:
            self._last_sizes = self.sizes()
            self.equalize_panes()

    def maximize_custom_widget(self):
        self.setSizes([0, self._max_width()])

    def equalize_panes(self):
        # Stretch factors do not work reliably for QSplitters, so in order to
        # achieve an equal split, we set the size of both widgets to an equal
        # value that is higher than each widget's minimum size. The most sensible
        # source for that number is the width of the parent widget which cannot
        # be lower than any of its childrens' minimum widths.
        self.setSizes([self._max_width(), self._max_width()])

    def _max_width(self):
        return self.parent().width()  # type: ignore

    @property
    def main_handle(self) -> QSplitterHandle:
        return self.handle(1)

    def _restore_sizes(self):
        if self._last_sizes is None:
            raise ValueError("No last sizes stored")
        self.setSizes(self._last_sizes)

    def _is_main_view_collapsed(self):
        main_view = self.widget(0)
        return self.sizes()[0] <= main_view.minimumSize().width()

    def _is_equalized(self):
        size_left, size_right = self.sizes()
        return size_left == size_right or abs(size_left - size_right) == 1

    # Resize event propagation:

    def setSizes(self, sizes: Iterable[int]):
        super().setSizes(sizes)
        self.signal_resized()

    def signal_resized(self):
        self.resized.emit(*self.sizes())


class _SplitterHandleEventFilter(QObject):
    """
    Qt Event filter, installable on a _MainViewSplitter splitter handle

    Signals mouse-click events back to subscribers in _MainViewSplitter,
    mediating UI interactions like double-clicking the splitter handle to
    prompt resizing the panes

    TODO: Use signal/slot connections instead of mediating directly between objects
    """

    def __init__(self, main_view_splitter: _MainViewSplitter):
        super().__init__(parent=main_view_splitter)
        self._main_view_splitter = main_view_splitter
        self._click_timer: QTimer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.timeout.connect(self._main_view_splitter.signal_resized)
        self._is_double: bool = False

    def eventFilter(self, object: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.MouseButtonDblClick:
            self._is_double = True
            self._main_view_splitter.toggle_equalize_panes()
            return True
        elif (
            event.type() == QEvent.Type.MouseButtonRelease
            and event.button() == Qt.MouseButton.LeftButton  # type: ignore[attr-defined]
        ):
            # Prevent firing twice on double-click by using a QTimer to wait
            # before signalling click release event and cancelling queued timers
            # when events are fired in quick sequence
            if self._click_timer.isActive():
                self._click_timer.stop()
            else:
                self._click_timer.start(500)

            if self._is_double:
                # override default mouse-click release handlers to prevent
                # erroneously re-resizing on mouse release
                self._is_double = False
                return True

        return super().eventFilter(object, event)


class _MainViewWidgetInjector:
    _injected: bool = False

    def __init__(self, main_window: "AnkiQt"):
        self._main_window = main_window

    def inject_panel(self, widget: QWidget, splitter: QSplitter):
        if self._injected:
            raise Exception("Side panel may only be injected once")

        widget_index = self._main_window.mainLayout.indexOf(self._main_window.web)

        self._main_window.mainLayout.removeWidget(self._main_window.web)

        splitter.addWidget(self._main_window.web)
        splitter.addWidget(widget)

        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

        # NOTE: Setting main view pane to a large int ensures that it is given
        # preference when stretching widgets. 400 is a good compromise between
        # article styling and size
        splitter.setSizes([10000, 400])

        self._main_window.mainLayout.insertWidget(widget_index, splitter)

        self._injected = True


class _NavBar(QWidget):
    home_clicked = pyqtSignal()
    back_clicked = pyqtSignal()
    forward_clicked = pyqtSignal()
    external_browser_clicked = pyqtSignal()

    _themed_qss = """\
QLabel{{color: {text-fg};}}

QPushButton{{border:none;}}

QPushButton:hover{{background-color: "{button-hover-bg}";}}

QPushButton:pressed{{background-color: "{button-pressed-bg}";}}\
"""

    def __init__(self, theme_manager: ThemeManager, parent: QWidget):
        super().__init__(parent=parent)
        self._theme_manager = theme_manager
        self._form = navbar.Ui_NavBar()
        self._form.setupUi(self)
        self.setObjectName("amboss_sidepanel_navbar")
        self._translate_ui()
        self._setup_theme()
        self._setup_signals()

    def set_forward_enabled(self, state: bool):
        self._form.button_forward.setEnabled(state)

    def set_back_enabled(self, state: bool):
        self._form.button_back.setEnabled(state)

    def _setup_signals(self):
        self._form.button_back.clicked.connect(self.back_clicked.emit)
        self._form.button_forward.clicked.connect(self.forward_clicked.emit)
        self._form.button_home.clicked.connect(self.home_clicked.emit)
        self._form.button_external.clicked.connect(self.external_browser_clicked.emit)

    def _setup_theme(self):
        navbar_qss = self._themed_qss.format(**self._theme_manager.colors_dict())

        form = self._form

        form.label_title.setStyleSheet(navbar_qss)

        for button in (
            form.button_back,
            form.button_forward,
            form.button_home,
            form.button_external,
        ):
            button.setStyleSheet(navbar_qss)

        icon_color = self._theme_manager.color("text-fg")

        form.button_back.setIcon(qta.icon("mdi.chevron-left", color=icon_color))
        form.button_forward.setIcon(qta.icon("mdi.chevron-right", color=icon_color))
        form.button_home.setIcon(qta.icon("mdi.home", color=icon_color))
        form.button_external.setIcon(
            qta.icon(
                "mdi.open-in-new", scale_factor=0.8, offset=(0, 0.1), color=icon_color
            )
        )

    def _translate_ui(self):
        self.setWindowTitle(_("SidePanel"))
        self._form.button_back.setToolTip(_("One page back"))
        self._form.button_forward.setToolTip(_("One page forward"))
        self._form.label_title.setText(_("AMBOSS viewer"))
        self._form.button_home.setToolTip(_("Go to your dashboard"))
        self._form.button_external.setToolTip(
            _("Open current page in external browser")
        )


class _NavBarEventFilter(QObject):
    """
    Qt Event filter, installable on a _NavBar instance

    Signal double-click event to a _MainViewSplitter, prompting pane resizing

    TODO: Use signal/slot connections instead of mediating directly between objects
    """

    def __init__(self, main_view_splitter: _MainViewSplitter):
        super().__init__(parent=main_view_splitter)
        self._main_view_splitter = main_view_splitter

    def eventFilter(self, object: QObject, event: Union[QMouseEvent, QEvent]) -> bool:
        if event.type() == QEvent.Type.MouseButtonDblClick:
            self._main_view_splitter.toggle_custom_widget_maximized()
            return True
        return super().eventFilter(object, event)


class SidePanel(QWidget):
    logout_requested = pyqtSignal()
    external_browser_requested = pyqtSignal(str)
    url_changed = pyqtSignal(str)
    url_redirected = pyqtSignal(str, str)
    navigated = pyqtSignal(str)  # navigated_to: str

    def __init__(
        self,
        web_profile: WebProfile,
        home_uri: str,
        login_uri: str,
        url_redirector: SidePanelURLRedirector,
        theme_manager: ThemeManager,
        main_window: "AnkiQt",
        anki_version: Optional[str] = None,
        on_bridge_cmd: Optional[Callable] = None,
    ):
        # Needed for AltGr shortcuts workaround. Has to be initialized ahead of any
        # potential events fired off
        self._altgr_pressed: bool = False

        super().__init__(parent=main_window)

        self._theme_manager = theme_manager
        self._home_uri = home_uri
        self._login_uri = login_uri

        self._form = sidepanel.Ui_SidePanel()
        self._form.setupUi(self)
        self.setObjectName("amboss_sidepanel")

        self._web_view = WebView(
            theme_manager=self._theme_manager,
            history_filter=_side_panel_history_filter,
            parent=self,
            object_name="amboss_sidepanel_webview",
        )
        self._web_page = SidePanelWebPage(
            web_profile=web_profile,
            url_redirector=url_redirector,
            main_window=main_window,
            anki_version=anki_version,
            on_bridge_cmd=on_bridge_cmd,
            parent=self._web_view,
        )
        self._web_view.setPage(self._web_page)

        self._navbar = _NavBar(theme_manager, self)

        self._setup_layout()
        self._setup_signals()

        self.set_logged_in()

    def event(self, event: QEvent) -> bool:
        """Main event handler

        All widget events pass through here before being passed on to more specific
        handlers. We use this reimplementation to capture and handle certain events that
        help us deal with certain Qt bugs.
        """
        event_type = event.type()

        # Keep track of AltGr state for workaround below
        # "Think differently": Qt.Key_AltGr does not register on macOS, so we
        # have to fall back to using a magic key number. For whatever reason, Qt
        # does not provide an enum for this.
        if event.type() == QEvent.Type.KeyPress and (
            event.key() == Qt.Key.Key_AltGr or event.key() == 16777251  # type: ignore[attr-defined]
        ):
            self._altgr_pressed = True

        elif event.type() == QEvent.Type.KeyRelease and (
            event.key() == Qt.Key.Key_AltGr or event.key() == 16777251  # type: ignore[attr-defined]
        ):
            self._altgr_pressed = False

        if event_type != QEvent.Type.ShortcutOverride:
            return super().event(event)

        # Workaround: Override main window shortcuts in auth view or when AltGr pressed
        #
        # Addresses a series of Qt bugs regarding keyboard focus handling in web views
        # Present for all hotkeys in 2.1.23-2.1.26 on macOS, 2.1.15-2.1.26 on Windows
        # Present for AltGr specifically in Anki versions 2.1.28+ on macOS and Windows
        # Example of an upstream report: https://bugreports.qt.io/browse/QTBUG-85450
        #
        # NOTE: Does not fix keyboard entry in search field or other hotkey conflicts
        # (e.g. when in a Qbank session). We should evaluate whether to just blanket-
        # intercept all main window hotkeys when side panel is focused

        # assumes that login and registration URLs use the same path
        if (
            self._web_view.url().fileName() == QUrl(self._login_uri).fileName()
            or self._altgr_pressed
        ):
            event.accept()
            return True

        return False

    def set_bridge_command(self, on_bridge_cmd: Optional[Callable]):
        self._web_page.setBridgeCommand(on_bridge_cmd)

    def _setup_layout(self):
        self._form.layout_navbar.addWidget(self._navbar)
        self._form.layout_main.addWidget(self._web_view)

        if is_mac:
            # Layout spacing on macOS is way too generous by default, so we adjust it
            self._form.mainLayout.setContentsMargins(0, 3, 0, 0)
            self._form.mainLayout.setSpacing(3)

    def _setup_signals(self):
        self._web_view.urlChanged.connect(self._on_url_changed)
        self._web_page.url_redirected.connect(self.url_redirected.emit)
        self._navbar.back_clicked.connect(self.go_back)
        self._navbar.forward_clicked.connect(self.go_forward)
        self._navbar.home_clicked.connect(self.go_home)
        self._navbar.external_browser_clicked.connect(self._on_external_browser_clicked)

    def set_logged_out(self):
        self._navbar.setEnabled(False)

    def set_logged_in(self):
        self._navbar.setEnabled(True)

    def load_login_page(self):
        self.load_url(self._login_uri)

    def load_url(self, url: str):
        self._web_view.setUrl(QUrl(url))

    @pyqtSlot()
    def go_forward(self, navbar=True):
        if navbar:
            self.navigated.emit("forwards")
        self._web_view.navigate_forward()

    @pyqtSlot()
    def go_back(self, navbar=True):
        if navbar:
            self.navigated.emit("backwards")
        self._web_view.navigate_back()

    @pyqtSlot()
    def go_home(self, navbar=True):
        if navbar:
            self.navigated.emit("home")
        self.load_url(self._home_uri)

    @property
    def web_view(self):
        return self._web_view

    @property
    def navbar(self):
        return self._navbar

    @pyqtSlot()
    def _on_external_browser_clicked(self):
        url = self._web_view.url().toString()
        if url == URI_BLANK:
            url = self._home_uri
        self.navigated.emit(url)
        self.external_browser_requested.emit(url)

    @pyqtSlot(QUrl)
    def _on_url_changed(self, url: QUrl):
        self.navbar.set_back_enabled(self._web_view.can_navigate_back())
        self.navbar.set_forward_enabled(self._web_view.can_navigate_forward())
        self.url_changed.emit(url.toString())


class _WebViewEventFilter(QObject):
    """
    Qt Event filter, installable on a WebView instance

    Signal mouse-click events to a SidePanel instance, controlling
    back/forwards navigation

    TODO: Use signal/slot connections instead of mediating directly between objects
    """

    def __init__(self, side_panel: SidePanel):
        super().__init__(parent=side_panel)
        self._side_panel = side_panel

    def eventFilter(self, object: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.MouseButtonRelease:
            button = event.button()  # type:ignore[attr-defined]
            if button == Qt.MouseButton.BackButton:
                self._side_panel.go_back(False)
                return True
            elif button == Qt.MouseButton.ForwardButton:
                self._side_panel.go_forward(False)
                return True
        return super().eventFilter(object, event)


class _ChildEventFilter(QObject):
    """
    Install a predefined event filter on all child widgets added to a widget
    during its runtime.
    """

    def __init__(self, parent_filter: QObject, parent: QObject):
        super().__init__(parent)
        self._parent_filter = parent_filter

    def eventFilter(self, object: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.ChildAdded:
            child: QObject = event.child()  # type: ignore[attr-defined]
            child.installEventFilter(self._parent_filter)
        return False


def _side_panel_history_filter(url: str) -> bool:
    return url != URI_BLANK and not any(
        i in url for i in (_URI_FRAGMENT_LOGIN, _URI_FRAGMENT_LOGOUT)
    )


class SidePanelController(QObject):
    logout_requested = pyqtSignal()
    toggled = pyqtSignal(bool, str)  # shown: bool, origin: str
    resized = pyqtSignal(int, int)  # main_view_width: int, side_panel_width: int

    def __init__(
        self,
        main_window: "AnkiQt",
        side_panel: SidePanel,
        user_service: UserService,
        history: Deque[str],
        local_url_fragment_auth: str,
        theme_manager: ThemeManager,
        error_prompt_factory: ErrorPromptFactory,
    ):
        super().__init__(parent=main_window)
        self._main_window = main_window
        self._side_panel = side_panel
        self._user_service = user_service
        self._history = history
        self._local_url_fragment_auth = local_url_fragment_auth
        self._error_prompt_factory = error_prompt_factory

        self._splitter = _MainViewSplitter(theme_manager, self._main_window)
        self._injector = _MainViewWidgetInjector(self._main_window)
        self._injector.inject_panel(self._side_panel, self._splitter)
        self._side_panel.hide()

        self._setup_signals()
        self._setup_event_filters()
        self._setup_style()

        self._shown_before: bool = False
        self._main_window_min_width = self._main_window.minimumWidth()

    def _setup_signals(self):
        self._side_panel.url_redirected.connect(self._on_url_redirected)
        self._side_panel.external_browser_requested.connect(
            self._on_external_browser_requested
        )
        self._side_panel.logout_requested.connect(self.logout_requested.emit)
        self._splitter.resized.connect(self.resized.emit)

    def _setup_event_filters(self):
        splitter_handle_event_filter = _SplitterHandleEventFilter(self._splitter)
        self._splitter.main_handle.installEventFilter(splitter_handle_event_filter)

        nav_bar_event_filter = _NavBarEventFilter(self._splitter)
        self._side_panel.navbar.installEventFilter(nav_bar_event_filter)

        web_view = self._side_panel.web_view
        web_view_event_filter = _WebViewEventFilter(self._side_panel)

        if web_view.focusProxy() is not None:
            web_view.installEventFilter(web_view_event_filter)
        else:
            # Qt idiosyncracy: Focus proxy will change during the runtime of the web
            # view, so use a special wrapping filter to apply the event filter on all
            # child widgets created during the web view's runtime
            # cf. https://bugreports.qt.io/browse/QTBUG-43602
            web_view_child_event_filter = _ChildEventFilter(
                web_view_event_filter, web_view
            )
            web_view.installEventFilter(web_view_child_event_filter)

    def _setup_style(self):
        self._splitter.main_handle.setAttribute(Qt.WidgetAttribute.WA_Hover)

    def toggle(self, show: Optional[bool] = None, origin: Optional[str] = None):
        will_show = show is True or not self._side_panel.isVisible()

        if will_show and not self._shown_before:
            if origin != "show-url":
                # Load different starting page depending on auth state
                if self._user_service.is_logged_in():
                    self._side_panel.go_home(navbar=False)
                else:
                    self._side_panel.load_login_page()
            self._shown_before = True

        if will_show:
            # Big enough for Anki main area + sidebar image barely larger than most tooltip sizes (640px and below),
            # small enough for lowest targeted screen resolution of 1024px width
            self._main_window.setMinimumWidth(1024)
        else:
            self._main_window.setMinimumWidth(self._main_window_min_width)

        self._side_panel.setVisible(will_show)
        self.toggled.emit(will_show, origin or "")

    def show_url(self, url: str):
        self._side_panel.web_view.load(QUrl(url))
        self.toggle(True, "show-url")

    @pyqtSlot()
    def set_logged_in(self):
        self._side_panel.set_logged_in()
        if self._side_panel.isVisible():
            if self._history:
                self._side_panel.load_url(self._history.pop())
            else:
                self._side_panel.go_home()

    @pyqtSlot()
    def set_logged_out(self):
        self._side_panel.set_logged_out()
        if self._side_panel.isVisible():
            self._side_panel.load_login_page()

    @pyqtSlot(Exception)
    def on_login_error(self, exception: Exception):
        self._error_prompt_factory.create_and_exec(
            exception=exception,
            message_heading=_(
                "Encountered an error while trying to log into AMBOSS sidebar."
            ),
        )

    @pyqtSlot(str, str)
    def _on_url_redirected(self, url_fragment: str, redirected_to: str):
        if (
            self._user_service.is_logged_in()
            and self._local_url_fragment_auth in redirected_to
        ):
            self._user_service.logout()

    @pyqtSlot(str)
    def _on_external_browser_requested(self, url: str):
        url_parts = urlparse(url)
        url_query = parse_qs(url_parts.query)
        url_query["utm_medium"] = ["anki"]
        url_query["utm_source"] = ["navbar"]
        openLink(
            ParseResult(
                scheme=url_parts.scheme,
                netloc=url_parts.hostname,  # type: ignore[arg-type]
                path=url_parts.path,
                params=url_parts.params,
                query=urlencode(url_query, doseq=True),
                fragment=url_parts.fragment,
            ).geturl()
        )


class SidePanelActivityRegistry(QObject):
    def __init__(
        self, activity_service: ActivityService, parent: QObject, side_panel: SidePanel
    ):
        super().__init__(parent=parent)
        self._activity_service = activity_service
        self._side_panel = side_panel

    start: float = 0

    @pyqtSlot(bool, str)
    def register_toggled(self, shown: bool, origin: str):
        elapsed: float = 0
        if shown:
            self.start = time.perf_counter()
        else:
            elapsed = round(time.perf_counter() - self.start, 2)
            self.start = 0

        self._activity_service.register_activity(
            "sidepanel.toggled",
            {"shown": shown, "origin": origin, "shownForSeconds": elapsed or None},
        )

    @pyqtSlot(int, int)
    def register_resized(self, main_view_width: int, side_panel_width: int):
        total_width = main_view_width + side_panel_width
        width_ratio = round(side_panel_width / total_width, 2) if total_width else None
        self._activity_service.register_activity(
            "sidepanel.resized", {"width": side_panel_width, "ratio": width_ratio}
        )

    @pyqtSlot(str)
    def register_navigated(self, navigated_to: str):
        self._activity_service.register_activity(
            "sidepanel.navbar.navigated", {"navigatedTo": navigated_to}
        )
