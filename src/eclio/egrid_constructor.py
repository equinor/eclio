from dataclasses import dataclass
from typing import List, Optional, Tuple, Union

import numpy as np

from .ecl_output_file import (
    CoordinateType,
    GdOrient,
    GridUnit,
    MapAxes,
    TypeOfGrid,
    Units,
)
from .egrid_contents import (
    AmalgamationSection,
    EGrid,
    EGridHead,
    Filehead,
    GlobalGrid,
    GridFormat,
    GridHead,
    LGRSection,
    NNCHead,
    NNCSection,
    RockModel,
)


@dataclass
class LGR:
    coord: np.ndarray
    zcorn: np.ndarray
    start: Tuple[int, int, int]
    end: Tuple[int, int, int]
    name: str
    coordinate_type: CoordinateType = CoordinateType.CARTESIAN
    actnum: Optional[np.ndarray] = None
    coord_sys: Optional[MapAxes] = None
    corsnum: Optional[np.ndarray] = None
    parent: Optional[str] = None
    grid_parent: Optional[str] = None
    hostnum: Optional[np.ndarray] = None
    boxorig: Optional[Tuple[int, int, int]] = None


@dataclass
class NNC:
    upstream_nnc: np.ndarray
    downstream_nnc: np.ndarray
    lgr_name: Optional[str] = None
    nncl: Optional[np.ndarray] = None
    nncg: Optional[np.ndarray] = None


@dataclass
class Amalgamation:
    lgr1_name: str
    lgr2_name: str
    lgr1_cells: np.ndarray
    lgr2_cells: np.ndarray


def egrid(
    coord: np.ndarray,
    zcorn: np.ndarray,
    actnum: Optional[np.ndarray] = None,
    coordinate_type: Optional[CoordinateType] = None,
    coord_sys: Optional[MapAxes] = None,
    corsnum: Optional[np.ndarray] = None,
    boxorig: Optional[Tuple[int, int, int]] = None,
    lgrs: List[LGR] = [],
    nncs: List[Union[NNC, Amalgamation]] = [],
    type_of_grid: Optional[TypeOfGrid] = None,
    rock_model: Optional[RockModel] = None,
    grid_format: Optional[GridFormat] = None,
    mapaxes: Optional[MapAxes] = None,
    mapunits: Optional[Units] = None,
    gridunit: Optional[GridUnit] = None,
    gdorient: Optional[GdOrient] = None,
    version=3,
    version_year=2004,
    version_bound=0,
):
    if rock_model is None:
        rock_model = RockModel.SINGLE_PERMEABILITY_POROSITY
    if grid_format is None:
        grid_format = GridFormat.IRREGULAR_CORNER_POINT
    if type_of_grid is None:
        type_of_grid = TypeOfGrid.CORNER_POINT
    lgr_idxs = {}

    idx = 1
    for lgr in lgrs:
        if lgr.name not in lgr_idxs:
            lgr_idxs[lgr.name] = idx
            idx += 1

    return EGrid(
        EGridHead(
            Filehead(
                version,
                version_year,
                version_bound,
                type_of_grid,
                rock_model,
                grid_format,
            ),
            mapunits,
            mapaxes,
            gridunit,
            gdorient,
        ),
        GlobalGrid(
            GridHead(
                type_of_grid,
                zcorn.shape[0],
                zcorn.shape[2],
                zcorn.shape[4],
                0,
                1,
                1,
                coordinate_type
                if coordinate_type is not None
                else CoordinateType.CARTESIAN,
                (0, 0, 0),
                (0, 0, 0),
            ),
            coord.ravel(),
            zcorn.ravel(),
            actnum.ravel() if actnum is not None else None,
            coord_sys,
            boxorig,
            corsnum,
        ),
        [
            LGRSection(
                GridHead(
                    type_of_grid,
                    lgr.zcorn.shape[0],
                    lgr.zcorn.shape[2],
                    lgr.zcorn.shape[4],
                    0,
                    1,
                    1,
                    lgr.coordinate_type,
                    lgr.start,
                    lgr.end,
                ),
                lgr.coord.ravel(),
                lgr.zcorn.ravel(),
                lgr.name,
                lgr.actnum.ravel() if lgr.actnum is not None else None,
                lgr.parent,
                lgr.grid_parent,
                lgr.hostnum,
                lgr.boxorig,
                lgr.coord_sys,
            )
            for lgr in lgrs
        ],
        [
            NNCSection(
                NNCHead(
                    len(nnc.upstream_nnc),
                    lgr_idxs[nnc.lgr_name] if nnc.lgr_name is not None else 0,
                ),
                nnc.upstream_nnc,
                nnc.downstream_nnc,
                nnc.nncl,
                nnc.nncg,
            )
            if isinstance(nnc, NNC)
            else AmalgamationSection(
                (lgr_idxs[nnc.lgr1_name], lgr_idxs[nnc.lgr2_name]),
                nnc.lgr1_cells,
                nnc.lgr2_cells,
            )
            for nnc in nncs
        ],
    )
