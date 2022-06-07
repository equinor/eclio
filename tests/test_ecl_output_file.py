from hypothesis import given
from hypothesis.strategies import one_of

from .ecl_output_generator import (
    coordinate_types,
    gdorients,
    grid_relatives,
    gridunits,
    handedness,
    map_axes,
    orders,
    orientations,
    units,
)


@given(
    one_of(
        coordinate_types,
        grid_relatives,
        gridunits(),
        handedness,
        map_axes,
        orders,
        orientations,
        units,
        gdorients,
    )
)
def test_to_ecl_from_ecl_are_inverse(keyword):
    assert type(keyword).from_ecl(keyword.to_ecl())


@given(
    one_of(
        grid_relatives,
        handedness,
        orders,
        orientations,
        units,
    )
)
def test_to_ecl_from_ecl_are_inverse_bytestrings(keyword):
    assert type(keyword).from_ecl(keyword.to_ecl().encode())
