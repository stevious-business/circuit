import circuitlogger
from locals import *
from circuit.base_classes import Package

from .component_scripts import vcc, gnd, nmos_fet, pmos_fet


PACKAGE = Package(
    "_builtins",
    "Built-in Components",
    {
        "vcc": vcc.VCC,
        "gnd": gnd.GND,
        "nmos_fet": nmos_fet.NMOS_FET,
        "pmos_fet": pmos_fet.PMOS_FET
    }
)
