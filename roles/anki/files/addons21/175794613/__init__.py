# Anki Leaderboard
# Copyright (C) 2020 - 2024 Thore Tyborski <https://github.com/ThoreBor>
# Copyright (C) 2024 Shigeyuki <http://patreon.com/Shigeyuki>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from aqt import mw
from aqt.qt import QAction, QMenu, QKeySequence
from aqt.utils import showInfo, showWarning, tooltip, askUser, openLink
from aqt.operations import QueryOp
from anki.utils import pointVersion

from os.path import dirname, join, realpath
import os
import webbrowser
import requests
from bs4 import BeautifulSoup
import datetime
import json

from .custom_shige.random_error import custom_error

from .Leaderboard import start_main
from .config import start_config
from .Stats import Stats
from .config_manager import write_config
from .lb_on_homescreen import leaderboard_on_deck_browser, on_deck_browser_will_render_content
from .version import version
from .api_connect import *

from .custom_shige.path_manager import *
from .shige_pop.popup_config import set_gui_hook_change_log, change_log_popup_B
set_gui_hook_change_log()
from .custom_shige.translate.translate import ShigeTranslator
_translate = ShigeTranslator.translate

from .custom_shige.shige_pycmd import set_gui_hooks_leaderboard
set_gui_hooks_leaderboard()

from .user_icon_uploader import upload_image_request
from .custom_shige.count_time import shigeTaskTimer
from .shigeAPI import shigeAPI

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .leaderboardV2.build_bord_v2 import RebuildLeaderbord

startup_shige_leaderboard = None

class startup():
    def __init__(self):
        # ｼｰｽﾞﾝのﾃﾞﾌｫﾙﾄ値を設定
        self.start = datetime.datetime.now()
        self.end = datetime.datetime.now()
        self.currentSeason = ""
        self.last_checked_time = None
        self.LeaderboardV2 = None #type: RebuildLeaderbord

        config = mw.addonManager.getConfig(__name__)

        # self.addMenu(MENU_NAME, "&leaderboard-V2", rebuild_leaderboard, 'Shift+G')
        # self.addMenu(MENU_NAME, _translate(TRANSLATE_MENU, "&Open leaderboard"), self.leaderboard, 'Shift+L')

        # Create menu
        self.addMenu(MENU_NAME, _translate(TRANSLATE_MENU, "&Open leaderboard"), self.rebuild_leaderboard, 'Shift+L')
        self.addMenu(MENU_NAME, _translate(TRANSLATE_MENU, "&Sync and update"), self.startBackgroundSync, "Shift+S")
        # self.addMenu(MENU_NAME, _translate(TRANSLATE_MENU, "&GetSyncV2"), self.startBackgroundSyncV2, "Shift+G") #test
        self.addMenu(MENU_NAME, _translate(TRANSLATE_MENU, "&Config"), self.invokeSetup, "Alt+C")
        # self.addMenu(MENU_NAME, "&Make a feature request or report a bug", self.github)
        self.addMenu(MENU_NAME, "&Upload profile image", upload_image_request)

        self.addMenu(MENU_NAME, _translate(TRANSLATE_MENU, "&Web site"), lambda: openLink("https://shigeyuki.pythonanywhere.com/"))
        self.addMenu(MENU_NAME, _translate(TRANSLATE_MENU, "&Change Log"), change_log_popup_B)
        mw.addonManager.setConfigAction(__name__, self.configSetup)

        try:
            from aqt import gui_hooks
            gui_hooks.profile_did_open.append(self.profileHook)
            gui_hooks.addons_dialog_will_delete_addons.append(self.deleteHook)
            # if config["autosync"] == True:
            #     gui_hooks.reviewer_will_end.append(self.startBackgroundSync)
            # if config["autosync"] == True:
            gui_hooks.reviewer_will_end.append(self.reviewer_will_end_start_sync)

            # Rearrange home addonsの互換性を追加 ----
            gui_hooks.deck_browser_will_render_content.remove(on_deck_browser_will_render_content)
            gui_hooks.deck_browser_will_render_content.append(on_deck_browser_will_render_content)
            # ----------------------------------------

        except:
            if config["import_error"] == True:
                showInfo("Because you're using an older Anki version some features of the Leaderboard add-on can't be used.", title="Leaderboard")
                write_config("import_error", False)

    def rebuild_leaderboard(self):
        config = mw.addonManager.getConfig(__name__)
        if config.get("gamification_mode", True):
            if config["username"] == "" or not config["authToken"]:
                self.invokeSetup()
            else:
                from .leaderboardV2.build_bord_v2 import RebuildLeaderbord
                from .leaderboardV2.leaderboardV2 import LeaderBoardV2

                if isinstance(self.LeaderboardV2, RebuildLeaderbord):
                    self.LeaderboardV2.cancel_execution = True
                if (hasattr(self.LeaderboardV2, "pagination_board")
                and isinstance(self.LeaderboardV2.pagination_board, LeaderBoardV2)):
                    self.LeaderboardV2.pagination_board.close()
                self.LeaderboardV2 = RebuildLeaderbord()
        else:
            self.leaderboard()


    def profileHook(self):
        config = mw.addonManager.getConfig(__name__)
        self.checkInfo()
        self.checkBackup()
        write_config("achievement", True)
        write_config("homescreen_data", [])
        self.addUsernameToFriendlist()

        # custom -------
        # Anki起動時のｼｰｽﾞﾝのﾁｪｯｸをﾊﾞｯｸｸﾞﾗｳﾝﾄﾞへ移動
        self.profile_season_sync()

        # self.season()
        # # if config["homescreen"] == True:
        # if config["username"] == "" or not config["authToken"]:
        #     return
        # if config["homescreen"] == True:
        #     self.startBackgroundSync()
        # ---------

    # custom --------------------
    def check_time_and_update_season(self):
        # 起動時のｼｰｽﾞﾝの取得が失敗した場合に再更新する
        # 6時間に1回ｼｰｽﾞﾝを更新する
        try:
            current_time = datetime.datetime.now()
            if (not isinstance(self.last_checked_time, datetime.datetime)
                or (current_time - self.last_checked_time).total_seconds() >= 6 * 3600):
                self.season()
        except:
            pass


    def profile_season_sync(self):
        # ｼｰｽﾞﾝのﾃﾞﾌｫﾙﾄ値を設定 # initへ移動
        # self.start = datetime.datetime.now()
        # self.end = datetime.datetime.now()
        # self.currentSeason = ""

        op = QueryOp(parent=mw, op=lambda col: self.season(), success=self.profile_season_sync_on_success)
        if pointVersion() >= 231000:
            op.without_collection()
        op.run_in_background()

    def profile_season_sync_on_success(self, result):
        # if config["homescreen"] == True:
        config = mw.addonManager.getConfig(__name__)
        if config["username"] == "" or not config["authToken"]:
            return
        if config["homescreen"] == True:
            self.startBackgroundSync()
    # ---------------------------


    def leaderboard(self):
        config = mw.addonManager.getConfig(__name__)
        if config["username"] == "" or not config["authToken"]:
            self.invokeSetup()
        else:
            # mw.shige_leaderboard = start_main(self.start, self.end, self.currentSeason)
            if hasattr(mw, 'shige_leaderboard') and isinstance(mw.shige_leaderboard, start_main):
                mw.shige_leaderboard.close()
                mw.shige_leaderboard.deleteLater()
            # mw.shige_leaderboard = start_main(self.start, self.end, self.currentSeason, mw)

            if config.get("allways_on_top", False):
                bord_parent = None
            else:
                bord_parent = mw
            mw.shige_leaderboard = start_main(self.start, self.end, self.currentSeason, bord_parent)


    def invokeSetup(self):
        if hasattr(mw, 'shige_lb_setup') and isinstance(mw.shige_lb_setup, start_config):
            mw.shige_lb_setup.close()
            mw.shige_lb_setup.deleteLater()
        mw.shige_lb_setup = start_config(self.start, self.end, mw)
        mw.shige_lb_setup.show()
        mw.shige_lb_setup.raise_()
        mw.shige_lb_setup.activateWindow()

    def configSetup(self):
        if hasattr(mw, 'shige_lb_setup') and isinstance(mw.shige_lb_setup, start_config):
            mw.shige_lb_setup.close()
            mw.shige_lb_setup.deleteLater()
        mw.shige_lb_setup = start_config(self.start, self.end, mw)
        if mw.shige_lb_setup.exec():
            pass

    def github(self):
        # webbrowser.open(WEBBROWSER_OPEN_GITHUB_URL)
        webbrowser.open(WEBBROWSER_OPEN_GITHUB_URL)

    def checkInfo(self):
        return
        config = mw.addonManager.getConfig(__name__)
        try:
            url = CHECK_INFO_URL
            page = requests.get(url, timeout=10)
            soup = BeautifulSoup(page.content, 'html.parser')
            if soup.find(id='show_message').get_text() == "True":
                info = soup.find("div", id="Message")
                notification_id = soup.find("div", id="id").get_text()
                if config["notification_id"] != notification_id:
                    showInfo(str(info), title="Leaderboard")
                    write_config("notification_id", notification_id)
        except Exception as e:
            showWarning(f"Timeout error [checkInfo] - No internet connection, or server response took too long.\n {e}", title="Leaderboard error")

    def addUsernameToFriendlist(self):
        # Legacy
        config = mw.addonManager.getConfig(__name__)
        if config['username'] != "" and config['username'] not in config['friends']:
            friends = config["friends"]
            friends.append(config['username'])
            write_config("friends", friends)

    def reviewer_will_end_start_sync(self, *args, **kwargs):
        config = mw.addonManager.getConfig(__name__)
        if config["autosync"] == True:
            self.startBackgroundSync()


    def startBackgroundSync(self):
        op = QueryOp(parent=mw, op=lambda col: self.backgroundSync(), success=self.on_success)
        # https://github.com/ThoreBor/Anki_Leaderboard/pull/229
        # op.with_progress().run_in_background()
        if pointVersion() >= 231000:
            op.without_collection()
        op.run_in_background()


    def startBackgroundSyncV2(self):
        # test
        shigeTaskTimer.start("GetSyncV2")
        op = QueryOp(parent=mw, op=lambda col: self.backgroundSyncV2(), success=self.on_success_V2)
        if pointVersion() >= 231000:
            op.without_collection()
        op.run_in_background()


    def backgroundSyncV2(self):
        # test
        self.check_time_and_update_season()
        self.response = getRequestV2("shige_api/get_sync_cards/", 200, False)
        try:
            if self.response.status_code == 200:
                write_config("homescreen_data", [])
                return False
            else:
                return self.response.text
        except:
            return self.response


    def backgroundSync(self):
        self.check_time_and_update_season() # TODO:秒数がかかるので"sync/"に組み込む

        config = mw.addonManager.getConfig(__name__)
        streak, cards, time, cardsPast30Days, retention, leagueReviews, leagueTime, leagueRetention, leagueDaysPercent = Stats(self.start, self.end)

        if datetime.datetime.now() < self.end:
            data = {'username': config['username'], "streak": streak, "cards": cards, "time": time, "syncDate": datetime.datetime.now(),
            "month": cardsPast30Days, "country": config['country'].replace(" ", ""), "retention": retention,
            "leagueReviews": leagueReviews, "leagueTime": leagueTime, "leagueRetention": leagueRetention, "leagueDaysPercent": leagueDaysPercent,
            "authToken": config["authToken"], "version": version, "updateLeague": True, "sortby": config["sortby"]}
        else:
            data = {'username': config['username'], "streak": streak, "cards": cards, "time": time, "syncDate": datetime.datetime.now(),
            "month": cardsPast30Days, "country": config['country'].replace(" ", ""), "retention": retention,
            "authToken": config["authToken"], "version": version, "updateLeague": False, "sortby": config["sortby"]}

        self.response = postRequest("sync/", data, 200, False)
        try:
            if self.response.status_code == 200:
                write_config("homescreen_data", [])
                return False
            else:
                return self.response.text
        except:
            return self.response

    def on_success(self, result):
        if result:
            if "Timeout" in result:
                custom_error()
            else:
                custom_error(result)
                # showWarning(result, title="Leaderboard Error")
        else:
            leaderboard_on_deck_browser(self.response.json())

    def on_success_V2(self, result):
        # test
        shigeTaskTimer.end("GetSyncV2")
        if result:
            if "Timeout" in result:
                custom_error()
            else:
                custom_error(result)
                # showWarning(result, title="Leaderboard Error")
        else:
            leaderboard_on_deck_browser(self.response.json())


    def season(self):
        # TODO: ｼｰｽﾞﾝはAnkiの起動時に同期される､なので再起動しない場合開始時刻がずれる
        # TODO: ｼｰｽﾞﾝの開始時刻と終わりの時刻にｽﾞﾚがある(ｸﾞﾛｰﾊﾞﾙ時刻､ﾛｰｶﾙ時刻)
        # Next season didn't begin for me #164
        # https://github.com/ThoreBor/Anki_Leaderboard/issues/164

        response = getRequest("season/", False)
        if response:
            response = response.json()
            self.start = response[0]
            self.start = datetime.datetime(self.start[0],self.start[1],self.start[2],self.start[3],self.start[4],self.start[5])
            self.end = response[1]
            self.end = datetime.datetime(self.end[0],self.end[1],self.end[2],self.end[3],self.end[4],self.end[5])
            self.currentSeason = response[2]
            self.last_checked_time = datetime.datetime.now() # add
        else:
            self.start = datetime.datetime.now()
            self.end = datetime.datetime.now()
            self.currentSeason = ""


    def deleteHook(self, dialog, ids):
        config = mw.addonManager.getConfig(__name__)
        showInfoDeleteAccount = """<h3>Deleting Leaderboard Account</h3>
        Keep in mind that deleting the add-on only removes the local files. If you also want to delete your account, go to
        Leaderboard>Config>Account>Delete account.
        """
        askUserCreateMetaBackup = """
        <h3>Leaderboard Configuration Backup</h3>
        If you want to reinstall this add-on in the future, creating a backup of the configurations is recommended. Do you want to create a backup?
        """
        if ADDON_ID in ids or ADD_ON_NAME in ids:
            showInfo(showInfoDeleteAccount)
            if askUser(askUserCreateMetaBackup):
                meta_backup = open(join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "leaderboard_meta_backup.json"), "w", encoding="utf-8")
                meta_backup.write(json.dumps({"config": config}))
                meta_backup.close()
                tooltip("Successfully created a backup")

    def checkBackup(self):
        askUserRestoreFromBackup = """<h3>Leaderboard configuration backup found</h3>
        Do you want to restore your configurations?
        """
        backup_path = join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "leaderboard_meta_backup.json")
        if os.path.exists(backup_path):
            meta_backup = open(backup_path, "r", encoding="utf-8")
            if askUser(askUserRestoreFromBackup):
                new_meta = open(join(dirname(realpath(__file__)), "meta.json"), "w", encoding="utf-8")
                new_meta.write(json.dumps(json.loads(meta_backup.read())))
                new_meta.close()
                meta_backup.close()
            os.remove(backup_path)

    def addMenu(self, parent, child, function, shortcut=None):
        menubar = [i for i in mw.form.menubar.actions()]
        if parent in [i.text() for i in menubar]:
            menu = [i.parent() for i in menubar][[i.text() for i in menubar].index(parent)]
        else:
            menu = mw.form.menubar.addMenu(parent) # type: QMenu
        item = QAction(child, menu)
        # https://github.com/ThoreBor/Anki_Leaderboard/issues/195
        item.setMenuRole(QAction.MenuRole.NoRole) #🐞追加
        item.triggered.connect(function)
        if shortcut:
            item.setShortcut(QKeySequence(shortcut))
        menu.addAction(item)

startup_shige_leaderboard = startup()

def get_startup_shige_leaderboard():
    return startup_shige_leaderboard

# for my add-on: BreakTimer https://ankiweb.net/shared/info/174058935
shigeAPI.open_leaderboard.add(startup_shige_leaderboard.rebuild_leaderboard)