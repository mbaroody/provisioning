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

import datetime
from datetime import date, timedelta
import json
import os

try:
    from aqt import gui_hooks
except:
    pass
from aqt.deckbrowser import DeckBrowser
from aqt import mw
# from aqt.deckbrowser import DeckBrowser
from anki.hooks import wrap

from .userInfo import start_user_info
from .config_manager import write_config

data = None


def getData():
    config = mw.addonManager.getConfig(__name__)
    medal_users = config["medal_users"]
    if config["tab"] != 4:
        new_day = datetime.time(int(config['newday']),0,0)
        time_now = datetime.datetime.now().time()
        if time_now < new_day:
            start_day = datetime.datetime.combine(date.today() - timedelta(days=1), new_day)
        else:
            start_day = datetime.datetime.combine(date.today(), new_day)

        lb_list = []
        counter = 0
        for i in data[0]:
            username = i[0]
            streak = i[1]
            cards = i[2]
            time = i[3]
            sync_date = i[4]
            sync_date = datetime.datetime.strptime(sync_date, '%Y-%m-%d %H:%M:%S.%f')
            month = i[5]
            country = i[7]
            retention = i[8]
            groups = []
            if i[6]:
                groups.append(i[6].replace(" ", ""))
            if i[9]:
                for group in json.loads(i[9]):
                    groups.append(group)
            groups = [x.replace(" ", "") for x in groups]

            if config["show_medals"] == True:
                for i in medal_users:
                    if username in i:
                        username = f"{username} |"
                        if i[1] > 0:
                            username = f"{username} {i[1] if i[1] != 1 else ''}🥇"
                        if i[2] > 0:
                            username = f"{username} {i[2] if i[2] != 1 else ''}🥈"
                        if i[3] > 0:
                            username = f"{username} {i[3] if i[3] != 1 else ''}🥉"

            if sync_date > start_day and username not in config["hidden_users"]:
                if config["tab"] == 0:
                    counter += 1
                    lb_list.append([counter, username, cards, time, streak, month, retention])
                if config["tab"] == 1 and username in config["friends"]:
                    counter += 1
                    lb_list.append([counter, username, cards, time, streak, month, retention])
                if config["tab"] == 2 and country == config["country"].replace(" ", ""):
                    counter += 1
                    lb_list.append([counter, username, cards, time, streak, month, retention])
                if config["tab"] == 3 and config["current_group"] is not None and config["current_group"].replace(" ", "") in groups:
                    counter += 1
                    lb_list.append([counter, username, cards, time, streak, month, retention])

    if config["tab"] == 4:
        for i in data[1]:
            if config["username"] in i:
                user_league_name = i[5]

        counter = 0
        lb_list = []
        for i in data[1]:
            username = i[0]
            xp = i[1]
            reviews = i[2]
            time_spend = i[3]
            retention = i[4]
            league_name = i[5]
            days_learned = i[7]

            for i in medal_users:
                if username in i:
                    username = f"{username} |"
                    if i[1] > 0:
                        username = f"{username} {i[1] if i[1] != 1 else ''}🥇"
                    if i[2] > 0:
                        username = f"{username} {i[2] if i[2] != 1 else ''}🥈"
                    if i[3] > 0:
                        username = f"{username} {i[3] if i[3] != 1 else ''}🥉"

            if league_name == user_league_name and xp != 0:
                counter += 1
                # lb_list.append([counter, username, xp, reviews, time_spend, retention, days_learned])
                if username not in config["hidden_users"]:
                    lb_list.append([counter, username, xp, reviews, time_spend, retention, days_learned])

    write_config("homescreen_data", lb_list)
    return lb_list

def on_deck_browser_will_render_content(overview, content):
    # Rearrange home addonsの互換性を追加 ---------------------
    if data == None:
        return
    config = mw.addonManager.getConfig(__name__)
    if config["homescreen"] == False:
        return
    # ----------------------------

    if config["homescreen_data"]:
        lb = config["homescreen_data"]
    else:
        lb = getData()

    from .colors_config import get_color_config
    colors = get_color_config()

    result = []

    lb_length = len(lb)
    if config["maxUsers"] > lb_length:
        config["maxUsers"] = lb_length
    if config["focus_on_user"] == True and len(lb) > config["maxUsers"]:
        for i in lb:
            if config["username"] == i[1].split(" |")[0]:
                user_index = lb.index(i)

                half_max_users = config["maxUsers"] // 2
                extra = 1 if config["maxUsers"] % 2 != 0 else 0

                if user_index + half_max_users + extra > lb_length:
                    for i in range((user_index - config["maxUsers"] + 1), user_index + 1):
                        if 0 <= i < lb_length:
                            result.append(lb[i])
                    break
                if user_index - half_max_users < 0:
                    for i in range(user_index, (user_index + config["maxUsers"])):
                        if 0 <= i < lb_length:
                            result.append(lb[i])
                    break
                else:
                    for i in range((user_index - half_max_users), (user_index + half_max_users + extra)):
                        if 0 <= i < lb_length:
                            result.append(lb[i])
                    break

        if not result:
            result = lb[:config["maxUsers"]]

        table_style = """
        <style>
            table.lb_table {
                font-family: arial, sans-serif;
                border-collapse: collapse;
                width: 35%;
                margin-left:auto;
                margin-right:auto;
                font-weight: bold;
            }

            table.lb_table td{
                white-space: nowrap;  /** added **/
            }

            table.lb_table td, th {
                text-align: left;
                padding: 8px;
            }
        </style>
        """
    else:

        result = lb[:config["maxUsers"]]

        gold_color = colors["GOLD_COLOR"]
        silver_color = colors["SILVER_COLOR"]
        bronze_color = colors["BRONZE_COLOR"]

        table_style = """
        <style>
        table.lb_table {{
            font-family: arial, sans-serif;
            border-collapse: collapse;
            width: 35%;
            margin-left:auto;
            margin-right:auto;
            font-weight: bold;
        }}

        table.lb_table td{{
            white-space: nowrap;  /** added **/
        }}

        table.lb_table td, th {{
            text-align: left;
            padding: 8px;
        }}

        table.lb_table tr:nth-child(2) {{
            background-color: {gold_color};
        }}

        table.lb_table tr:nth-child(3) {{
            background-color: {silver_color};
        }}

        table.lb_table tr:nth-child(4) {{
            background-color: {bronze_color};
        }}
        </style>
        """.format(gold_color=gold_color,
                    silver_color=silver_color,
                    bronze_color=bronze_color)


    # try:
    #     from aqt.theme import theme_manager
    #     nightmode = theme_manager.night_mode
    # except:
    #     nightmode = False

    # with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "colors.json"), "r") as colors_file:
    #     color_data = colors_file.read()
    #     colors_themes = json.loads(color_data)
    #     colors = colors_themes["dark"] if nightmode else colors_themes["light"]


    if config["tab"] != 4:
        table_header = """

        <table class="lb_table">
            <tr>
                <th>#</th>
                <th>Username</th>
                <th style="text-align:right">Reviews</th>
                <th style="text-align:right">Minutes</th>
                <th style="text-align:right">Streak</th>
                <th style="text-align:right">Past 31 days</th>
                <th style="text-align:right">Retention</th>
            </tr>
        """
        table_content = ""

        for i in result:

            if i[1].split(" |")[0] == config["username"]:
                color = colors["USER_COLOR"]
            elif i[1].split(" |")[0] in config["friends"] and not config["tab"] == 1:
                color = colors["FRIEND_COLOR"]
            else:
                color = ""

            table_content = table_content + f"""
            <tr style="background-color:{color}">
                <td>{i[0]}</td>
                <td><button style="outline:0 !important; cursor:pointer; border: none; background: none;" type="button" onclick="pycmd('userinfo:{i[1]}')"><b>{i[1]}</b></button></td>
                <td style="text-align:right">{i[2]}</td>
                <td style="text-align:right">{i[3]}</td>
                <td style="text-align:right">{i[4]}</td>
                <td style="text-align:right">{i[5]}</td>
                <td style="text-align:right">{i[6]}%</td>
            </tr>
            """
    if config["tab"] == 4:
        table_header = """

        <table class="lb_table">
            <tr>
                <th>#</th>
                <th>Username</th>
                <th style="text-align:right">XP</th>
                <th style="text-align:right">Minutes</th>
                <th style="text-align:right">Reviews</th>
                <th style="text-align:right">Retention</th>
                <th style="text-align:right">Days learned</th>
            </tr>
        """
        table_content = ""

        for i in result:

            if i[1].split(" |")[0] == config["username"]:
                color = colors["USER_COLOR"]
            elif i[1].split(" |")[0] in config["friends"]:
                color = colors["FRIEND_COLOR"]
            else:
                color = ""


            table_content = table_content + f"""
            <tr style="background-color:{color}">
                <td>{i[0]}</td>
                <td><button style="outline:0 !important; cursor:pointer; border: none; background: none;" type="button" onclick="pycmd('userinfo:{i[1]}')"><b>{i[1]}</b></button></td>
                <td style="text-align:right">{i[2]}</td>
                <td style="text-align:right">{i[3]}</td>
                <td style="text-align:right">{i[4]}</td>
                <td style="text-align:right">{i[5]}%</td>
                <td style="text-align:right">{i[6]}%</td>
            </tr>
            """

    shige_text = ""
    if config.get("show_home_buttons", True):

        rate_and_donation = ""
        if config.get("rate_and_donation_buttons", True):
            rate_and_donation ="""
            <a href="https://ankiweb.net/shared/review/175794613">👍️Rate</a> |
            <a href="http://patreon.com/Shigeyuki">💖Donate</a> |
            """

        shige_text = f"""<br><div>
        <a style="cursor: pointer;" onclick="pycmd(\'shige_leaderboard\')">🏆️Anki-Leaderboard</a> |
        <a style="cursor: pointer;" onclick="pycmd(\'shige_leaderboard_sync_and_update\')">🌐Sync</a> |
        <a style="cursor: pointer;" onclick="pycmd(\'shige_leaderboard_config\')">⚙️Config</a> |
        <a href="https://shigeyukey.github.io/shige-addons-wiki/anki-leaderboard.html">📖Wiki</a> |
        {rate_and_donation}
        </div>
        """

    # <a href="https://www.reddit.com/submit?url=https://ankiweb.net/shared/info/175794613&title=Anki%20Leaderboard" target="_blank">Share</a>



    content.stats += table_style + shige_text + table_header + table_content + "</table>"

def leaderboard_on_deck_browser(response):
    global data
    data = response
    # Rearrange home addonsの互換性を追加 
    # config = mw.addonManager.getConfig(__name__)
    # gui_hooks.deck_browser_will_render_content.remove(on_deck_browser_will_render_content)
    # if config["homescreen"] == True:
    #     gui_hooks.deck_browser_will_render_content.append(on_deck_browser_will_render_content)
    if mw.state == "deckBrowser":
        mw.deckBrowser.refresh()
    # DB = DeckBrowser(mw)
    # DB.refresh()

    # from aqt.utils import tooltip
    # tooltip("DB.refresh()")

def deckbrowser_linkHandler_wrapper(overview, url):
    url = url.split(":")
    if url[0] == "userinfo":
        mw.shige_user_info = start_user_info(url[1], False)
        mw.shige_user_info.show()
        mw.shige_user_info.raise_()
        mw.shige_user_info.activateWindow()

DeckBrowser._linkHandler = wrap(DeckBrowser._linkHandler, deckbrowser_linkHandler_wrapper, "after")