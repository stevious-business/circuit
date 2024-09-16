from os.path import join, basename
from json import loads, JSONDecodeError

from .dag import DAG
from circuitlogger import *
from configuration import INCLUDED_PACKAGES


class ProjectLoaderError(RuntimeError): pass


class Project:
    def __init__(self, name):
        self.config = {}
        self.name = name
        self.metadata = {}
        self.is_loaded = True
        self.ddag = DAG()
        self.included_components = {}
        self.root_component = None
        self.selected_component = None

    def load_from_config(self, data, package_datas):
        self.config = data
        if self.config == {}:
            log(LOG_FAIL, f"Received empty project config!")
            raise ValueError("No configuration data")
        project_dependencies = data["required-packages"]
        for packname in project_dependencies:
            prepped_pname = "packages." + packname
            if not prepped_pname in package_datas.keys():
                log(LOG_FAIL, f"Package {prepped_pname} is not available!")
                raise ProjectLoaderError(f"Error obtaining package")
            package_data = package_datas[prepped_pname]
            for chipname in project_dependencies[packname]:
                try:
                    component_data = package_data.PACKAGE[chipname]
                    self.included_components[package_data.PACKAGE.mangled_name(chipname)] = component_data
                except KeyError:
                    log(LOG_FAIL, f"Chip {package_data.PACKAGE.mangled_name(chipname)} could not be found!")
                    raise ProjectLoaderError("Error obtaining component")
        return self

    def save(self, path):
        return

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
