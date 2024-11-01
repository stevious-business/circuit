from json import loads, JSONDecodeError
from os.path import basename

from .backend.dag import DAG
from circuitlogger import log
from locals import *


class Pin:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.has_label = False
        self.label_ = ""
        self.linked_to_wire = False
        self.wire = -1

    def move(self, x, y):
        self.x = x
        self.y = y

    def label(self, l):
        self.has_label = True
        self.label_ = l

    def link_to_wire(self, widx):
        self.linked_to_wire = True
        self.wire = widx

    @staticmethod
    def from_json(json: dict):
        x = json["x"]
        y = json["y"]
        label = json.get("label", None)
        has_label = label is not None
        wire = json.get("wire", None)
        has_wire = wire is not None
        p = Pin(x, y)
        p.has_label = has_label
        if has_label:
            p.label(label)
        if has_wire:
            p.link_to_wire(wire)
        return p


class Chip:
    def __init__(self, component, x, y):
        self.x = x
        self.y = y
        self.component = component

    def move(self, x, y):
        self.x = x
        self.y = y

    @staticmethod
    def from_json(json):
        # TODO: Find a good way to handle component types
        c = Chip()
        c.move(json["x"], json["y"])


class Component:
    def __init__(self, project, id_):
        # TODO: Find some good way to obtain this from id
        # IMPORTANT NOTE ABOUT PROJECT: Components may be used throughout multiple projects.
        # The project attribute is specific to an instance of an open project.
        # A component instance exists for every chip, but does not contain chip information
        self.id_ = id_
        self.project = project
        self.projectDDAG: DAG = self.project.ddag
        self.projectDDAG.add_node(id_, True)
        self.pins = {}
        self.io_pins = {}
        self.chips = {}
        self.wires = {}
        self.metadata = {}
        self.new_pin_idx = lambda: self._new_idx(self.pins)
        self.new_iopin_idx = lambda: self._new_idx(self.io_pins)
        self.new_chip_idx = lambda: self._new_idx(self.chips)
        self.new_wire_idx = lambda: self._new_idx(self.wires)

    def _new_idx(self, dict_: dict) -> str:
        # Runs in o(n) (i think)
        used_keys = set(dict_.keys())
        idx = 0
        while True:
            if str(idx) in used_keys:
                idx += 1
            else:
                return str(idx)

    def new_pin(self, x: int, y: int):
        self.pins[self.new_pin_idx()] = Pin(x, y)

    def mark_pin_as_io(self, idx: str):
        assert self.pins.get(idx, None)
        self.io_pins[self.new_iopin_idx()] = idx

    def add_chip(self, component, x, y):
        self.chips[self.new_chip_idx()] = Chip(component, x, y)
        # Add dependency
        self.projectDDAG.connect(self.id_, component.id_)

    def get_pin(self, idx: str):
        return self.pins[idx]

    def get_chip(self, idx: str):
        return self.chips[idx]

    def get_wire(self, idx: str):
        return self.wires[idx]

    def setid(self, id_):
        self.id_ = id_

    @staticmethod
    def from_json(project, id_, json: dict):
        # TODO: Error messages for asserts
        assert "component-data" in json
        assert "pins" in json
        assert "io-pins" in json
        assert "subcomponents" in json
        assert "wires" in json
        c = Component(project, id_)
        c.metadata = json["component_meta"]
        c.io_pins = json["io-pins"]
        for k in json["pins"]:
            c.pins[k] = Pin.from_json(json["pins"][k])
        return c

    @staticmethod
    def from_file(project, path):
        try:
            id_from_path = ".".join(basename(path).split(".")[:-1])
            with open(path) as f:
                jsondata = loads(f.read())
            return Component.from_json(project, id_from_path, jsondata)
        except FileNotFoundError:
            log(LOG_FAIL, f"Component from {path} could not be loaded")
            raise
        except JSONDecodeError:
            log(LOG_FAIL, f"Component from {path} has invalid json")
            raise


class PluginComponent(Component):
    """Component class for package plugin components"""
    # TODO: Think about global update candidates here

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
        self.publisher = publisher
        # global id -> component class
        self.included_components = {}
        # Mangle component names
        for c_name in included_components:
            mangled_name = ".".join([publisher, id, c_name])
            self.included_components[mangled_name] = included_components[c_name]
        self.base_path = base_path
        self.components_path = base_path + "/components"
        self.component_scripts_path = base_path + "/component_scripts"

    def mangled_name(self, c_name):
        return ".".join([self.publisher, self.id, c_name])

    def get_components(self):
        return self.included_components

    def get_ambiguous_component_names(self):
        cnames = []
        universal_prefix = self.publisher+"."+self.id+"."
        for mangled_name in self.included_components.keys():
            ambiguous_name = mangled_name.removeprefix(universal_prefix)
            cnames.append(ambiguous_name)
        return cnames

    def __getitem__(self, item):
        if item in self.included_components.keys():
            return self.included_components[item]
        elif self.mangled_name(item) in self.included_components.keys():
            return self.included_components[self.mangled_name(item)]
        raise KeyError(item)
