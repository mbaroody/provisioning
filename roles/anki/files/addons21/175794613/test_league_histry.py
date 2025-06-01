



import json
from aqt import QCursor, QHeaderView, QTableWidgetItem, Qt
from os.path import dirname, join

from .check_user_rank import compute_user_rank
from .custom_shige.country_dict import COUNTRY_FLAGS
from .create_icon import create_leaderboard_icon

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from  .Leaderboard import start_main

LEAGUE_NAMES = ["Delta", "Gamma", "Beta", "Alpha" ]


def get_history(self:"start_main"):

    for item in self.response[1]:
        username = item[0]
        league_name = item[5]
        xp = item[1]

        if xp != 0:

            {"gold": 0,
            "silver": 0,
            "bronze": 0,
            "results":{
                "leagues": ["Delta", "Delta", "Gamma", "Gamma", "Gamma"],
                "seasons": [1, 2, 3, 4, 5],
                "xp": [139909, 2541037, 1691500, 1374747, 511386],
                "rank": [175, 21, 31, 71, 180]
                }
            }

            history = json.loads(item[6])

            history_league = history.get("results", {}).get("leagues", [None])[-1]
            history_season = history.get("results", {}).get("seasons", [None])[-1]
            history_xp = history.get("results", {}).get("xp", [None])[-1]
            history_rank = history.get("results", {}).get("rank", [None])[-1]

            username
            history_season
            history_league
            history_rank
            history_xp


            