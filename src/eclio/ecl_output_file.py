from dataclasses import astuple, dataclass, fields
from enum import Enum, auto, unique
from typing import Any, List, Tuple, Union

from .keyword import match_keyword


@unique
class TypeOfGrid(Enum):
    """
    A Grid has three possible data layout formats, UNSTRUCTURED, CORNER_POINT,
    BLOCK_CENTER and COMPOSITE (meaning combination of the two former). Only
    CORNER_POINT layout is supported by XTGeo.
    """

    COMPOSITE = 0
    CORNER_POINT = 1
    UNSTRUCTURED = 2
    BLOCK_CENTER = 3

    @classmethod
    def alternate_code(cls, code):
        """Converts from alternate code to TypeOfGrid member.

        weirdly, type of grid sometimes (For instance init's INTHEAD and
        FILEHEAD) have an alternate integer code for type of grid.
        """
        if code == 0:
            type_of_grid = cls.CORNER_POINT
        elif code == 1:
            type_of_grid = cls.UNSTRUCTURED
        elif code == 2:
            type_of_grid = cls.COMPOSITE
        elif code == 3:
            type_of_grid = cls.BLOCK_CENTER
        else:
            raise ValueError(f"Unknown grid type {code}")
        return type_of_grid

    @property
    def alternate_value(self):
        """Inverse of alternate_code."""
        alternate_value = 0
        if self == TypeOfGrid.CORNER_POINT:
            alternate_value = 0
        elif self == TypeOfGrid.UNSTRUCTURED:
            alternate_value = 1
        elif self == TypeOfGrid.COMPOSITE:
            alternate_value = 2
        elif self == TypeOfGrid.BLOCK_CENTER:
            alternate_value = 3
        else:
            raise ValueError(f"Unknown grid type {self}")
        return alternate_value


@unique
class Units(Enum):
    METRES = auto()
    CM = auto()
    FEET = auto()

    def to_ecl(self):
        return self.name

    @classmethod
    def from_ecl(cls, unit_string):
        if hasattr(unit_string, "decode"):
            unit_string = unit_string.decode()
        if match_keyword(unit_string, "METRES"):
            return cls.METRES
        if match_keyword(unit_string, "FEET"):
            return cls.FEET
        if match_keyword(unit_string, "CM"):
            return cls.CM
        raise ValueError(f"Unknown unit string {unit_string}")


@unique
class GridRelative(Enum):
    """GridRelative is the second value given GRIDUNIT keyword.

    MAP means map relative units, while
    leaving it blank means relative to the origin given by the
    MAPAXES keyword.
    """

    MAP = auto()
    ORIGIN = auto()

    def to_ecl(self) -> str:
        if self == GridRelative.MAP:
            return "MAP"
        else:
            return ""

    @classmethod
    def from_ecl(cls, unit_string: str):
        if hasattr(unit_string, "decode"):
            unit_string = unit_string.decode()
        if match_keyword(unit_string, "MAP"):
            return cls.MAP
        else:
            return cls.ORIGIN


@dataclass
class EclKeyword:
    """An abstract ecl keyword.

    Gives a general implementation of to/from ecl which recurses on
    fields. Ie. a dataclass such as

    >>> @dataclass
    >>> class MyKeyword(GrdeclKeyword):
    >>>      field1 : A
    >>>      field2 : B

    will have a to_grdec  method that returns

    >>> [self.field1.to_grdecl(), self.field2.to_grdecl()]

    Similarly from_grdecl will call fields from_grdecl
    to construct the object

    >>> MyKeyword(A.from_grdecl(values[0]), B.from_grdecl(values[1]))
    """

    def to_ecl(self) -> List[Any]:
        """Convert the keyword to list of grdecl keyword values.
        Returns:
            list of values of the given keyword. ie. The keyword read from
            "SPECGRID" with values "[1, 1, 1, 0]" should return
            [1,1,1,CoordinateType.CYLINDRICAL]
        """
        return [value.to_ecl() for value in astuple(self)]

    @classmethod
    def from_ecl(cls, values):
        """Convert list of ecl keyword values to a keyword.
        Args:
            values(list): list of values given after the keyword in
                the grdecl file.
        Returns:
            A EclKeyword constructed from the given values.
        """
        object_types = [f.type for f in fields(cls)]
        return cls(*[typ.from_ecl(val) for val, typ in zip(values, object_types)])


@unique
class Order(Enum):
    """Either increasing or decreasing.

    Used for the grdecl keywords INC and DEC
    respectively.
    """

    INCREASING = auto()
    DECREASING = auto()

    def to_ecl(self) -> str:
        return str(self.name)[0:3]

    @classmethod
    def from_ecl(cls, order_string):
        if hasattr(order_string, "decode"):
            order_string = order_string.decode()
        if match_keyword(order_string, "INC"):
            return cls.INCREASING
        if match_keyword(order_string, "DEC"):
            return cls.DECREASING


@unique
class Handedness(Enum):
    """The handedness of an orientation.

    Eiter left handed or right handed.  Used for the grdecl keywords LEFT and
    RIGHT.
    """

    LEFT = auto()
    RIGHT = auto()

    def to_ecl(self) -> str:
        return self.name

    @classmethod
    def from_ecl(cls, orientation_string):
        if hasattr(orientation_string, "decode"):
            orientation_string = orientation_string.decode()
        if match_keyword(orientation_string, "LEFT"):
            return cls.LEFT
        if match_keyword(orientation_string, "RIGHT"):
            return cls.RIGHT
        raise ValueError(f"Unknown handedness string {orientation_string}")


@unique
class Orientation(Enum):
    """Either up or down, for the grdecl keywords UP and DOWN."""

    UP = auto()
    DOWN = auto()

    def to_ecl(self) -> str:
        return self.name

    @classmethod
    def from_ecl(cls, orientation_string: str):
        if hasattr(orientation_string, "decode"):
            orientation_string = orientation_string.decode()
        if match_keyword(orientation_string, "UP"):
            return cls.UP
        if match_keyword(orientation_string, "DOWN"):
            return cls.DOWN
        raise ValueError(f"Unknown orientation string {orientation_string}")


@dataclass
class GdOrient(EclKeyword):
    """The GDORIENT keyword gives the orientation of the grid.

    The three first values is either increasing or decreasing
    depending on whether the corresponding dimension has increasing
    or decreasing coordinates. Then comes the direction of the z dimension,
    and finally the handedness of the orientation. Defaults to
    "GDORIENT INC INC INC DOWN RIGHT /".
    """

    i_order: Order = Order.INCREASING
    j_order: Order = Order.INCREASING
    k_order: Order = Order.INCREASING
    z_direction: Orientation = Orientation.DOWN
    handedness: Handedness = Handedness.RIGHT


@dataclass
class GridUnit(EclKeyword):
    """Defines the units used for grid dimensions.

    The first value is a string describing the units used, defaults to METRES,
    known accepted other units are FIELD and LAB. The last value describes
    whether the measurements are relative to the map or to the origin of
    MAPAXES.
    """

    unit: Units = Units.METRES
    grid_relative: GridRelative = GridRelative.ORIGIN


@dataclass
class MapAxes(EclKeyword):
    """The mapaxes keyword gives the local coordinate system of the map.

    The map coordinate system is given by a point on the y line, the origin and
    a point on the x line. ie. The usual coordinate system is given by "MAPAXES
    0 1 0 0 1 0 /" where the two first values is a point on the y line, the
    middle two values is the origin, and the last two values is a point on the
    x line.
    """

    y_line: Tuple[float, float] = (0.0, 1.0)
    origin: Tuple[float, float] = (0.0, 0.0)
    x_line: Tuple[float, float] = (1.0, 0.0)

    def to_ecl(self) -> List[float]:
        return list(self.y_line) + list(self.origin) + list(self.x_line)

    @classmethod
    def from_ecl(cls, values: List[Union[float, str]]):
        if len(values) != 6:
            raise ValueError("MAPAXES must contain 6 values")
        return cls(
            (float(values[0]), float(values[1])),
            (float(values[2]), float(values[3])),
            (float(values[4]), float(values[5])),
        )


@unique
class CoordinateType(Enum):
    """The coordinate system type given in the SPECGRID keyword.

    This is given by either T or F in the last value of SPECGRID, meaning
    either cylindrical or cartesian coordinates respectively.
    """

    CARTESIAN = auto()
    CYLINDRICAL = auto()

    def to_ecl(self) -> bool:
        if self == CoordinateType.CARTESIAN:
            return False
        else:
            return True

    @classmethod
    def from_ecl(cls, coord_value: bool):
        if coord_value:
            return cls.CYLINDRICAL
        else:
            return cls.CARTESIAN
