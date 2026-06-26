"""Backend package initialization. Ensures imports like 'backend.research' work when the cwd is 'backend'."""
import os, sys
_parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)
