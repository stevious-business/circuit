from os.path import join
from json import loads, JSONDecodeError

from .dag import DAG
from circuitlogger import *


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

    def load_from_config(self, data):
        self.config = data
        return self

    def save(self, path):
        return

    @staticmethod
    def load(path):
        try:
            with open(join(path, "config.json")) as config_file:
                config_data = loads(config_file.read())
        except FileNotFoundError:
            log(LOG_FAIL, f"Could not locate project config @ {path}!")
        except JSONDecodeError as e:
            log(LOG_FAIL, f"Malformed project json for project {path}! {e}")
        return Project().load_from_config(config_data)
