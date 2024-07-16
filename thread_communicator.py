from enum import Enum, auto
import threading

from circuitlogger import *


class Executable:
    def __init__(self, fn, args=(), kwargs={}):
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def update(self, args=None, kwargs=None):
        if args is not None:
            self.args = args
        if kwargs is not None:
            self.kwargs = kwargs

    def run(self, *args, **kwargs):
        self.fn(*(args or self.args), **(kwargs or self.kwargs))


class DirectiveType(Enum):
    QUIT = auto()


class Directive:
    def __init__(self, dt: DirectiveType, *args, **kwargs):
        self.dt = dt
        self.args = args
        self.kwargs = kwargs


class ThreadCommunicator:
    def __init__(self):
        self.activeThreadList = {}
        self.directives: dict[str: list[Directive]] = {}

    def add_directive(self, targets, d: Directive):
        for target in targets:
            if target not in self.activeThreadList.keys():
                log(LOG_WARN, f"Invalid directive target [{target}]!")
                continue
            self.directives[target] = self.directives.get(target, []) + [d]

    def directives_for(self, target):
        return self.directives[target]

    def rm_directive(self, target, dir):
        for directive in self.directives[target]:
            if directive is dir:
                del directive

    def registerThread(self, name, thread):
        self.activeThreadList[name] = thread

    def removeThread(self, name):
        del self.activeThreadList[name]

    def getThreadNames(self):
        return self.activeThreadList.keys()

    def newThread(self, name, *args, daemon=True, **kwargs):
        t = threading.Thread(None, *args, name=name, daemon=daemon, **kwargs)
        self.registerThread(name, t)

    def startThreads(self):
        for threadName in self.activeThreadList:
            t: threading.Thread = self.activeThreadList[threadName]
            if not t.ident:  # t.ident will be None if it hasn't been started
                t.start()
