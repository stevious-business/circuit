LOG_BASE = 0    # dump everything
LOG_VERB = 1    # realistically everything that should be known
LOG_DEBG = 2    # general structure and program trace
LOG_INFO = 3    # user-level output
LOG_WARN = 4    # important mishaps
LOG_FAIL = 5    # absolute failure
LOG_SILENT_MODE = 6     # For setting floor
LOG_SPACING = 4

SW_NAME = "LCST"
SW_NAME_LONG = "Large Circuit Simulation Tool"
SW_VERSION = (1, 0)
SW_VER_STRING = ".".join([str(k) for k in SW_VERSION])
SW_UPDATE_DATE = "29 Mar 2024"
SW_COPYRIGHT_STRING = "© David Schroeder 2024. All rights reserved."
SW_CONTACT_STRING = "Email me: david@tobiasschroeder.de"
SW_SIGN_STRING = f"{SW_NAME_LONG} v{SW_VER_STRING} ({SW_UPDATE_DATE})." \
                 + f" {SW_COPYRIGHT_STRING}\n{SW_CONTACT_STRING}"
SW_HELP_STRING = f"""
Displaying help for '{SW_NAME_LONG}'
Usage: python main.py [MODE] [OPTIONS]

Options for MODE:
- 'help' / '--help':    Print this help and exit.

{SW_SIGN_STRING}
"""

TERMINAL_PROMPT = f"\033[36m{SW_NAME}\033[0m >>> "


class DebugOptions:
    FLOOR = 0


class DBGLVL:
    def __init__(self, lvl):
        self.lvl = lvl
        self.floor = 0
        self.silent = False
        self.cr_on_log = False
    
    def set_cr_on_log(self, state=True):
        self.cr_on_log = state

    def set(self, lvl):
        if lvl >= self.floor:
            self.lvl = lvl

    def set_silent(self, is_silent):
        self.silent = is_silent

    def set_floor(self, lvl):
        self.floor = lvl
        if self.lvl < lvl:
            self.lvl = lvl

    def get(self):
        return LOG_SILENT_MODE if self.silent else self.lvl


DBG = DBGLVL(LOG_DEBG)
