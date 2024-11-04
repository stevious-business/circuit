from json import loads, JSONDecodeError, dumps
from os.path import basename, join

from .backend.dag import DAG
from circuitlogger import log
from locals import *


def serialize(dict_):
    json = {}
    for k in dict_:
        object_ = dict_[k]
        if not hasattr(object_, "serialize"):
            log(LOG_WARN, f"Encountered unserializable object {object_}!")
        else:
            json[k] = object_.serialize()
    return json


class Pin:
    def __init__(self, x, y):
        self.x = int(x)
        self.y = int(y)
        self.has_label = False
        self.label_ = ""
        self.linked_to_wire = False
        self.wire = -1

    def move(self, x, y):
        self.x = int(x)
        self.y = int(y)

    def label(self, l):
        self.has_label = True
        self.label_ = l

    def link_to_wire(self, widx):
        self.linked_to_wire = True
        self.wire = int(widx)

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

    def serialize(self):
        d = {}
        if self.linked_to_wire:
            d["wire"] = self.wire
        d |= {
            "x": self.x,
            "y": self.y
        }
        if self.has_label:
            d["label"] = self.label_
        return d


class WireDataHandler:
    def __init__(self):
        self.dataFormat = {}

    def add_package(self, pack):
        self.dataFormat[pack.uid()] = pack.get_data_format()

    @staticmethod
    def from_packdatas(packdatas):
        wdh = WireDataHandler()
        for packname in packdatas:
            pack: Package = packdatas[packname].PACKAGE
            wdh.add_package(pack)


class Wire:

    class AlreadyConnectedError(ValueError): pass

    class Connection:

        class Endpoint:
            # subclasses must override this
            def serialize(self): pass

        class PinEndpoint(Endpoint):
            def __init__(self, id_):
                self.id = int(id_)

            def serialize(self):
                return {
                    "type": "pin",
                    "id": self.id
                }

        class ChipEndpoint(Endpoint):
            def __init__(self, cid, iid):
                self.cid = int(cid)
                self.iid = int(iid)

            def serialize(self):
                return {
                    "type": "chip",
                    "cid": self.cid,
                    "iid": self.iid
                }

        def __init__(self):
            self.from_: Wire.Connection.Endpoint = None
            self.to: Wire.Connection.Endpoint = None

        def getpins(self):
            p = []
            if isinstance(self.from_, Wire.Connection.PinEndpoint):
                p.append(self.from_.id)
            if isinstance(self.to, Wire.Connection.PinEndpoint):
                p.append(self.to.id)
            return p

        def set_from(self, e: Endpoint):
            self.from_ = e

        def set_to(self, e: Endpoint):
            self.to = e

        @staticmethod
        def endpointFromString(s: str):
            if s.startswith("p"):
                # pin (p<id>)
                assert s[1:].isdigit()
                pid = s[1:]
                e = Wire.Connection.PinEndpoint(pid)
                return e
            elif s.startswith("c"):
                # chip (c<cid>.<iid>)
                cid, iid, *_ = s[1:].split(".")
                assert cid.isdigit()
                assert iid.isdigit()
                e = Wire.Connection.ChipEndpoint(cid, iid)
                return e
            else:
                raise ValueError(s)

        @staticmethod
        def new(s1, s2):
            c = Wire.Connection()
            c.set_from(Wire.Connection.endpointFromString(s1))
            c.set_to(Wire.Connection.endpointFromString(s2))
            return c

        def serialize(self):
            return {
                "from": self.from_.serialize(),
                "to": self.to.serialize()
            }

    def __init__(self):
        self.connections: list[Wire.Connection] = []

    def serialize(self):
        return {
            "connections": [conn.serialize() for conn in self.connections]
        }

    def add_connection(self, c: Connection):
        self.connections.append(c)

    def connect(self, s1, s2):
        self.add_connection(Wire.Connection.new(s1, s2))


class Chip:
    def __init__(self, component, x, y):
        self.x = int(x)
        self.y = int(y)
        self.component = component

    def move(self, x, y):
        self.x = int(x)
        self.y = int(y)

    @staticmethod
    def from_json(json):
        # TODO: Find a good way to handle component types
        c = Chip()
        c.move(json["x"], json["y"])

    def serialize(self):
        return {
            "type": self.component.id_,
            "x": self.x,
            "y": self.y
        }


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
        self.metadata = {
            "data-version": 1,
            "width": -1,
            "height": -1,
            "backgroud-color": "#000000",
            "box-label": ""
        }
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

    def new_wire(self, e1: str, e2: str):
        w = Wire()
        idx = self.new_wire_idx()
        self.wires[idx] = w
        self.wire_connect(idx, e1, e2)

    def wire_connect(self, idx, e1, e2):
        assert self.wires.get(idx, None), f"Wire {idx} does not exist"
        conn = Wire.Connection.new(e1, e2)
        inv = conn.getpins()
        while inv:
            firstPinIdx: Wire.Connection.PinEndpoint = inv[0]
            pinobj: Pin = self.pins[str(firstPinIdx)]
            if pinobj.linked_to_wire:
                if not pinobj.wire == int(idx):
                    raise Wire.AlreadyConnectedError(firstPinIdx)
            else:
                pinobj.link_to_wire(idx)
            del inv[0]
        self.wires[idx].add_connection(conn)

    def mark_pin_as_io(self, idx: str, state=True):
        assert self.pins.get(idx, None)
        if state:
            self.io_pins[self.new_iopin_idx()] = int(idx)
        else:
            for k in self.io_pins:
                if str(self.io_pins[k]) == idx:
                    del self.io_pins[k]
                    break

    def add_chip(self, component, x, y):
        warning = "Cannot place %s in %s recursively"
        prevent_place = self.projectDDAG.connection_exists(
            component.id_, self.id_
        )
        assert not prevent_place, warning % (self.id_, component.id_)
        self.chips[self.new_chip_idx()] = Chip(component, x, y)
        # Add dependency
        self.projectDDAG.connect(self.id_, component.id_)

    def get_pin(self, idx: str) -> Pin:
        return self.pins[idx]

    def get_chip(self, idx: str) -> Chip:
        return self.chips[idx]

    def get_wire(self, idx: str):
        return self.wires[idx]

    def setid(self, id_):
        self.id_ = id_

    @staticmethod
    def from_json(project, id_, json: dict):
        assert "component-meta" in json, "Missing <component-meta> in json!"
        assert "pins" in json, "Missing <pins> in json!"
        assert "io-pins" in json, "Missing <io-pins> in json!"
        assert "subcomponents" in json, "Missing <subcomponents> in json!"
        assert "wires" in json, "Missing <wires> in json!"
        c = Component(project, id_)
        c.metadata = json["component-meta"]
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

    def save(self, filepath):
        with open(filepath, "w") as wfile:
            json = {}
            json["component-meta"] = self.metadata
            json["pins"] = serialize(self.pins)
            json["io-pins"] = self.io_pins
            json["subcomponents"] = serialize(self.chips)
            json["wires"] = serialize(self.wires)
            wfile.write(dumps(json, indent=4))


class PluginComponent(Component):
    """Component class for package plugin components"""
    # TODO: Think about global update candidates here

    _component_name = "Basic Component"
    _component_file_path = "dummy.json"

    def __init__(self, project, id_, package_path):
        super().__init__(project, id_)
        self._load_from_component_file(join(
            package_path,
            "components",
            self._component_file_path
        ))

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
    def __init__(self, id: str, name: str,
                 included_components: dict[str: type], data_fmt=[],
                 publisher="lcst"):
        self.id = id
        self.name = name
        self.publisher = publisher
        # global id -> component class
        self.included_components = {}
        # Mangle component names
        for c_name in included_components:
            mangled_name = ".".join([publisher, id, c_name])
            self.included_components[mangled_name] = included_components[c_name]
        self.data_format = data_fmt

    def has_component(self, id_):
        return id_ in self.included_components.keys()

    def uid(self):
        return ".".join([self.publisher, self.id])

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

    def get_data_format(self):
        return self.data_format
