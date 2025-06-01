# Add-on for Anki
#
# License: AGPLv3 (license of the original release, see
#     https://web.archive.org/web/20200225134227/https://ankiweb.net/shared/info/1639597619
#
# This is a modification of Arthur's modification khonkhortisan's
# port of Arthaey "Rebuild All & Empty All" which was originally released at
# https://ankiweb.net/shared/info/1639597619
#
# Contributors:
# - Arthaey Angosii, https://github.com/Arthaey
# - ankitest
# - ArthurMilchior
# - ijgnd

import time

from anki.cards import Card
from anki.hooks import wrap

from aqt import mw
from aqt.deckbrowser import DeckBrowser
from aqt.gui_hooks import (
    deck_browser_will_show_options_menu,
    profile_did_open,
)
from aqt.utils import tooltip

from .helpers import anki_point_version, gc



def rebuilt_nested_first(dynDeckIds, actionFunc):
    nestedlevels = {}
    for id in dynDeckIds:
        deck = mw.col.decks.get(id)
        n = deck['name'].count("::")
        nestedlevels.setdefault(n, []).append(id)
    #for level in sorted(nestedlevels, key=nestedlevels.get, reverse=False):
    for level in sorted(nestedlevels.keys(), reverse=True):
        for e in nestedlevels[level]:
            actionFunc(e)


def this_name_excluded_by_config(deck_name):
    only_these = [] 
    for e in gc("build only these partial matches - this overrides all other settings", []):
        if isinstance(e, str) and len(e.strip()) > 1:
            only_these.append(e)
    if only_these:
        for partial in only_these:
            if partial in deck_name:
                return False
        return True
    else:
        for name in gc("build exclude - exact match", []):
            if name.strip():  # avoid empty like " "
                if name == deck_name:
                    return True
        for partial in gc("build exclude - partial match", []):
            if partial.strip():  # avoid empty like " "
                if partial in deck_name:
                    return True
        return False


def _updateFilteredDecks(actionFuncName):
    relevant_dyn_deck_ids_and_names = {}
    for d in mw.col.decks.all():
        if d["dyn"]:
            if not this_name_excluded_by_config(d["name"]):
                relevant_dyn_deck_ids_and_names[d["id"]] = d["name"]
    dyn_deck_ids = sorted(relevant_dyn_deck_ids_and_names.keys())
    count = len(dyn_deck_ids)
    if not count:
        tooltip("No filtered decks found.")
        return
    # should be one of "rebuildDyn" or "emptyDyn"
    actionFunc = getattr(mw.col.sched, actionFuncName)
    mw.checkpoint("{0} {1} filtered decks".format(actionFuncName, count))
    mw.progress.start()
    if actionFuncName == "emptyDyn":
        # [actionFunc(did) for did in sorted(dynDeckIds)]
        for did in dyn_deck_ids:
            actionFunc(did)
    else:
        build_first = gc("build first (exact match)")
        if build_first and isinstance(build_first, list):
            for dname in build_first:
                deck = mw.col.decks.byName(dname) if anki_point_version <= 44 else mw.col.decks.by_name(dname)
                if deck and deck["id"] in dyn_deck_ids:
                    actionFunc(deck["id"])
                    dyn_deck_ids.remove(deck["id"])
        build_last = gc("build last (exact match)")
        if build_last and isinstance(build_last, list):
            for dname in build_last:
                deck = mw.col.decks.byName(dname) if anki_point_version <= 44 else mw.col.decks.by_name(dname)
                if deck and deck["id"] in dyn_deck_ids:
                    dyn_deck_ids.remove(deck["id"])
                else:
                    build_last.remove(dname)
        if gc("build - prioritize most nested subdecks"):
            rebuilt_nested_first(dyn_deck_ids, actionFunc)    
        else:
            [actionFunc(did) for did in sorted(dyn_deck_ids)]
        if build_last:
            for dname in build_last:
                deck = mw.col.decks.byName(dname)
                actionFunc(deck['id'])
    mw.progress.finish()
    tooltip("Updated {0} filtered decks.".format(count))
    mw.reset()


def _handleFilteredDeckButtons(self, url):
    if url in ["rebuildDyn", "emptyDyn"]:
        _updateFilteredDecks(url)


def _addButtons(self):
    # TODO rebuildDyn and emptyDyn are old: see scheduler/legacy.py
    # check if the new methods just have a new name or more
    
    # in 2023-03 adding a shortcut into the first place in the nested list drawLinks doesn't work
    # I'm not motivated to investigate because the main screen will be rewritten soon.
    drawLinks = [
        ["", "rebuildDyn", "Rebuild All"],
        ["", "emptyDyn", "Empty All"]
    ]
    # don't duplicate buttons every click
    if drawLinks[0] not in self.drawLinks:
        self.drawLinks += drawLinks

DeckBrowser._drawButtons = wrap(DeckBrowser._drawButtons, _addButtons, "before")
DeckBrowser._linkHandler = wrap(DeckBrowser._linkHandler, _handleFilteredDeckButtons, "after")



def on_show_options(menu, deck_id) -> None:
    if not gc("add empty,rebuild to each cog icon menu behind deck name"):
        return
    deck_id = int(deck_id)
    d = mw.col.decks.get(deck_id)
    if d["dyn"]:
        action = menu.addAction("Empty")
        action.triggered.connect(lambda _, did=deck_id: deckbrowser_empty_and_refresh(did))
        action = menu.addAction("Rebuild")
        action.triggered.connect(lambda _, did=deck_id: deckbrowser_rebuild_and_refresh(did))

# this hook is available since at least 2.1.20, see
# https://github.com/ankitects/anki/commit/b09e7e8247cd1b9e5214fab67f77876919ff483f
# note this change for 2.1.28
# https://github.com/ankitects/anki/commit/6144317736ff6f22a2fac0ab217e67ad148fa5e1
deck_browser_will_show_options_menu.append(on_show_options)


def deckbrowser_empty_and_refresh(did):
    mw.col.sched.emptyDyn(did)
    # up to 2.1.49 that scrolls the webview back to the top, in 2.1.50 up to 2.1.63 (latest current version)
    # the vertical scroll position is kept in my anki version.
    mw.deckBrowser.refresh()

def deckbrowser_rebuild_and_refresh(did):
    mw.col.sched.rebuildDyn(did)
    mw.deckBrowser.refresh()

# config.md: - `auto rebuild interval`: the number of seconds between two recomputation of the filters. Or null if it's not activated.
# config.json: "auto rebuild interval": null,
# ankiweb.html: This version also includes Arthur's <a href="https://github.com/Arthur-Milchior/anki-rebuild-all/commits/delta" rel="nofollow">recent addition</a> to rebuild periodically automatically rebuilt the filtered decks.
lastReview = None
def postSched(self):
    global lastReview
    delta = gc("auto rebuild interval")
    if delta and (lastReview is None or time.time() > lastReview + delta):
        print("....auto rebuilding filtered decks")
        _updateFilteredDecks("rebuildDyn")
        lastReview = time.time()
if anki_point_version < 45:
    Card.flushSched = wrap(Card.flushSched, postSched)
    Card.sched = wrap(Card.flush, postSched)
