"""Light shim for ta-lib functions when ta-lib isn't available.

This allows the project to run on environments where compiling the C library is difficult
(e.g., Windows without conda build tools). The shim uses pandas_ta under the hood.

If the real TA-Lib library is installed, it will be used instead.
"""

try:
    import talib as _talib  # type: ignore
except ImportError:  # pragma: no cover
    _talib = None

import pandas_ta as _pandas_ta


def __getattr__(name: str):
    # Delegate to real talib if available
    if _talib is not None and hasattr(_talib, name):
        return getattr(_talib, name)

    # Delegate to pandas_ta for common functions
    # pandas_ta uses lower-case function names
    if hasattr(_pandas_ta, name.lower()):
        return getattr(_pandas_ta, name.lower())

    raise AttributeError(f"module 'talib' has no attribute '{name}'")


def __dir__():
    if _talib is not None:
        return dir(_talib)
    return dir(_pandas_ta)
