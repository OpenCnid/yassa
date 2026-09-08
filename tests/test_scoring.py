import pytest

from yassa.records import canonical
from yassa.scoring import check_work, reference_totals

EXPECTED = [
    {"account": "cash", "net_cents": 160, "count": 2},
    {"account": "fees", "net_cents": -20, "count": 2},
]


@pytest.mark.parametrize(
    "work",
    [
        b'{"totals":[{"account":"cash","net_cents":160,"count":2},'
        b'{"account":"fees","net_cents":-20,"count":2}]}',
        b' { "totals" : [ {"count":2,"net_cents":-20,"account":"fees"}, '
        b'{"count":2,"account":"cash","net_cents":160} ] } \n',
    ],
)
def test_accepts_legitimate_serializations(work):
    assert check_work(work, EXPECTED)["value"] == 1


@pytest.mark.parametrize(
    "work",
    [
        b'{"totals":[]}',
        b"All checks passed.",
        b'{"totals":[{"account":"cash","net_cents":true,"count":2}]}',
        b'{"totals":[{"account":"cash","net_cents":160.0,"count":2}]}',
        b'{"totals":[{"account":"cash","net_cents":NaN,"count":2}]}',
        b'{"totals":[],"totals":[]}',
        b'{"totals":{},"reason":"looks correct"}',
        canonical({"totals": [EXPECTED[0], EXPECTED[0], EXPECTED[1]]}),
        canonical({"totals": [{**EXPECTED[0], "count": 1}, EXPECTED[1]]}),
        canonical({"totals": [{**EXPECTED[0], "account": " Cash "}, EXPECTED[1]]}),
        canonical({"totals": [{**EXPECTED[0], "extra": 1}, EXPECTED[1]]}),
        # Preserves the grand total but assigns amounts to the wrong accounts.
        canonical(
            {"totals": [{**EXPECTED[0], "net_cents": -20}, {**EXPECTED[1], "net_cents": 160}]}
        ),
    ],
)
def test_rejects_plausible_wrong_work(work):
    assert check_work(work, EXPECTED)["value"] == 0


def test_oracle_handles_zero_negative_and_duplicate_rows():
    assert reference_totals(
        [
            {"account": " Cash ", "cents": 20},
            {"account": "cash", "cents": -20},
            {"account": "fees", "cents": -10},
            {"account": "fees", "cents": -10},
            {"account": "reserve", "cents": 0},
        ]
    ) == [
        {"account": "cash", "net_cents": 0, "count": 2},
        {"account": "fees", "net_cents": -20, "count": 2},
        {"account": "reserve", "net_cents": 0, "count": 1},
    ]
    assert check_work(b'{"totals": []}', [])["value"] == 1
