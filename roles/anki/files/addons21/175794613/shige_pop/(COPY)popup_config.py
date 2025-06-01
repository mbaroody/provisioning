# Shigeyuki <https://www.patreon.com/Shigeyuki>

from aqt import QAction, QDialog, QHBoxLayout, QIcon, QResizeEvent, QTextBrowser, Qt, qconnect
from aqt import QVBoxLayout, QLabel, QPushButton
from aqt import mw
from os.path import join, dirname
from aqt import QPixmap,gui_hooks
from aqt.utils import openLink
from ..custom_shige.path_manager import ADDON_ID
from ..config_manager import write_config
from .patreons_list import PATRONS_LIST #🟢


from .change_log import OLD_CHANGE_LOG #🟢

CHANGE_LOG = "shige_chang_log_day"
# CHANGE_LOG_DAY = "2024-10-27g"
CHANGE_LOG_DAY = "2024-11-10c" #🟢
CHANGE_LOG_DEFAULT = ""
# -> config.manager.pyに追加


#🟢 AnkiWebのﾊﾟﾄﾛﾝのﾘｽﾄを更新
# https://ankiweb.net/shared/info/175794613

SPECIAL_THANKS ="""\
[ Patreon ] Special thanks
Without the support of my Patrons, I would never have been
able to develop this. Thank you very much!🙏"""


# popup-size
# mini-pupup
SIZE_MINI_WIDTH = 464
SIZE_MINI_HEIGHT = 536
# Width: 464, Height: 536

# Large-popup
SIZE_BIG_WIDTH = 600
SIZE_BIG_HEIGHT = 500


POKEBALL_PATH = r"popup_icon.png"

THE_ADDON_NAME = "🏆️Anki Leaderboard (Fixed by Shige)"
SHORT_ADDON_NAME = "Anki Leaderboard" # not used

GITHUB_URL = "https://github.com/shigeyukey/my_addons/issues" #🟢



ANKI_WEB_URL = ""
RATE_THIS_URL = ""

if ADDON_ID:
    ADDON_PACKAGE = ADDON_ID
else:
    ADDON_PACKAGE = mw.addonManager.addonFromModule(__name__)

# ｱﾄﾞｵﾝのURLが数値であるか確認
if (isinstance(ADDON_PACKAGE, (int, float))
    or (isinstance(ADDON_PACKAGE, str)
    and ADDON_PACKAGE.isdigit())):
    ANKI_WEB_URL = f"https://ankiweb.net/shared/info/{ADDON_PACKAGE}"
    RATE_THIS_URL = f"https://ankiweb.net/shared/review/{ADDON_PACKAGE}"



PATREON_URL = "http://patreon.com/Shigeyuki"
REDDIT_URL = "https://www.reddit.com/r/Anki/comments/1b0eybn/simple_fix_of_broken_addons_for_the_latest_anki/"

POPUP_PNG = r"popup_shige.png"


#🟢
NEW_FEATURE = """
🔥Enhanced
[1] Zoom
    - Added + and - buttons to the global leaderboard.
    press to zoom in and out on the leaderboard.
    The default setting is 1.5x.
[2] Font
    - Added a gear button to the global leaderboard.
    Press to change the leaderboard font.
[3] Resize
    - Auto saves and reproduces the leaderboard size.

If distracting, you can disable by config.
Config -> Others tab -> Zoom and Font Enable

[4] Achievement
    - Enhanced Achievement for Streaks.

🐞Bug Fixed
[5] Fixed to auto select leagues.
"""

# [3] Note
#     [1] I have not yet tested all the features.
#         Feel free to contact me if you find any problems.

UPDATE_TEXT = "I updated this Add-on."
# UPDATE_TEXT = ""  #League



CHANGE_LOG_TEXT = """\
[ Change log : {addon} ]

Shigeyuki : Hello thank you for using this add-on! :-)
{update_text}
{new_feature}
When Anki gets a major update add-ons will be broken, so if you like this add-on please support my volunteer development (so far I fixed 50 add-ons and created 37 new ones) by donating on Patreon to get exclusive add-ons. Thanks!


[ Old change log ]
{old_change_log}

{special_thanks}

{patron}

""".format(addon=THE_ADDON_NAME,
            update_text=UPDATE_TEXT,
            new_feature=NEW_FEATURE,
            old_change_log = OLD_CHANGE_LOG,
            special_thanks=SPECIAL_THANKS,
            patron=PATRONS_LIST)



CHANGE_LOG_TEXT_B = """\
Shigeyuki :
Hello, thank you for using this add-on, I'm Shige!😆

I development of Anki Add-ons for Gamification Learning
and so far I fixed 40+ broken add-ons.
If you like this add-on, please support my development on Patreon,
and you can get add-ons for patrons only(about 28 Contents).

If you have any problems or requests feel free to contact me.
Thanks!

----
{addon}
[ Change log ]

{new_feature}

{old_change_log}

----
{special_thanks}

{patron}
""".format(addon=THE_ADDON_NAME,patron=PATRONS_LIST,special_thanks=SPECIAL_THANKS,
            new_feature=NEW_FEATURE, old_change_log=OLD_CHANGE_LOG, )




# ------- Change Log PopUp ---------------

def set_gui_hook_change_log():
    gui_hooks.main_window_did_init.append(change_log_popup)
    # gui_hooks.main_window_did_init.append(add_config_button) #🟢

# def change_log_popup(*args,**kwargs):
#     try:
#         config = mw.addonManager.getConfig(__name__)
#         # if (config[IS_RATE_THIS] == False and config[CHANGE_LOG] == False):
#         if (config.get(CHANGE_LOG, CHANGE_LOG_DEFAULT) != CHANGE_LOG_DAY):

#             dialog = CustomDialog(None,CHANGE_LOG_TEXT,size_mini=True)
#             if hasattr(dialog, 'exec'):result = dialog.exec() # Qt6
#             else:result = dialog.exec_() # Qt5

#             if result == QDialog.DialogCode.Accepted:
#                 openLink(PATREON_URL)
#                 toggle_rate_this()
#             elif  result == QDialog.DialogCode.Rejected:
#                 toggle_changelog()

#     except Exception as e:
#         print(e)
#         pass

def change_log_popup(*args,**kwargs):
    try:
        config = mw.addonManager.getConfig(__name__)
        if (config.get(CHANGE_LOG, CHANGE_LOG_DEFAULT) != CHANGE_LOG_DAY):
            dialog = CustomDialog(mw, CHANGE_LOG_TEXT, size_mini=True)
            dialog.finished.connect(lambda result: handle_dialog_result(result))
            dialog.show()
    except Exception as e:
        pass

def handle_dialog_result(result):
    if result == QDialog.DialogCode.Accepted:
        openLink(PATREON_URL)
        toggle_rate_this()
    elif result == QDialog.DialogCode.Rejected:
        toggle_changelog()


def change_log_popup_B(*args,**kwargs):
    try:
        dialog = CustomDialog(None,CHANGE_LOG_TEXT_B,True)
        if hasattr(dialog, 'exec'):result = dialog.exec() # Qt6
        else:result = dialog.exec_() # Qt5

        if result == QDialog.DialogCode.Accepted:
            openLink(PATREON_URL)
            toggle_rate_this()
        elif  result == QDialog.DialogCode.Rejected:
            toggle_changelog()
    except Exception as e:
        print(e)
        pass



# ----- add-onのconfigをｸﾘｯｸしたら設定ｳｨﾝﾄﾞｳを開く -----
def add_config_button():
    mw.addonManager.setConfigAction(__name__, change_log_popup_B)
    # ----- ﾒﾆｭｰﾊﾞｰに追加 -----
    action = QAction(THE_ADDON_NAME, mw)
    qconnect(action.triggered, change_log_popup_B)
    mw.form.menuTools.addAction(action)

# ================================================



class CustomDialog(QDialog):
    def __init__(self, parent=None,change_log_text=CHANGE_LOG_TEXT,more_button=False,size_mini=False):
        super().__init__(parent)

        addon_path = dirname(__file__)
        icon = QPixmap(join(addon_path, POPUP_PNG))
        layout = QVBoxLayout()
        if size_mini:
            self.resize(SIZE_MINI_WIDTH, SIZE_MINI_HEIGHT)
        else:
            self.resize(SIZE_BIG_WIDTH, SIZE_BIG_HEIGHT)

        pokeball_icon = QIcon(join(addon_path, POKEBALL_PATH))
        self.setWindowIcon(pokeball_icon)

        self.setWindowTitle(THE_ADDON_NAME)

        icon_label = QLabel()
        icon_label.setPixmap(icon)

        hbox = QHBoxLayout()

        change_log_label = QTextBrowser()
        change_log_label.setReadOnly(True)
        change_log_label.setOpenExternalLinks(True)

        change_log_label.setPlainText(change_log_text)

        hbox.addWidget(icon_label)
        hbox.addWidget(change_log_label)

        layout.addLayout(hbox)


        if more_button:
            button_layout = QVBoxLayout()
        else:
            button_layout = QHBoxLayout()

        self.yes_button = QPushButton("💖Patreon")
        self.yes_button.clicked.connect(self.accept)
        self.yes_button.setFixedWidth(120)


        if more_button:
            row1_layout = QHBoxLayout()
            row1_layout.addWidget(self.yes_button)
        else:
            button_layout.addWidget(self.yes_button)

        if more_button:
            self.rate_button = QPushButton("👍️RateThis")
            self.rate_button.clicked.connect(lambda : openLink(RATE_THIS_URL))
            self.rate_button.setFixedWidth(120)
            row1_layout.addWidget(self.rate_button)
            if RATE_THIS_URL == "":
                self.rate_button.setEnabled(False)

            self.ankiweb_button = QPushButton("🌟AnkiWeb")
            self.ankiweb_button.clicked.connect(lambda : openLink(ANKI_WEB_URL))
            self.ankiweb_button.setFixedWidth(120)
            row1_layout.addWidget(self.ankiweb_button)
            if ANKI_WEB_URL == "":
                self.ankiweb_button.setEnabled(False)

            button_layout.addLayout(row1_layout)

            row2_layout = QHBoxLayout()

            self.reddit_button = QPushButton("👨‍🚀Reddit")
            self.reddit_button.clicked.connect(lambda : openLink(REDDIT_URL))
            self.reddit_button.setFixedWidth(120)
            row2_layout.addWidget(self.reddit_button)

            self.github_button = QPushButton("🐈️Github")
            self.github_button.clicked.connect(lambda : openLink(GITHUB_URL))
            self.github_button.setFixedWidth(120)
            row2_layout.addWidget(self.github_button)

        self.no_button = QPushButton("OK (Close)")
        self.no_button.clicked.connect(self.reject)
        self.no_button.setFixedWidth(120)
        if more_button:
            row2_layout.addWidget(self.no_button)
            button_layout.addLayout(row2_layout)
        else:
            button_layout.addWidget(self.no_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def resizeEvent(self, event:"QResizeEvent"):
        size = event.size()
        print(f"Width: {size.width()}, Height: {size.height()}")
        super().resizeEvent(event)


def toggle_rate_this():
    # config = mw.addonManager.getConfig(__name__)
    # # config[IS_RATE_THIS] = True
    # config[CHANGE_LOG] = CHANGE_LOG_DAY
    # mw.addonManager.writeConfig(__name__, config)
    write_config(CHANGE_LOG, CHANGE_LOG_DAY)

def toggle_changelog():
    # config = mw.addonManager.getConfig(__name__)
    # config[CHANGE_LOG] = CHANGE_LOG_DAY
    # mw.addonManager.writeConfig(__name__, config)
    write_config(CHANGE_LOG, CHANGE_LOG_DAY)

# -----------------------------------




# class CustomDialog(QDialog):
#     def __init__(self, parent=None,change_log_text=CHANGE_LOG_TEXT,more_button=False,size_mini=False):
#         super().__init__(parent)

#         addon_path = dirname(__file__)
#         icon = QPixmap(join(addon_path, POPUP_PNG))
#         layout = QVBoxLayout()
#         if size_mini:
#             self.resize(SIZE_MINI_WIDTH, SIZE_MINI_HEIGHT)
#         else:
#             self.resize(SIZE_BIG_WIDTH, SIZE_BIG_HEIGHT)

#         pokeball_icon = QIcon(join(addon_path, POKEBALL_PATH))
#         self.setWindowIcon(pokeball_icon)

#         self.setWindowTitle(THE_ADDON_NAME)

#         icon_label = QLabel()
#         icon_label.setPixmap(icon)

#         hbox = QHBoxLayout()

#         change_log_label = QTextBrowser()
#         change_log_label.setReadOnly(True)
#         change_log_label.setOpenExternalLinks(True)

#         change_log_label.setPlainText(change_log_text)

#         hbox.addWidget(icon_label)
#         hbox.addWidget(change_log_label)

#         layout.addLayout(hbox)


#         if more_button:
#             button_layout = QVBoxLayout()
#         else:
#             button_layout = QHBoxLayout()

#         self.yes_button = QPushButton("💖Patreon")
#         self.yes_button.clicked.connect(self.accept)
#         self.yes_button.setFixedWidth(120)


#         if more_button:
#             row1_layout = QHBoxLayout()
#             row1_layout.addWidget(self.yes_button)
#         else:
#             button_layout.addWidget(self.yes_button)

#         if more_button:
#             self.rate_button = QPushButton("👍️RateThis")
#             self.rate_button.clicked.connect(lambda : openLink(RATE_THIS_URL))
#             self.rate_button.setFixedWidth(120)
#             row1_layout.addWidget(self.rate_button)
#             if RATE_THIS_URL == "":
#                 self.rate_button.setEnabled(False)

#             self.ankiweb_button = QPushButton("🌟AnkiWeb")
#             self.ankiweb_button.clicked.connect(lambda : openLink(ANKI_WEB_URL))
#             self.ankiweb_button.setFixedWidth(120)
#             row1_layout.addWidget(self.ankiweb_button)
#             if ANKI_WEB_URL == "":
#                 self.ankiweb_button.setEnabled(False)

#             button_layout.addLayout(row1_layout)

#             row2_layout = QHBoxLayout()

#             self.reddit_button = QPushButton("👨‍🚀Reddit")
#             self.reddit_button.clicked.connect(lambda : openLink(REDDIT_URL))
#             self.reddit_button.setFixedWidth(120)
#             row2_layout.addWidget(self.reddit_button)

#             self.github_button = QPushButton("🐈️Github")
#             self.github_button.clicked.connect(lambda : openLink(GITHUB_URL))
#             self.github_button.setFixedWidth(120)
#             row2_layout.addWidget(self.github_button)

#         self.no_button = QPushButton("OK (Close)")
#         self.no_button.clicked.connect(self.reject)
#         self.no_button.setFixedWidth(120)
#         if more_button:
#             row2_layout.addWidget(self.no_button)
#             button_layout.addLayout(row2_layout)
#         else:
#             button_layout.addWidget(self.no_button)

#         layout.addLayout(button_layout)
#         self.setLayout(layout)

#         layout.addLayout(button_layout)
#         self.setLayout(layout)

#     def resizeEvent(self, event:"QResizeEvent"):
#         size = event.size()
#         print(f"Width: {size.width()}, Height: {size.height()}")
#         super().resizeEvent(event)