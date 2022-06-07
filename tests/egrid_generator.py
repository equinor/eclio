import eclio.egrid as eio
import hypothesis.strategies as st
import numpy as np
from hypothesis.extra.numpy import arrays

indices = st.integers(min_value=4, max_value=6)

finites = st.floats(
    min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False, width=32
)
from eclio.egrid import EGrid, GridFormat, RockModel

from .ecl_output_generator import (
    coordinate_types,
    gdorients,
    gridunits,
    map_axes,
    types_of_grid,
    units,
)


@st.composite
def zcorns(draw, dims):
    return draw(
        arrays(
            shape=8 * dims[0] * dims[1] * dims[2],
            dtype=np.float32,
            elements=finites,
        )
    )


@st.composite
def ascii_string(draw, min_size=0, max_size=8):
    size = draw(st.integers(min_value=min_size, max_value=max_size))
    result = b""
    for _ in range(size):
        # Printable non-extended ascii characters are between 32 and 126
        result += draw(st.integers(min_value=32, max_value=126)).to_bytes(1, "little")
    return result.decode("ascii")


rock_models = st.sampled_from(RockModel)
grid_formats = st.just(GridFormat.IRREGULAR_CORNER_POINT)
file_heads = st.builds(
    eio.Filehead,
    st.integers(min_value=0, max_value=5),
    st.integers(min_value=2000, max_value=2022),
    st.integers(min_value=0, max_value=5),
    types_of_grid,
    rock_models,
    grid_formats,
)


@st.composite
def grid_heads(
    draw,
    gridtype=types_of_grid,
    nx=indices,
    ny=indices,
    nz=indices,
    index=st.integers(min_value=0, max_value=5),
    coordinatesystem=coordinate_types,
):
    return eio.GridHead(
        draw(gridtype),
        draw(nx),
        draw(ny),
        draw(nz),
        draw(index),
        1,
        1,
        draw(coordinatesystem),
        draw(st.tuples(indices, indices, indices)),
        draw(st.tuples(indices, indices, indices)),
    )


@st.composite
def global_grids(draw, header=grid_heads(), zcorn=zcorns):
    grid_head = draw(header)
    dims = (grid_head.num_x, grid_head.num_y, grid_head.num_z)
    corner_size = (dims[0] + 1) * (dims[1] + 1) * 6
    coord = arrays(
        shape=corner_size,
        dtype=np.float32,
        elements=finites,
    )
    actnum = st.one_of(
        st.just(None),
        arrays(
            shape=dims[0] * dims[1] * dims[2],
            dtype=np.int32,
            elements=st.integers(min_value=0, max_value=3),
        ),
    )
    return eio.GlobalGrid(
        coord=draw(coord),
        zcorn=draw(zcorn(dims)),
        actnum=draw(actnum),
        grid_head=grid_head,
        coord_sys=draw(map_axes),
        boxorig=draw(st.tuples(indices, indices, indices)),
        corsnum=draw(
            arrays(elements=indices, dtype="int32", shape=indices),
        ),
    )


@st.composite
def lgr_sections(draw, nx=st.just(2), ny=st.just(2), nz=st.just(2), zcorn=zcorns):
    grid_head = draw(grid_heads(nx=nx, ny=ny, nz=nz))
    dims = (grid_head.num_x, grid_head.num_y, grid_head.num_z)
    corner_size = (dims[0] + 1) * (dims[1] + 1) * 6
    coord = arrays(
        shape=corner_size,
        dtype=np.float32,
        elements=finites,
    )
    actnum = st.one_of(
        st.just(None),
        arrays(
            shape=dims[0] * dims[1] * dims[2],
            dtype=np.int32,
            elements=st.integers(min_value=0, max_value=3),
        ),
    )
    return eio.LGRSection(
        coord=draw(coord),
        zcorn=draw(zcorn(dims)),
        actnum=draw(actnum),
        grid_head=grid_head,
        name=draw(ascii_string(min_size=1)),
        parent=draw(st.one_of(st.just(None), ascii_string(min_size=1))),
        grid_parent=draw(st.one_of(st.just(None), ascii_string(min_size=1))),
        hostnum=draw(arrays(elements=indices, dtype="int32", shape=indices)),
        boxorig=draw(st.tuples(indices, indices, indices)),
        coord_sys=draw(map_axes),
    )


nnc_heads = st.builds(eio.NNCHead, indices, indices)

nnc_sections = st.one_of(
    st.builds(
        eio.NNCSection,
        nnc_heads,
        arrays(elements=indices, dtype="int32", shape=st.just(2)),
        arrays(elements=indices, dtype="int32", shape=st.just(2)),
        arrays(elements=indices, dtype="int32", shape=st.just(2)),
        arrays(elements=indices, dtype="int32", shape=st.just(2)),
    ),
    st.builds(
        eio.AmalgamationSection,
        st.tuples(indices, indices),
        arrays(elements=indices, dtype="int32", shape=st.just(2)),
        arrays(elements=indices, dtype="int32", shape=st.just(2)),
    ),
)


@st.composite
def egrid_heads(draw, mpaxes=map_axes):
    return eio.EGridHead(
        draw(file_heads),
        draw(units),
        draw(mpaxes),
        draw(gridunits()),
        draw(gdorients),
    )


@st.composite
def egrids(
    draw,
    head=egrid_heads(),
    global_grid=global_grids(),
    lgrs=st.lists(lgr_sections(), max_size=2),
    nncs=st.lists(nnc_sections, max_size=2),
):
    return EGrid(draw(head), draw(global_grid), draw(lgrs), draw(nncs))
