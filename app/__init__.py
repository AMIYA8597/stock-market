# Package alias for 'app' to point to the backend implementation.
import os
import sys

# Determine the absolute path to the backend/app directory.
_current_dir = os.path.abspath(os.path.dirname(__file__))
_backend_app_path = os.path.abspath(os.path.join(_current_dir, "..", "backend", "app"))

# Insert this path at the start of sys.path if not already present.
if _backend_app_path not in sys.path:
    sys.path.insert(0, _backend_app_path)

# Extend the package __path__ so submodule imports resolve correctly.
__path__.append(_backend_app_path)
