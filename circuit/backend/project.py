from os.path import join, basename, exists, dirname
from os import makedirs, mkdir
from json import loads, dumps, JSONDecodeError
import re

from .dag import DAG
from circuitlogger import *
from configuration import INCLUDED_PACKAGES
from circuit.base_classes import Component, PluginComponent
from circuit.package_manager import trygetpackage


class ProjectLoaderError(RuntimeError): pass


class ComponentWrapper:
    def __init__(self, c: Component, n):
        self.component = c
        self.name = n
        self.id_ = c.id_
        project: Project = c.project
        self.path = Project.id_to_file_name(
            self.id_,
            project.get_component_file_names()
        )

    def serialize(self):
        return {
            "name": self.name,
            "path": self.path
        }

    @staticmethod
    def load_from_component_dict(project, ckey, cdict):
        name = cdict["name"]
        path = cdict["path"]
        with open(path) as rf:
            jsondata = loads(rf.read()) # TODO: error msgs
        return ComponentWrapper(Component.from_json(project, ckey, jsondata),
                                name)


class Project:
    def __init__(self, name):
        self.config = {
            "settings": {
                "true_subsize": False
            },
            "root-component": {
                "id": None
            },
            "required-packages": {},
            "components": {}
        }
        self.name = name
        self.metadata = {
            "data-version": 1,
            "name": name,
            "description": "New project"
        }
        self.is_loaded = True
        self.ddag = DAG()
        self.included_components = {}
        self.root_component = None
        self.selected_component = None

    def set_meta(self, attrname, *values):
        if attrname in ("description", "name"):
            self.metadata[attrname] = " ".join(values)

    def load_from_config(self, data, package_datas):
        self.config = data.copy()
        if self.config == {}:
            log(LOG_FAIL, f"Received empty project config!")
            raise ValueError("No configuration data")
        del self.config["meta"]
        for k in data["meta"]:
            if k in ("data-version", "name", "description"):
                self.set_meta(k, data["meta"][k])
        del self.config["components"]
        self.config["components"] = {}
        for ckey in data["components"]:
            cw = ComponentWrapper.load_from_component_dict(
                self,
                ckey,
                data["components"][ckey]
            )
            self.config["components"][ckey] = cw
        project_dependencies = data["required-packages"]
        for packname in project_dependencies:
            if not packname in package_datas.keys():
                log(LOG_FAIL, f"Package {packname} is not available!")
                raise ProjectLoaderError(f"Error obtaining package")
            package_data = package_datas[packname]
            for chipname in project_dependencies[packname]:
                try:
                    component_class = package_data.PACKAGE[chipname]
                    self.included_components[package_data.PACKAGE.mangled_name(chipname)] = component_class
                except KeyError:
                    log(LOG_FAIL, f"Chip {package_data.PACKAGE.mangled_name(chipname)} could not be found!")
                    raise ProjectLoaderError("Error obtaining component")
        return self

    @staticmethod
    def id_to_file_name(id_: str, existing_names=None):
        existing_names = existing_names or [] # damn you weird python feature
        primary_fn = id_+".json"
        i = 2
        while primary_fn in existing_names:
            primary_fn = id_+str(i)+".json"
            i += 1
        return primary_fn

    def get_component_file_names(self):
        fns = []
        for ckey in self.config["components"]:
            cw: ComponentWrapper = self.config["components"][ckey]
            fns.append(cw.path)
        return fns

    def save(self, path):
        makedirs(path, exist_ok=True)
        if not exists(join(path, "components")):
            mkdir(join(path, "components"))
        config_dict = {"meta": self.metadata}
        config_dict |= self.config
        del config_dict["components"]
        config_dict["components"] = {}
        for ckey in self.config["components"]:
            cw = self.getComponentWrapper(ckey)
            json = cw.serialize()
            config_dict["components"][ckey] = json
        with open(join(path, "config.json"), "w") as configfile:
            configfile.write(dumps(config_dict, indent=4))
        for ckey in self.config["components"]:
            c: ComponentWrapper = self.config["components"][ckey]
            c.component.save(join(path, "components", c.path))

    @staticmethod
    def load(path, package_datas: dict):
        config_data = {}
        try:
            with open(join(path, "config.json")) as config_file:
                config_data = loads(config_file.read())
        except FileNotFoundError:
            log(LOG_FAIL, f"Could not locate project config @ {path}!")
        except JSONDecodeError as e:
            log(LOG_FAIL, f"Malformed project json for project {path}! {e}")
        return Project(basename(path)).load_from_config(config_data, package_datas)

    def set_root_id(self, id_: str):
        if not id_ in self.config["components"].keys():
            raise KeyError("No component with ID " + id_)
        self.config["root-component"]["id"] = id_

    def new_component(self, id_: str, n=None):
        name = n or id_
        if re.fullmatch("[a-zA-Z_.][a-zA-Z0-9_\-.]*", id_) is None:
            raise ValueError(f"{id_} is an invalid component ID!")
        if id_ in self.config["components"].keys():
            raise ValueError(f"Component {id_} already exists!")
        c = Component(self, id_)
        self.config["components"][id_] = ComponentWrapper(c, name)
        return c

    def getComponentWrapper(self, id_) -> ComponentWrapper:
        return self.config["components"][id_]

    def getComponent(self, id_, packdatas) -> Component | PluginComponent:
        if self.componentExists(id_):
            return self.getComponentWrapper(id_).component
        if self.pluginComponentExists(id_):
            pcClass = self.included_components[id_]
            containerPackage = trygetpackage(id_, packdatas)
            packpath = dirname(containerPackage.__file__)
            component: PluginComponent = pcClass(self, id_, packpath)
            return component
        raise KeyError(f"Component {id_} does not exist!")

    def componentExists(self, id_) -> bool:
        """Check whether `id_` is a project component"""
        return id_ in self.config["components"].keys()

    def pluginComponentExists(self, id_) -> bool:
        return id_ in self.included_components.keys()
