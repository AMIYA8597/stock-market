from pathlib import Path


FORBIDDEN_MARKERS = (
    "api.upstox.com/v2/order",
    "TRADING_MODE",
    "guest-user",
)


def test_production_code_contains_no_live_trading_markers() -> None:
    app_dir = Path(__file__).parents[1] / "app"
    matches = [
        f"{path}:{marker}"
        for path in app_dir.rglob("*.py")
        for marker in FORBIDDEN_MARKERS
        if marker.lower() in path.read_text(encoding="utf-8").lower()
    ]
    assert not matches, "Retired trading markers found: " + ", ".join(matches)
