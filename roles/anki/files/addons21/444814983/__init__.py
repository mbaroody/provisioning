from aqt import mw
from aqt.browser import Browser
from aqt.qt import QAction
from aqt.utils import getText, showWarning, qconnect

def show_dialog():
    qid_list, ok = getText(prompt = "Paste UWorld question IDs:")
    
    if ok:
        valid_input = check_integrity(qid_list)
        
        if valid_input:
            final_list = [int(x.strip()) for x in qid_list.split(",")]
            search(final_list)
        else:
            showWarning("Invalid input")

def check_integrity(ids):
    processed = ids.split(",")

    for qid in processed:
        if not qid.strip().isdigit():
            return False

    return True

def search(ids):
    query = create_query(ids)
    browser = Browser(mw)
    browser.form.searchEdit.lineEdit().setText(query)
    browser.onSearchActivated()

def create_query(ids):
    query = " OR ".join(f"tag:*UWorld*::{tag}" for tag in ids)
    return query

action = QAction("Find cards from UWorld test", mw)
qconnect(action.triggered, show_dialog)
mw.form.menuTools.addAction(action)
