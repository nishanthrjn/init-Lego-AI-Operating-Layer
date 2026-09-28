"""The runnable example is a consumer of the public API only."""

import pytest
import station_reading


def test_example_output(capsys: pytest.CaptureFixture[str]) -> None:
    station_reading.main()
    assert capsys.readouterr().out.splitlines() == [
        "agreed selected=4.2 disagreement=no values=4.2",
        "precedence_selected selected=4.2 disagreement=yes values=4.2,4.6",
        "feed-a rank=0 raw=4.20 admissible",
        "feed-b rank=1 raw=4.6 admissible",
        "feed-c rank=none raw=4.4 unranked_source",
    ]
