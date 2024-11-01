from locals import *
from circuitlogger import *
from thread_communicator import ServerData, Directive, DirectiveType
from .project import Project
from circuit.base_classes import Package, Component

from json import loads, JSONDecodeError


CONSOLE_HELP = f"""\033[1A
Console help for {SW_NAME_LONG} {SW_VER_STRING}
Valid commands:
%s

Type 'help <command>' for more info on any command."""


class InvalidCommandException(SyntaxError): pass


class CCP:
    # Console command processor, not chinese communist party
    def __init__(self, tc: ServerData):
        self.threadCommunicator = tc
        self.history = []
        self.should_close = False
        self.previous_result = None
        try:
            self.command_help_data = loads(open("circuit/backend/command_help.json").read())
        except JSONDecodeError:
            log(LOG_FAIL, f"Malformed json in console manual file!")
            self.command_help_data = {}
        except FileNotFoundError:
            log(LOG_FAIL, f"Console manual file could not be located!")
            self.command_help_data = {}


    def help(self, *args):
        if len(args) is 0:
            self.print_valid_commands()
        else:
            if not self.command_help_data:
                log(LOG_FAIL, f"Manual could not be loaded!")
                return
            command_manual = self.command_help_data["manual"]
            try:
                for next_arg in args:
                    command_manual = command_manual[next_arg]
                    if next_arg is not args[-1]:
                        command_manual = command_manual["subcommands"]
                fmt = command_manual["format"]
                description = command_manual.get("description", "")
                print(f"Printing help for '{' '.join(args)}'")
                print(f"Usage: {fmt}")
                if description:
                    print(description)
            except KeyError:
                log(LOG_FAIL, f"Command '{' '.join(args)}' isn't valid!")
                self.print_valid_commands()

    def exit(self, *args):
        self.threadCommunicator.add_directive(None, Directive(DirectiveType.QUIT))
        DBG.set_cr_on_log(False)
        self.should_close = True

    def quit(self, *args):
        self.exit(*args)

    @logAutoIndent
    def execute(self, path, *args):
        try:
            DBG.set_cr_on_log(False)
            with open(path) as file:
                for line in file.readlines():
                    line = line.removesuffix("\n")
                    if not line:
                        continue
                    self.process_command(line, help_on_fail=False)
        except FileNotFoundError:
            log(LOG_FAIL, f"Execute file '{path}' could not be opened!")
        finally:
            DBG.set_cr_on_log()

    def saveall(self, path, *args):
        self.threadCommunicator.openProject.save(path)
        log(LOG_VERB, f"Saving all to {path}...")

    def project(self, *args):
        self.help("project")

    def project_new(self, name, *args):
        openProject = Project(name)
        self.threadCommunicator.openProject = openProject

    def project_open(self, path, *args):
        openProject = Project.load(path, self.threadCommunicator.package_datas)
        self.threadCommunicator.openProject = openProject

    def project_meta(self, *args):
        self.help("project", "meta")

    def project_meta_set(self, attr, *value):
        self.threadCommunicator.openProject.set_meta(attr, *value)
        return

    def project_include(self, pack, *chips):
        if (packdata := self.threadCommunicator.package_datas.get(pack, None)) is None:
            raise InvalidCommandException(f"Package {pack} could not be located!")
        package: Package = packdata.PACKAGE
        proj_includes = self.threadCommunicator.openProject.config["required-packages"]
        already_included_chips = proj_includes.get(pack, [])
        for chip in chips:
            if chip in already_included_chips:
                continue
            if chip not in package.get_ambiguous_component_names():
                raise InvalidCommandException(f"Chip {chip} does not exist within {pack}")
            mangled_cname = package.mangled_name(chip)
            chip_class = package[mangled_cname]
            self.threadCommunicator.openProject.included_components[mangled_cname] = chip_class # TODO: move to project method
            already_included_chips.append(chip)
        self.threadCommunicator.openProject.config["required-packages"][pack] = already_included_chips

    def project_setroot(self, cname, *args):
        self.threadCommunicator.openProject.set_root_id(cname)

    def component_add(self, name, *args):
        self.threadCommunicator.openProject.new_component(name, args[0] if args else None)

    def component_select(self, name, *args):
        if self.threadCommunicator.openProject.componentExists(name):
            self.threadCommunicator.selectedComponent = name
        else:
            raise KeyError(f"Component {name} does not exist!")

    def chip_place(self, cname, x, y, *args):
        scn = self.threadCommunicator.selectedComponent
        sc: Component = self.threadCommunicator.openProject.getComponent(
            scn, self.threadCommunicator.package_datas
        )
        c: Component = self.threadCommunicator.openProject.getComponent(
            cname, self.threadCommunicator.package_datas
        )
        sc.add_chip(c, x, y)

    def pin_place(self, x, y, *args):
        return

    def pin_label(self, id_, label, *args):
        return

    def pin_io(self, *args):
        self.help("pin", "io")

    def pin_io_set(self, id_, *args):
        return

    def wire_new(self, from_, to, *args):
        return

    def wire_connect(self, from_, to, *args):
        return


    def debug(self, lvl: str):
        if lvl.lower() in ("base", "b"):
            DBG.set(LOG_BASE)
        elif lvl.lower() in ("verbose", "verb", "v"):
            DBG.set(LOG_VERB)
        elif lvl.lower() in ("debug", "debg", "d"):
            DBG.set(LOG_DEBG)
        elif lvl.lower() in ("info", "i"):
            DBG.set(LOG_INFO)
        elif lvl.lower() in ("warning", "warn", "w"):
            DBG.set(LOG_WARN)
        elif lvl.lower() in ("fatal", "fail", "f"):
            DBG.set(LOG_FAIL)
        else:
            log(LOG_FAIL, f"Invalid level '{lvl}'. Valid levels are 'Base', "\
                +"'Verbose', 'Debug', 'Info', 'Warning', 'Fatal'.")

    def print_valid_commands(self):
        print(CONSOLE_HELP % "\n".join(
            list(self.command_help_data.get("manual", {}).keys())))

    def process_command(self, command: str, help_on_fail=True):
        if command == "": return
        log(LOG_DEBG, f"Executing command: '{command}'")
        self.history.append(command)
        operation, *args = command.split()
        for arg in args.copy():
            if hasattr(self, f"{operation}_{arg}"):
                operation = f"{operation}_{arg}"
                del args[0]
            else:
                break
        if hasattr(self, operation) and not operation.startswith("__"):
            try:
                self.previous_result = getattr(self, operation)(*args) or self.previous_result
            except InvalidCommandException as e:
                log(LOG_FAIL, f"The command format provided is not valid.")
                log(LOG_FAIL, f"Message: {e}")
                if help_on_fail:
                    self.print_valid_commands()
            except Exception as e:
                log(LOG_FAIL, f"There was an error ({repr(e)}) executing the command.")
                if help_on_fail:
                    self.print_valid_commands()
                raise e
        else:
            log(LOG_FAIL, f"Invalid command '{operation}'!")
            if help_on_fail:
                self.print_valid_commands()

    def mainloop(self):
        while not self.should_close:
            command = input("\r"+TERMINAL_PROMPT)
            self.process_command(command)

def launch_terminal(tc):
    DBG.set_cr_on_log()
    ccp = CCP(tc)
    ccp.mainloop()
