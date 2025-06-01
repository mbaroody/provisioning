
from aqt import gui_hooks


def addButtons(handled, message, context):
    from .. import get_startup_shige_leaderboard
    if message == "shige_leaderboard":
        get_startup_shige_leaderboard().leaderboard()
        return (True, None)

    elif message == "shige_leaderboard_sync_and_update":
        get_startup_shige_leaderboard().startBackgroundSync()
        return (True, None)

    elif message == "shige_leaderboard_config":
        get_startup_shige_leaderboard().invokeSetup()
        return (True, None)

    else:
        return handled

def set_gui_hooks_leaderboard():
    gui_hooks.webview_did_receive_js_message.remove(addButtons)
    gui_hooks.webview_did_receive_js_message.append(addButtons)