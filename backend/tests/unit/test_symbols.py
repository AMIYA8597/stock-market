import json
from pathlib import Path

import pytest

from app.data_platform.symbols import normalize_symbol


def load_cases():
    cases_path = Path(__file__).parent.parent.parent.parent / "packages" / "contracts" / "symbol_cases.json"
    with open(cases_path, encoding="utf-8") as f:
        return json.load(f)

@pytest.mark.parametrize("case", load_cases())
def test_symbol_normalization(case):
    canonical, exchange = normalize_symbol(case["raw"], case["exchange_hint"])
    assert canonical == case["expected_canonical"], f"Failed canonical for {case['raw']}"
    assert exchange == case["expected_exchange"], f"Failed exchange for {case['raw']}"
