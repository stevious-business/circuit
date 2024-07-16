from time import perf_counter

from functools import wraps

from locals import *

_launch_time = perf_counter()

_log_indents = 0
_log_file = None

"""
class Timer:
    def __init__(self):
        self._timer = perf_counter()

    def reset(self):
        self._timer = perf_counter()

    def time_since_launch(self):
        return perf_counter() - self._timer


def sfmt(str_: str, len_: int, ws=False):
    strlen = len(str_)
    remain = len_ - strlen
    return str_ + remain * (" " if ws else ".")
"""

def _ts() -> str:
    global _launch_time
    time_float = perf_counter()-_launch_time
    time_secs = int(time_float)
    time_offset = round(time_float - time_secs, 4)
    return f"{str(time_secs).zfill(5)}.\
{str(time_offset).ljust(6, '0').removeprefix('0.')}"


def log_indent():
    global _log_indents
    _log_indents += LOG_SPACING


def log_dedent():
    global _log_indents
    _log_indents -= LOG_SPACING


def setup_logger():
    global _log_file
    _log_file = open("program.log", "w", encoding="utf-8")


def exit_logger():
    global _log_file
    _log_file.flush()
    _log_file.close()


def log(level, text, nts=False, use_indent=True, **kwargs):
    # TODO: clean up this function ffs
    global _log_file
    if level >= DBG.get():
        level_colors = {
            LOG_BASE: "\033[90m",
            LOG_VERB: "\033[35m",
            LOG_DEBG: "\033[2;33m",
            LOG_INFO: "\033[0m",
            LOG_WARN: "\033[1;33m",
            LOG_FAIL: "\033[41m"
        }
        level_texts = {
            LOG_BASE: "BASE",
            LOG_VERB: "VERB",
            LOG_DEBG: "DEBG",
            LOG_INFO: "INFO",
            LOG_WARN: "WARN",
            LOG_FAIL: "FAIL"
        }
        if nts:     # No time stamp (no prefix)
            print(f"{level_colors[level]}{text}\033[0m", **kwargs)
            return
        t = _ts()
        print_indent_count = _log_indents*use_indent
        pre = f"\r\033[0m[\033[36m{SW_NAME}\033[0m::" \
            + f"\033[32m{t}\033[0m::" \
            + f"{level_colors[level]+level_texts[level]}\033[0m]"
        final_text = f"{pre} {' '*print_indent_count} \
{level_colors[level]}{text}\033[0m"
        uncolored_pref = f"[{SW_NAME}::{t}::{level_texts[level]}]"
        uncolored_text = f"{uncolored_pref}{' '*print_indent_count}{text}"
        if DBG.cr_on_log:
            final_text = "\r" + final_text
        print(final_text, **kwargs)
        if DBG.cr_on_log:
            print(TERMINAL_PROMPT, end="")
        _log_file.write(uncolored_text+"\n")


def logAutoIndent(function):

    @wraps(function)
    def inner(*args, **kwargs):
        log_indent()
        try:
            r = function(*args, **kwargs)
        except Exception as e:
            log_dedent()
            raise e
        else:
            log_dedent()
            return r
    return inner


#timer = Timer()
