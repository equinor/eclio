"""
The egrid fileformat is a file outputted by reservoir simulators such as opm
flow containing the grid geometry.

There is an alternate data layout (in addition to that of grdecl files), called
unstructured, which is not widely supported. ecl-io does not currently support
that format.

The package ecl-data-io handles the carrying format and outputs pairs of
keywords and data values.The enums in this file generally describe a range of
values for a position in one of these lists, the dataclasses describe the
values of one keyword or a collection of those, named a file section.

The following egrid file contents (as keyword/array pairs)::

  ("FILEHEAD", [2001,3,0,3,0,0,0])
  ("GRIDUNIT", "METRES   ")

is represented by::

    EGridHead(
        Filehead(2001,3,3,TypeOfGrid.CORNER_POINT,RockModel(0),GridFormat(0)),
        GridUnit("METRES   ")
    )

Where ``EGridHead`` is a section of the file, ``Filehead`` and ``GridUnit`` are
keywords.

Generally, the data layout of these objects map 1-to-1 with some section of an
valid egrid file.

keywords implement the `to_ecl` and `from_ecl` functions
which should satisfy::

    GridHead.from_ecl(x).to_ecl() == x

These convert to and from the object representation and the keyword/array
pairs, ie.

>>> grid_head_contents = [0]*100
>>> head = GridHead.from_ecl(grid_head_contents)
>>> head
GridHead(type_of_grid=<TypeOfGrid.COMPOSITE...
>>> head.to_ecl().tolist() == grid_head_contents
True

Several structures describe a corner point geometry which
is defined by data in the keywords COORD, ZCORN and ACTNUM.

The corner point geometry is made up of nx*ny*nz cells in three corresponding
dimensions.

The values in COORD, ZCORN and ACTNUM are stored flattened in F-order and
have dimensions (nx+1,ny+1,6), (nx,2,ny,2,nz,2), and (nx,ny,nz) respectively.

COORD and ZCORN descibe the position of corners in the corner point geometry.
There is a straight line from the bottom to the top of the grid on which the
corners of each grid lie. COORD describe the top and bottom (x,y,z) values of
these corner lines, hence, it contains six floats for each corner line.

ZCORN has 8 values for each grid, which describes the z-value (height) at
which that cells corners intersect with the corresponding corner line. The
order of corners is  "left" before "right" in the second dimension of
ZCORN, "near"  before "far" in the fourth dimension , and "upper" before
"bottom" in the last dimension. Note that this orientation assumes,
increasing first dimension as to the "right", increasing second dimension
towards "far", and increasing third dimension as towards "bottom".

The topology is such that, assuming no gaps between cells, the (i,j,k)th
cell and the (i+1,j+1,k+1)th cell share the upper near left corner of the
(i+1,j+1,k+1)th cell which is the lower far right corner of the (i,j,k)th
cell.

ACTNUM describes the active status of each cell. For simulations without
dual porosity or thermal, 0 means inactive, 1 means active and other values
are not used. For dual porosity, 0 means inactive, 1 means matrix only,
2 means fracture only, and 3 means both fracture and matrix. For thermal
simulations, 0 means inactive, 1 means active, 2 means rock volume only,
3 means pore volume only.


"""
from dataclasses import dataclass
from enum import Enum, unique
from itertools import chain
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

import numpy as np
from ecl_data_io import Format, lazy_read, write

from .ecl_output_file import (
    CoordinateType,
    GdOrient,
    GridUnit,
    MapAxes,
    TypeOfGrid,
    Units,
)


class EGridFileFormatError(ValueError):
    """
    Exception raised when an file unexpectedly does not conform to the egrid
    format.
    """

    pass


@unique
class RockModel(Enum):
    """
    Type of rock model.
    """

    SINGLE_PERMEABILITY_POROSITY = 0
    DUAL_POROSITY = 1
    DUAL_PERMEABILITY = 2


@unique
class GridFormat(Enum):
    """
    The format of the "original grid", ie., what
    method was used to construct the values in the file.
    """

    UNKNOWN = 0
    IRREGULAR_CORNER_POINT = 1
    REGULAR_CARTESIAN = 2


@dataclass
class Filehead:
    """
    The first keyword in an egrid file is the FILEHEAD
    keyword, containing metadata about the file and its
    content.
    """

    version_number: int
    year: int
    version_bound: int
    type_of_grid: TypeOfGrid
    rock_model: RockModel
    grid_format: GridFormat

    @classmethod
    def from_ecl(cls, values: List[int]):
        """
        Construct a Filehead given the list of values following
        the FILEHEAD keyword.
        Args:
            values(List[int]): list of values following the FILEHEAD keyword,
                expected to contain at least 7 values (normally 100).
        Returns:
            A Filhead constructed from the given values.
        """
        if len(values) < 7:
            raise ValueError(f"Filehead given too few values, {len(values)} < 7")
        return cls(
            version_number=values[0],
            year=values[1],
            version_bound=values[3],
            type_of_grid=TypeOfGrid.alternate_code(values[4]),
            rock_model=RockModel(values[5]),
            grid_format=GridFormat(values[6]),
        )

    def to_ecl(self) -> np.ndarray:
        """
        Returns:
            List of values, as layed out after the FILEHEAD keyword for
            the given filehead.
        """
        # The data is expected to consist of
        # 100 integers, but only a subset is used.
        result = np.zeros((100,), dtype=np.int32)
        result[0] = self.version_number
        result[1] = self.year
        result[3] = self.version_bound
        result[4] = self.type_of_grid.alternate_value
        result[5] = self.rock_model.value
        result[6] = self.grid_format.value
        return result


@dataclass
class GridHead:
    """
    Both for lgr (see LGRSection) and the global grid (see GlobalGrid)
    the GRIDHEAD keyword indicates the start of the grid layout for that
    section.
    """

    type_of_grid: TypeOfGrid
    num_x: int
    num_y: int
    num_z: int
    grid_reference_number: int
    numres: int
    nseg: int
    coordinate_type: CoordinateType
    lgr_start: Tuple[int, int, int]
    lgr_end: Tuple[int, int, int]

    @classmethod
    def from_ecl(cls, values: Sequence[int]):
        if len(values) < 33:
            raise ValueError(
                f"Too few arguments to GridHead.from_ecl {len(values)} < 33"
            )
        return cls(
            type_of_grid=TypeOfGrid(values[0]),
            num_x=values[1],
            num_y=values[2],
            num_z=values[3],
            grid_reference_number=values[4],
            numres=values[24],
            nseg=values[25],
            coordinate_type=CoordinateType.from_ecl(values[26]),
            lgr_start=(values[27], values[28], values[29]),
            lgr_end=(values[30], values[31], values[32]),
        )

    def to_ecl(self) -> np.ndarray:
        # The data is expected to consist of
        # 100 integers, but only a subset is used.
        result = np.zeros((100,), dtype=np.int32)
        result[0] = self.type_of_grid.value
        result[1] = self.num_x
        result[2] = self.num_y
        result[3] = self.num_z
        result[4] = self.grid_reference_number
        result[24] = self.numres
        result[25] = self.nseg
        result[26] = self.coordinate_type.to_ecl()
        result[[27, 28, 29]] = np.array(self.lgr_start)
        result[[30, 31, 32]] = np.array(self.lgr_end)
        return result


@dataclass
class LGRSection:
    """
    An Egrid file can contain multiple LGR (Local Grid Refinement) sections
    which define a subgrid with finer layout. The section contains one corner point
    geometry along with information about where it is located in the global grid (see
    :class:`GlobalGrid`.
    """

    grid_head: GridHead
    coord: np.ndarray
    zcorn: np.ndarray
    name: str
    actnum: Optional[np.ndarray] = None
    parent: Optional[str] = None
    grid_parent: Optional[str] = None
    hostnum: Optional[np.ndarray] = None
    boxorig: Optional[Tuple[int, int, int]] = None
    coord_sys: Optional[MapAxes] = None

    def __eq__(self, other):
        if not isinstance(other, LGRSection):
            return False
        return (
            self.grid_head == other.grid_head
            and np.array_equal(self.coord, other.coord)
            and np.array_equal(self.zcorn, other.zcorn)
            and np.array_equal(self.actnum, other.actnum)
            and self.name == other.name
            and self.parent == other.parent
            and self.grid_parent == other.grid_parent
            and np.array_equal(self.hostnum, other.hostnum)
            and self.boxorig == other.boxorig
            and self.coord_sys == other.coord_sys
        )

    def to_ecl(self) -> List[Tuple[str, Any]]:
        result_dict = {
            "gridhead": self.grid_head.to_ecl(),
            "coord   ": self.coord.astype(np.float32),
            "zcorn   ": self.zcorn.astype(np.float32),
        }
        if self.actnum is not None:
            result_dict["actnum  "] = self.actnum.astype(np.int32)
        result_dict["LGR     "] = [self.name]
        if self.parent is not None:
            result_dict["LGRPARNT"] = [self.parent]
        if self.grid_parent is not None:
            result_dict["LGRSGRID"] = [self.grid_parent]
        if self.hostnum is not None:
            result_dict["HOSTNUM "] = self.hostnum
        if self.boxorig is not None:
            result_dict["BOXORIG "] = np.array(self.boxorig, dtype=np.int32)
        if self.coord_sys is not None:
            result_dict["COORDSYS"] = self.coord_sys.to_ecl()
        result_dict["ENDGRID "] = np.array([], dtype=np.int32)
        result_dict["ENDLGR  "] = np.array([], dtype=np.int32)
        result = []
        order = [
            "LGR     ",
            "LGRPARNT",
            "LGRSGRID",
            "GRIDHEAD",
            "BOXORIG ",
            "COORD   ",
            "COORDSYS",
            "ZCORN   ",
            "ACTNUM  ",
            "HOSTNUM ",
            "ENDGRID ",
            "ENDLGR  ",
        ]
        for kw in order:
            if kw in result_dict:
                result.append((kw, result_dict[kw]))
        return result


@dataclass
class GlobalGrid:
    """
    The global grid contains the corner point layout of the grid without
    refinements, and the sectioning into grid coarsening through the optional
    corsnum keyword.
    """

    grid_head: GridHead
    coord: np.ndarray
    zcorn: np.ndarray
    actnum: Optional[np.ndarray] = None
    coord_sys: Optional[MapAxes] = None
    boxorig: Optional[Tuple[int, int, int]] = None
    corsnum: Optional[np.ndarray] = None

    def __eq__(self, other):
        if not isinstance(other, GlobalGrid):
            return False
        return (
            self.grid_head == other.grid_head
            and np.array_equal(self.coord, other.coord)
            and np.array_equal(self.zcorn, other.zcorn)
            and np.array_equal(self.actnum, other.actnum)
            and self.coord_sys == other.coord_sys
            and self.boxorig == other.boxorig
            and np.array_equal(self.corsnum, other.corsnum)
        )

    def to_ecl(self) -> List[Tuple[str, Any]]:
        result_dict = {
            "gridhead": self.grid_head.to_ecl(),
            "coord   ": self.coord.astype(np.float32),
            "zcorn   ": self.zcorn.astype(np.float32),
        }
        if self.actnum is not None:
            result_dict["actnum  "] = self.actnum.astype(np.int32)
        if self.coord_sys is not None:
            result_dict["COORDSYS"] = self.coord_sys.to_ecl()
        if self.boxorig is not None:
            result_dict["BOXORIG "] = np.array(self.boxorig, dtype=np.int32)
        if self.corsnum is not None:
            result_dict["CORSNUM "] = self.corsnum
        result_dict["ENDGRID "] = np.array([], dtype=np.int32)
        result = []
        order = [
            "GRIDHEAD",
            "BOXORIG ",
            "COORD   ",
            "COORDSYS",
            "ZCORN   ",
            "ACTNUM  ",
            "CORSNUM ",
            "ENDGRID ",
        ]
        for kw in order:
            if kw in result_dict:
                result.append((kw, result_dict[kw]))
        return result


@dataclass
class NNCHead:
    """
    The NNCHead keyword denotes the start of a
    NNCSection and contains the number of nncs and
    the grid number of the grid where the NNCs applies.
    """

    num_nnc: int
    grid_identifier: int

    @classmethod
    def from_ecl(cls, values: List[int]):
        return cls(*values[0:2])

    def to_ecl(self) -> np.ndarray:
        result = np.zeros((10,), dtype=np.int32)
        result[0] = self.num_nnc
        result[1] = self.grid_identifier
        return result


@dataclass
class NNCSection:
    """The NNCSection's describe non-neighboor connections in the grid.

    See, for instance, OPM user manual 2021-4 Rev. 1 Table D1.1 and 6.3.5.

    Args:
        nnchead: The nnc header
        upstream_nnc: list of cells (by index) for the upstream nnc.
        downstream_nnc: list of cells (by index) for the downstream nnc
            to be connected to the corresponding cell in upstream_nnc.
        nncl: list of LGR cells (by index) to be connected to the global grid.
        nncg: list of global cells (by index) connected to the corresponding
         LGR cells in nncl.

    """

    nnchead: NNCHead
    upstream_nnc: np.ndarray
    downstream_nnc: np.ndarray
    nncl: Optional[np.ndarray] = None
    nncg: Optional[np.ndarray] = None

    def __eq__(self, other):
        if not isinstance(other, NNCSection):
            return False
        return (
            self.nnchead == other.nnchead
            and np.array_equal(self.upstream_nnc, other.upstream_nnc)
            and np.array_equal(self.downstream_nnc, other.downstream_nnc)
            and np.array_equal(self.nncl, other.nncl)
            and np.array_equal(self.nncg, other.nncg)
        )

    def to_ecl(self) -> List[Tuple[str, Any]]:
        result = [
            ("NNCHEAD ", self.nnchead.to_ecl()),
            ("NNC1    ", self.upstream_nnc),
            ("NNC2    ", self.downstream_nnc),
        ]
        if self.nncl is not None:
            result.append(("NNCL    ", self.nncl))
        if self.nncg is not None:
            result.append(("NNCG    ", self.nncg))
        return result


@dataclass
class AmalgamationSection:
    """The AmalgamationSection's describe the amalgamation of two LGR's.

    See, for instance, OPM user manual 2021-4 Rev. 1 Table D1.1 and 6.3.5.

    Args:
    lgr_idxs: The indexes of the LGR's to be amalgamated
    nna1: indecies in the first lgr connected in the amalgamation.
    nna2: indecies in the second lgr connected in the amalgamation, to
        the corresponding cell in nna1.

    """

    lgr_idxs: Tuple[int, int]
    nna1: Optional[np.ndarray]
    nna2: Optional[np.ndarray]

    def __eq__(self, other):
        if not isinstance(other, AmalgamationSection):
            return False
        return (
            self.lgr_idxs == other.lgr_idxs
            and np.array_equal(self.nna1, other.nna1)
            and np.array_equal(self.nna2, other.nna2)
        )

    def to_ecl(self) -> List[Tuple[str, Any]]:
        return [
            ("NNCHEADA", np.array(self.lgr_idxs, np.int32)),
            ("NNA1    ", self.nna1),
            ("NNA2    ", self.nna2),
        ]


@dataclass
class EGridHead:
    """The EGridHead section occurs once at the start of an EGrid file."""

    file_head: Filehead
    mapunits: Optional[Units] = None
    mapaxes: Optional[MapAxes] = None
    gridunit: Optional[GridUnit] = None
    gdorient: Optional[GdOrient] = None

    def to_ecl(self) -> List[Tuple[str, Any]]:
        result = [
            ("FILEHEAD", self.file_head.to_ecl()),
        ]
        if self.mapunits is not None:
            result.append(("MAPUNITS", [self.mapunits.to_ecl()]))
        if self.mapaxes is not None:
            result.append(("MAPAXES ", self.mapaxes.to_ecl()))
        if self.gridunit is not None:
            result.append(("GRIDUNIT", self.gridunit.to_ecl()))
        if self.gdorient is not None:
            result.append(("GDORIENT", self.gdorient.to_ecl()))
        return result


@dataclass
class EGrid:
    """Contains all the data of an EGRID file.

    Args:
        egrid_head: The file header starting with the FILEHEAD keyword and
            contains optional information about units, map relative location, and
            orientation.
        global_grid: The global grid
        lgr_sections: List of local grid refinements.
        nnc_sections: Describe non-neighboring sections as a list of either
            NNCSections or AmalgamationSection's.
    """

    egrid_head: EGridHead
    global_grid: GlobalGrid
    lgr_sections: List[LGRSection]
    # The nnc_sections are kept as one list which can consist of both
    # NNCSection and AmalgamationSection as these occur interspersed in the
    # file. The order seems to be sorted by LGR index. Keeping them in
    # one list keeps the data layout of EGrid 1-to-1 with the contents
    # of the file.
    nnc_sections: List[Union[NNCSection, AmalgamationSection]]

    @classmethod
    def default_settings_grid(
        cls,
        coord: np.ndarray,
        zcorn: np.ndarray,
        actnum: Optional[np.ndarray],
        size: Tuple[int, int, int],
    ):
        grid_head = GridHead(
            TypeOfGrid.CORNER_POINT,
            *size,
            1,
            1,
            1,
            CoordinateType.CARTESIAN,
            (0, 0, 0),
            (0, 0, 0),
        )
        global_grid = GlobalGrid(
            grid_head,
            coord,
            zcorn,
            actnum,
        )
        return EGrid(
            EGridHead(
                Filehead(
                    3,
                    2007,
                    3,
                    TypeOfGrid.CORNER_POINT,
                    RockModel.SINGLE_PERMEABILITY_POROSITY,
                    GridFormat.IRREGULAR_CORNER_POINT,
                ),
                gridunit=GridUnit(),
            ),
            global_grid,
            [],
            [],
        )

    @classmethod
    def from_file(cls, filelike, fileformat: str = None):
        """
        Read an egrid file
        Args:
            filelike (str,Path,stream): The egrid file to be read.
            file_format (None or str): The format of the file (either "egrid"
                or "fegrid") None means guess.
        Returns:
            EGrid with the contents of the file.
        """
        file_format = None
        if fileformat == "egrid":
            file_format = Format.UNFORMATTED
        elif fileformat == "fegrid":
            file_format = Format.FORMATTED
        elif fileformat is not None:
            raise ValueError(f"Unrecognized egrid file format {fileformat}")
        return EGridReader(filelike, file_format=file_format).read()

    def to_file(self, filelike, fileformat: str = "egrid"):
        """
        write the EGrid to file.
        Args:
            filelike (str,Path,stream): The egrid file to write to.
            file_format (ecl_data_io.Format): The format of the file.
        """
        file_format = None
        if fileformat == "egrid":
            file_format = Format.UNFORMATTED
        elif fileformat == "fegrid":
            file_format = Format.FORMATTED
        elif fileformat is not None:
            raise ValueError(f"Unrecognized egrid file format {fileformat}")
        contents = []
        contents += self.egrid_head.to_ecl()
        contents += self.global_grid.to_ecl()
        for lgr in self.lgr_sections:
            contents += lgr.to_ecl()
        for nnc in self.nnc_sections:
            contents += nnc.to_ecl()
        write(filelike, contents, file_format)


keyword_translation = {
    "FILEHEAD": "file_head",
    "MAPUNITS": "mapunits",
    "MAPAXES ": "mapaxes",
    "GRIDUNIT": "gridunit",
    "GDORIENT": "gdorient",
    "LGR     ": "name",
    "GRIDHEAD": "grid_head",
    "HOSTNUM ": "hostnum",
    "BOXORIG ": "boxorig",
    "COORDSYS": "coord_sys",
    "LGRPARNT": "parent",
    "LGRSGRID": "grid_parent",
    "COORD   ": "coord",
    "ZCORN   ": "zcorn",
    "ACTNUM  ": "actnum",
    "NNCHEAD ": "nnchead",
    "NNC1    ": "upstream_nnc",
    "NNC2    ": "downstream_nnc",
    "NNCL    ": "nncl",
    "NNCG    ": "nncg",
    "NNCHEADA": "lgr_idxs",
    "NNA1    ": "nna1",
    "NNA2    ": "nna2",
    "CORSNUM ": "corsnum",
}


class EGridReader:
    """
    The EGridReader reads an egrid file through the `read` method.

    Args:
        filelike (str, Path, stream): The egrid file to read from.
        file_format (None or ecl_data_io.Format): The format of the file,
            None means guess.

    """

    def __init__(self, filelike, file_format: Format = None):
        self.filelike = filelike
        self.keyword_generator = lazy_read(filelike, file_format)

    def read_section(
        self,
        keyword_factories: Dict[str, Callable],
        required_keywords: Set[str],
        stop_keywords: Iterable[str],
        skip_keywords: Iterable[str] = [],
        keyword_visitors: Iterable[Callable] = [],
    ):
        """
        Read a general egrid file section.
        Args:
            keyword_factories (dict[str, func]): The function used
                to construct a section member.
            required_keywords (List[str]): List of keywords that are required
                for the given section.
            stop_keywords (List[str]): List of keywords which when read ends
                the section. The keyword generator will be at the first keyword
                in stop_keywords after read_section is called.
            skip_keywords (List[str]): List of keywords that does not
                have a factory, which should just be skipped.
            keyword_visitors (List[func]): List of functions that
                "visit" each keyword. Each of these functions are called
                for each keyword, value pair and can be used to
                preprocess the data.

        Returns:
            dictionary of parameters for the constructor of the given section.
        """
        results = {}
        i = 0
        while True:
            try:
                entry = next(self.keyword_generator)
            except StopIteration:
                break
            kw = entry.read_keyword()
            if kw in skip_keywords:
                continue
            if kw in stop_keywords and i > 0:
                # Optional keywords were possibly omitted and
                # we have reached the global grid section
                # push back the grid head of the global grid
                # and proceed
                self.keyword_generator = chain([entry], self.keyword_generator)
                break
            if kw in results:
                raise EGridFileFormatError(f"Duplicate keyword {kw} in {self.filelike}")
            try:
                factory = keyword_factories[kw]
            except KeyError as err:
                raise EGridFileFormatError(f"Unknown egrid keyword {kw}") from err
            try:
                value = factory(entry.read_array())
                results[kw] = value
            except (ValueError, IndexError, TypeError) as err:
                raise EGridFileFormatError(f"Incorrect values in keyword {kw}") from err
            for visit in keyword_visitors:
                visit(kw, value)
            i += 1

        missing_keywords = required_keywords.difference(results.keys())
        params = {keyword_translation[kw]: v for kw, v in results.items()}
        if missing_keywords:
            raise EGridFileFormatError(f"Missing required keywords {missing_keywords}")
        return params

    def read_header(self) -> EGridHead:
        """
        Reads the EGrid header from the start of the stream. Ensures
        that the keyword_generator is at the first GRIDHEAD keyword
        after the header.
        """
        params = self.read_section(
            keyword_factories={
                "FILEHEAD": Filehead.from_ecl,
                "MAPUNITS": lambda x: Units.from_ecl(x[0]),
                "MAPAXES ": MapAxes.from_ecl,
                "GRIDUNIT": GridUnit.from_ecl,
                "GDORIENT": GdOrient.from_ecl,
            },
            required_keywords={"FILEHEAD"},
            stop_keywords=["GRIDHEAD"],
        )
        return EGridHead(**params)

    def read_global_grid(self) -> GlobalGrid:
        """
        Reads the global grid section from the start of the keyword_generator,
        ensures the keyword_generator is at the keyword after the first ENDGRID
        keyword encountered.
        """

        def check_gridhead(kw: str, value):
            if kw == "GRIDHEAD" and value.type_of_grid != TypeOfGrid.CORNER_POINT:
                raise NotImplementedError(
                    "XTGeo does not support unstructured or mixed grids."
                )

        params = self.read_section(
            keyword_factories={
                "GRIDHEAD": GridHead.from_ecl,
                "BOXORIG ": tuple,
                "COORDSYS": MapAxes.from_ecl,
                "COORD   ": lambda x: np.array(x, dtype=np.float32),
                "ZCORN   ": lambda x: np.array(x, dtype=np.float32),
                "ACTNUM  ": lambda x: np.array(x, dtype=np.int32),
                "CORSNUM ": lambda x: np.array(x, dtype=np.int32),
            },
            required_keywords={"GRIDHEAD", "COORD   ", "ZCORN   "},
            stop_keywords=["ENDGRID "],
            keyword_visitors=[check_gridhead],
        )
        try:
            entry = next(self.keyword_generator)
        except StopIteration as err:
            raise EGridFileFormatError(
                "Did not read ENDGRID after global grid"
            ) from err
        if entry.read_keyword() != "ENDGRID ":
            raise EGridFileFormatError("Did not read ENDGRID after global grid")
        return GlobalGrid(**params)

    def read_subsections(self) -> Tuple[List[LGRSection], List[NNCSection]]:
        """
        Reads lgr and nnc subsections from the start of the keyword_generator.
        """
        lgr_sections = []
        nnc_sections = []
        while True:
            try:
                entry = next(self.keyword_generator)
            except StopIteration:
                break
            self.keyword_generator = chain([entry], self.keyword_generator)
            keyword = entry.read_keyword().rstrip()
            if keyword == "LGR":
                lgr_sections.append(self.read_lgr_subsection())
            elif keyword == "NNCHEAD":
                nnc_sections.append(self.read_nnc_subsection())
            elif keyword == "NNCHEADA":
                nnc_sections.append(self.read_amalgamation_subsection())
            else:
                raise EGridFileFormatError(
                    f"egrid subsection started with unexpected keyword {keyword}"
                )
        return lgr_sections, nnc_sections

    def read_lgr_subsection(self) -> LGRSection:
        """
        Reads one lgr subsection from the start of the keyword generator.
        After read_lgr_subsection is called, The keyword_generator is at the
        keyword after the first ENDLGR keyword encountered, or end of stream.
        """
        params = self.read_section(
            keyword_factories={
                "LGR     ": lambda x: x[0].decode("ascii"),
                "LGRPARNT": lambda x: x[0].decode("ascii"),
                "LGRSGRID": lambda x: x[0].decode("ascii"),
                "GRIDHEAD": GridHead.from_ecl,
                "BOXORIG ": tuple,
                "COORDSYS": MapAxes.from_ecl,
                "COORD   ": lambda x: np.array(x, dtype=np.float32),
                "ZCORN   ": lambda x: np.array(x, dtype=np.float32),
                "ACTNUM  ": lambda x: np.array(x, dtype=np.int32),
                "HOSTNUM ": lambda x: np.array(x, dtype=np.int32),
            },
            required_keywords={
                "LGR     ",
                "GRIDHEAD",
                "COORD   ",
                "ZCORN   ",
                "HOSTNUM ",
            },
            skip_keywords=["ENDGRID "],
            stop_keywords=["ENDLGR  "],
        )
        try:
            entry = next(self.keyword_generator)
        except StopIteration as err:
            raise EGridFileFormatError("Did not read ENDLGR after lgr section") from err
        if entry.read_keyword() != "ENDLGR  ":
            raise EGridFileFormatError("Did not read ENDLGR after lgr section")
        return LGRSection(**params)

    def read_nnc_subsection(self) -> NNCSection:
        """
        Reads one nnc subsection from the start of the keyword generator.
        After read_nncsubsection is called, The keyword_generator is
        at the next NNCHEAD, NNCHEADA or LGR keyword, or end of stream.
        """
        params = self.read_section(
            keyword_factories={
                "NNCHEAD ": NNCHead.from_ecl,
                "NNC1    ": lambda x: np.array(x, dtype=np.int32),
                "NNC2    ": lambda x: np.array(x, dtype=np.int32),
                "NNCL    ": lambda x: np.array(x, dtype=np.int32),
                "NNCG    ": lambda x: np.array(x, dtype=np.int32),
            },
            required_keywords={"NNCHEAD ", "NNC1    ", "NNC2    "},
            stop_keywords=["NNCHEAD ", "LGR     ", "NNCHEADA"],
        )
        return NNCSection(**params)

    def read_amalgamation_subsection(self) -> AmalgamationSection:
        """
        Reads one amalgamation subsection from the start of the keyword
        generator. After read_nncsubsection is called, The keyword_generator is
        at the next NNCHEAD, NNCHEADA or LGR keyword, or end of stream.
        """
        params = self.read_section(
            keyword_factories={
                "NNCHEADA": lambda x: tuple(x[0:2]),
                "NNA1    ": lambda x: np.array(x, dtype=np.int32),
                "NNA2    ": lambda x: np.array(x, dtype=np.int32),
            },
            required_keywords={"NNCHEADA", "NNA1    ", "NNA2    "},
            stop_keywords=["NNCHEAD ", "LGR     ", "NNCHEADA"],
        )
        return AmalgamationSection(**params)

    def read(self) -> EGrid:
        header = self.read_header()
        if header.file_head.type_of_grid != TypeOfGrid.CORNER_POINT:
            raise NotImplementedError(
                "XTGeo does not support unstructured or mixed grids."
            )
        global_grid = self.read_global_grid()
        lgr_sections, nnc_sections = self.read_subsections()
        return EGrid(header, global_grid, lgr_sections, nnc_sections)
