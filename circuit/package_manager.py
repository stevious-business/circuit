from importlib import import_module

from circuit.base_classes import Package, PluginComponent
from circuitlogger import *


class InvalidPackageError(ImportError): pass


def load_package(package_name: str):
    log(LOG_DEBG, f"Loading package {package_name}...")
    log(LOG_VERB, f"Importing package...")
    try:
        package_module = import_module(".".join([package_name, "package"]))
    except ImportError:
        raise InvalidPackageError(f"Package {package_name} cannot be imported!")
    log(LOG_VERB, f"Validating package...")
    if (errc := validate_package(package_module)):
        raise InvalidPackageError(f"Package {package_name} is invalid [Err {errc}]")
    log(LOG_DEBG, f"Finished loading package {package_name}!")
    return package_module


def validate_package(pack) -> int:
    # TODO: Check data versions etc.
    ERR_CODE = 0
    F_INVALID = 0x1
    F_PACKATTR = 0x2
    F_PACKTYPE = 0x4
    F_COMPTYPE = 0x8
    try:
        if not hasattr(pack, "PACKAGE"): ERR_CODE |= F_PACKATTR
        if not isinstance(pack.PACKAGE, Package): ERR_CODE |= F_PACKTYPE
        for component_name in pack.PACKAGE.get_components():
            log(LOG_VERB, f"Loading component {component_name}...")
            component_class = pack.PACKAGE.included_components[component_name]
            if not issubclass(component_class, PluginComponent):
                log(LOG_WARN, f"Component does not inherit from PluginComponent: {component_class}")
                ERR_CODE |= F_COMPTYPE
            log(LOG_VERB, "Done!")
    except:
        ERR_CODE |= F_INVALID
    finally:
        return ERR_CODE
