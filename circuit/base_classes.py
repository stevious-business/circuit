from json import loads, JSONDecodeError

from circuitlogger import log
from locals import *


class BaseComponent:

    _component_name = "Basic Component"
    _component_file_path = "dummy.json"

    def __init__(self):
        self._load_from_component_file(self._component_file_path)

    def _load_from_component_file(self, path):
        # TODO: Proper asset handling / data version checking etc.
        # AKA Resource manager in general
        try:
            with open(path) as f:
                component_data = loads(f.read())
        except FileNotFoundError:
            log(LOG_FAIL, f"Failed to initialize component '{self._component_name}': File {path} not found!")
        except JSONDecodeError:
            log(LOG_FAIL, f"Failed to initialize component '{self._component_name}': Malformed JSON in {path}!")


class Package:
    # TODO: Move params to configuration file
    def __init__(self, id: str, name: str, included_components: dict[str: type],
                 publisher="lcst", base_path="packages"):
        self.id = id
        self.name = name
        # global id -> component class
        self.included_components = {}
        # Mangle component names
        for c_name in included_components:
            mangled_name = ".".join([publisher, id, c_name])
            self.included_components[mangled_name] = included_components[c_name]
        self.base_path = base_path
        self.components_path = base_path + "/components"
        self.component_scripts_path = base_path + "/component_scripts"

    def get_components(self):
        return self.included_components
