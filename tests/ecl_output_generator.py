import hypothesis.strategies as st
import numpy as np
from eclio.ecl_output_file import (
    CoordinateType,
    GdOrient,
    GridRelative,
    GridUnit,
    Handedness,
    MapAxes,
    Order,
    Orientation,
    TypeOfGrid,
    Units,
)

finites = st.floats(
    min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False, width=32
)
units = st.sampled_from(Units)
grid_relatives = st.sampled_from(GridRelative)
orders = st.sampled_from(Order)
orientations = st.sampled_from(Orientation)
handedness = st.sampled_from(Handedness)
coordinate_types = st.sampled_from(CoordinateType)
gdorients = st.builds(GdOrient, orders, orders, orders, orientations, handedness)
types_of_grid = st.just(TypeOfGrid.CORNER_POINT)


@st.composite
def gridunits(draw, relative=grid_relatives):
    return draw(st.builds(GridUnit, units, relative))


def valid_mapaxes(mapaxes: MapAxes) -> bool:
    y_line = mapaxes.y_line
    x_line = mapaxes.x_line
    origin = mapaxes.origin
    x_axis = np.array(x_line) - origin
    y_axis = np.array(y_line) - origin

    return np.linalg.norm(x_axis) > 1e-5 and np.linalg.norm(y_axis) > 1e-5


map_axes = st.builds(
    MapAxes,
    st.tuples(finites, finites),
    st.tuples(finites, finites),
    st.tuples(finites, finites),
).filter(valid_mapaxes)
