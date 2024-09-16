from thread_communicator import ServerData, DirectiveType
from circuitlogger import *
from locals import *


def launchServer(name: str = "", threadCommunicator: ServerData = None):
    quits = False
    while True:
        for directive in threadCommunicator.directives_for(name):
            if directive.dt is DirectiveType.QUIT:
                quits = True # Pack up and gracefully exit
            threadCommunicator.rm_directive(name, directive)
        if quits:
            return
