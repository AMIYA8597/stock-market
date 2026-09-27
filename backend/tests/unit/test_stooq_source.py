"""Tests for app.services.ingestion.stooq_source.StooqProvider._map_symbol.

Regression coverage for a real bug: the guard conditions were
`stooq_symbol.endswith("")` / `symbol.endswith("")`, which are always
True for any string (every string ends with the empty string). That
made _map_symbol unconditionally chop the last 3 characters off every
symbol and always append ".IN" - e.g. "RELIANCE" became "RELIAN.IN"
instead of the intended "RELIANCE.IN" for ".NS"-suffixed input.
"""

from app.services.ingestion.stooq_source import StooqProvider


def test_map_symbol_strips_ns_suffix_and_appends_in():
    provider = StooqProvider()
    assert provider._map_symbol("RELIANCE.NS") == "RELIANCE.IN"
    assert provider._map_symbol("TCS.NS") == "TCS.IN"


def test_map_symbol_does_not_corrupt_bare_ns_free_symbol():
    """A bare symbol with no dot and no .NS suffix must not be mangled by
    the (formerly unconditional) 3-character chop; it should map to the
    .US convention untouched."""
    provider = StooqProvider()
    assert provider._map_symbol("AAPL") == "AAPL.US"


def test_map_symbol_passes_through_known_indices():
    provider = StooqProvider()
    assert provider._map_symbol("^NSEI") == "^NSEI"
    assert provider._map_symbol("^BSESN") == "^BSESN"
