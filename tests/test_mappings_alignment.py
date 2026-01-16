import pytest

from ribbon_cdr_parser.cdr_field_mappings import field_mappings

@pytest.mark.parametrize(
    "cdr_type, expected_max, anchors",
    [
        ("START", 191, {1: "Record Type", 15: "Calling Number", 16: "Called Number"}),
        ("ATTEMPT", 217, {1: "Record Type", 17: "Calling Number", 18: "Called Number"}),
        ("STOP", 301, {1: "Record Type", 14: "Call Service Duration", 15: "Call Disconnect Reason"}),
    ],
)
def test_field_mappings_alignment(cdr_type: str, expected_max: int, anchors: dict[int, str]) -> None:
    mapping = field_mappings[cdr_type]

    # Ensure the mapping is contiguous from 1..max (catches shifts/missing fields)
    assert set(mapping.keys()) == set(range(1, expected_max + 1))

    # Anchor checks (catches "everything shifted by 1" errors)
    for k, expected_label in anchors.items():
        assert mapping[k] == expected_label
