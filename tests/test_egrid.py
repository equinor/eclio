import io

import ecl_data_io as eclio
import eclio.egrid as egrid
import hypothesis.strategies as st
import numpy as np
import pytest
from hypothesis import HealthCheck, assume, given, settings

from .egrid_generator import egrids, lgr_sections


@pytest.mark.parametrize(
    "file_contents, bad_keyword",
    [
        ({"FILEHEAD": []}, "FILEHEAD"),
        (
            {
                "FILEHEAD": np.zeros((100,), dtype=np.int32),
                "MAPUNITS": [],
            },
            "MAPUNITS",
        ),
        (
            {
                "FILEHEAD": np.zeros((100,), dtype=np.int32),
                "MAPAXES ": [],
            },
            "MAPAXES",
        ),
        (
            {
                "FILEHEAD": np.zeros((100,), dtype=np.int32),
                "GRIDUNIT": ["METRES  "],
                "GRIDHEAD": [],
            },
            "GRIDHEAD",
        ),
        (
            {
                "FILEHEAD": np.zeros((100,), dtype=np.int32),
                "GRIDUNIT": ["METRES  "],
                "GRIDHEAD": np.ones((100,), dtype=np.int32),
            },
            "COORD",
        ),
        (
            {
                "FILEHEAD": np.zeros((100,), dtype=np.int32),
                "GRIDUNIT": ["METRES  "],
                "GRIDHEAD": np.ones((100,), dtype=np.int32),
                "COORD   ": [],
            },
            "ZCORN",
        ),
        (
            {
                "FILEHEAD": np.zeros((100,), dtype=np.int32),
                "GRIDUNIT": ["METRES  "],
                "GRIDHEAD": np.ones((100,), dtype=np.int32),
                "COORD   ": [],
                "ZCORN   ": [],
                "ACTNUM  ": [],
            },
            "ENDGRID",
        ),
        (
            {
                "FILEHEAD": np.zeros((100,), dtype=np.int32),
                "GRIDUNIT": ["METRES  "],
                "GRIDHEAD": np.ones((100,), dtype=np.int32),
                "COORD   ": [],
                "ZCORN   ": [],
                "ACTNUM  ": [],
                "ENDGRID ": [],
                "NNCHEAD ": [],
            },
            "NNCHEAD",
        ),
        (
            {
                "FILEHEAD": np.zeros((100,), dtype=np.int32),
                "GRIDUNIT": ["METRES  "],
                "GRIDHEAD": np.ones((100,), dtype=np.int32),
                "COORD   ": [],
                "ZCORN   ": [],
                "ACTNUM  ": [],
                "ENDGRID ": [],
                "NNCHEAD ": np.array([1, 0], dtype=np.int32),
            },
            "NNC1",
        ),
        (
            {
                "FILEHEAD": np.zeros((100,), dtype=np.int32),
                "GRIDUNIT": ["METRES  "],
                "GRIDHEAD": np.ones((100,), dtype=np.int32),
                "COORD   ": [],
                "ZCORN   ": [],
                "ACTNUM  ": [],
                "ENDGRID ": [],
                "NNCHEAD ": np.array([1, 0], dtype=np.int32),
                "NNC1    ": [],
            },
            "NNC2",
        ),
        (
            {
                "FILEHEAD": np.zeros((100,), dtype=np.int32),
                "GRIDUNIT": ["METRES  "],
                "GRIDHEAD": np.ones((100,), dtype=np.int32),
                "COORD   ": [],
                "ZCORN   ": [],
                "ACTNUM  ": [],
                "ENDGRID ": [],
                "LGR     ": [],
            },
            "LGR",
        ),
        (
            {
                "FILEHEAD": np.zeros((100,), dtype=np.int32),
                "GRIDUNIT": ["METRES  "],
                "GRIDHEAD": np.ones((100,), dtype=np.int32),
                "COORD   ": [],
                "ZCORN   ": [],
                "ACTNUM  ": [],
                "ENDGRID ": [],
                "LGR     ": ["name"],
            },
            "GRIDHEAD",
        ),
        (
            [
                ("FILEHEAD", np.zeros((100,), dtype=np.int32)),
                ("GRIDUNIT", ["METRES  "]),
                ("GRIDHEAD", np.ones((100,), dtype=np.int32)),
                ("COORD   ", []),
                ("ZCORN   ", []),
                ("ACTNUM  ", []),
                ("ENDGRID ", []),
                ("LGR     ", ["name"]),
                ("GRIDHEAD", np.ones((100,), dtype=np.int32)),
            ],
            "COORD",
        ),
        (
            [
                ("FILEHEAD", np.zeros((100,), dtype=np.int32)),
                ("GRIDUNIT", ["METRES  "]),
                ("GRIDHEAD", np.ones((100,), dtype=np.int32)),
                ("COORD   ", []),
                ("ZCORN   ", []),
                ("ACTNUM  ", []),
                ("ENDGRID ", []),
                ("LGR     ", ["name"]),
                ("GRIDHEAD", np.ones((100,), dtype=np.int32)),
                ("COORD   ", []),
            ],
            "ZCORN",
        ),
        (
            [
                ("FILEHEAD", np.zeros((100,), dtype=np.int32)),
                ("GRIDUNIT", ["METRES  "]),
                ("GRIDHEAD", np.ones((100,), dtype=np.int32)),
                ("COORD   ", []),
                ("ZCORN   ", []),
                ("ACTNUM  ", []),
                ("ENDGRID ", []),
                ("LGR     ", ["name"]),
                ("GRIDHEAD", np.ones((100,), dtype=np.int32)),
                ("COORD   ", []),
                ("ZCORN   ", []),
                ("HOSTNUM ", []),
            ],
            "ENDLGR",
        ),
    ],
)
def test_bad_keywords_raises(file_contents, bad_keyword):
    buf = io.BytesIO()
    eclio.write(buf, file_contents)
    buf.seek(0)
    with pytest.raises(egrid.EGridFileFormatError, match=bad_keyword):
        egrid.EGrid.from_file(buf)


@pytest.mark.parametrize("egrid_type_value", [0, 1, 2])
def test_to_from_filehead_type(egrid_type_value):
    values = np.zeros((100,), dtype=np.int32)
    values[4] = egrid_type_value
    assert egrid.Filehead.from_ecl(values).to_ecl()[4] == egrid_type_value


@given(
    st.sampled_from(egrid.TypeOfGrid),
    st.sampled_from(egrid.RockModel),
    st.sampled_from(egrid.GridFormat),
)
def test_from_to_filehead_type(type_of_grid, rock_model, grid_format):
    filehead = egrid.Filehead(3, 2007, 2, type_of_grid, rock_model, grid_format)
    filehead_roundtrip = egrid.Filehead.from_ecl(filehead.to_ecl())

    assert filehead_roundtrip.year == 2007
    assert filehead_roundtrip.version_number == 3
    assert filehead_roundtrip.version_bound == 2
    assert filehead_roundtrip.type_of_grid == type_of_grid
    assert filehead_roundtrip.rock_model == rock_model
    assert filehead_roundtrip.grid_format == grid_format


def test_type_of_grid_error():
    with pytest.raises(ValueError, match="grid type"):
        egrid.Filehead.from_ecl([3, 2007, 0, 2, 4, 0, 0])


def test_file_head_error():
    with pytest.raises(ValueError, match="too few values"):
        egrid.Filehead.from_ecl([])


def test_grid_head_error():
    with pytest.raises(ValueError, match="Too few arguments"):
        egrid.GridHead.from_ecl([])


def test_read_duplicate_keyword_error():
    buf = io.BytesIO()
    eclio.write(buf, [("FILEHEAD", np.zeros((100,), dtype=np.int32))] * 2)
    buf.seek(0)
    reader = egrid.EGridReader(buf)

    with pytest.raises(egrid.EGridFileFormatError, match="Duplicate"):
        reader.read()


def test_read_bad_keyword_error():
    buf = io.BytesIO()
    eclio.write(buf, [("NTKEYWRD", np.zeros((100,), dtype=np.int32))] * 2)
    buf.seek(0)
    reader = egrid.EGridReader(buf)

    with pytest.raises(egrid.EGridFileFormatError, match="Unknown egrid keyword"):
        reader.read()


def test_read_mixed_gridhead():
    buf = io.BytesIO()
    eclio.write(
        buf,
        [
            ("FILEHEAD", np.zeros((100,), dtype=np.int32)),
            ("GRIDUNIT", ["METRES  ", "MAP     "]),
            ("GRIDHEAD", 2 * np.ones((100,), dtype=np.int32)),
        ],
    )
    buf.seek(0)
    reader = egrid.EGridReader(buf)

    with pytest.raises(NotImplementedError, match="unstructured"):
        reader.read()


def test_read_no_endgrid():
    buf = io.BytesIO()
    eclio.write(
        buf,
        [
            ("FILEHEAD", np.zeros((100,), dtype=np.int32)),
            ("GRIDUNIT", ["METRES  ", "MAP     "]),
            ("GRIDHEAD", np.ones((100,), dtype=np.int32)),
            ("ZCORN   ", np.ones((8,), dtype=np.int32)),
            ("COORD   ", np.ones((4,), dtype=np.int32)),
        ],
    )
    buf.seek(0)
    reader = egrid.EGridReader(buf)

    with pytest.raises(egrid.EGridFileFormatError, match="ENDGRID"):
        reader.read()


def test_read_unexpected_section():
    buf = io.BytesIO()
    eclio.write(
        buf,
        [
            ("FILEHEAD", np.zeros((100,), dtype=np.int32)),
            ("GRIDUNIT", ["METRES  ", "MAP     "]),
            ("GRIDHEAD", np.ones((100,), dtype=np.int32)),
            ("ZCORN   ", np.ones((8,), dtype=np.int32)),
            ("COORD   ", np.ones((4,), dtype=np.int32)),
            ("ENDGRID ", []),
            ("SECTION ", []),
        ],
    )
    buf.seek(0)
    reader = egrid.EGridReader(buf)

    with pytest.raises(
        egrid.EGridFileFormatError, match="subsection started with unexpected"
    ):
        reader.read()


def test_read_multiple_amalgamations():
    buf = io.BytesIO()
    eclio.write(
        buf,
        [
            ("FILEHEAD", np.zeros((100,), dtype=np.int32)),
            ("GRIDUNIT", ["METRES  ", "MAP     "]),
            ("GRIDHEAD", np.ones((100,), dtype=np.int32)),
            ("ZCORN   ", np.ones((8,), dtype=np.int32)),
            ("COORD   ", np.ones((4,), dtype=np.int32)),
            ("ENDGRID ", []),
            ("NNCHEADA", [1, 2]),
            ("NNA1    ", []),
            ("NNA2    ", []),
            ("NNCHEADA", [1, 3]),
            ("NNA1    ", []),
            ("NNA2    ", []),
        ],
    )
    buf.seek(0)
    reader = egrid.EGridReader(buf)
    grid = reader.read()
    assert len(grid.nnc_sections) == 2
