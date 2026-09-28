"""The runnable example and the README usage are public-API consumers."""

import re
from pathlib import Path

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


def test_readme_usage_runs() -> None:
    readme = Path(__file__).resolve().parents[1] / "README.md"
    blocks = re.findall(
        r"```python\r?\n(.*?)```", readme.read_text(encoding="utf-8"), re.DOTALL
    )
    assert len(blocks) == 1
    # The block asserts its own documented outcome.
    exec(compile(blocks[0], "README.md", "exec"), {})
