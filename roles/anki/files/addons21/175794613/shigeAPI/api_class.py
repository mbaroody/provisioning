
from aqt import mw

class ShigeAPI():
    def __init__(self, new_attr_name:str):
        self.attr_name = "shigeAPI_" + new_attr_name

    def run(self):
        try:
            if hasattr(mw, self.attr_name):
                mw_addon_func = getattr(mw, self.attr_name)
                if callable(mw_addon_func):
                    mw_addon_func()
        except Exception as e:
            print(f"shigeAPI {self.attr_name} Error: {e}")

    def add(self, func):
        setattr(mw, self.attr_name, func)
