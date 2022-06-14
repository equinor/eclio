import eclio.version

from .egrid_constructor import LGR, NNC, Amalgamation, egrid
from .egrid_contents import GdOrient, GridFormat, GridUnit, RockModel, TypeOfGrid, Units

__all__ = [
    "egrid",
    "GdOrient",
    "GridFormat",
    "GridUnit",
    "RockModel",
    "TypeOfGrid",
    "Units",
    "LGR",
    "NNC",
    "Amalgamation",
]

__author__ = "Equinor"
__email__ = "fg_sib-scout@equinor.com"

__version__ = eclio.version.version
