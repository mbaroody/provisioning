
# https://github.com/shigeyukey/shigeAPI

from .api_class import ShigeAPI

# 🟢Lastupdate: 2025-03-25

### How to use ###

# set
# from .shigeAPI import shigeAPI
# shigeAPI.my_addon_name.add(my_addon_func)

# use
# from .shigeAPI import shigeAPI
# config = mw.addonManager.getConfig(__name__)
# if config.get("run_my_addon", True):
#     shigeAPI.my_addon_name.run()


### AnkiRestart ###
# https://ankiweb.net/shared/info/237169833
# Restart Anki now.
restart_anki = ShigeAPI("restart_anki")

### BreakTimer ###
# https://ankiweb.net/shared/info/174058935
# Start the break timer now.
start_break_timer = ShigeAPI("start_break_timer")

### Leaserboard ###
# https://ankiweb.net/shared/info/175794613
# Open the Leaderboard window.
open_leaderboard = ShigeAPI("open_leaderboard")

