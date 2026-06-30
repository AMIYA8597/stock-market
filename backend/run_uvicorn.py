#!/usr/bin/env python

"""
Run the FastAPI application with the correct import path so that modules like `app.api` resolve correctly.

Usage:
    python backend/run_uvicorn.py

This script adds the project root to `sys.path` before invoking uvicorn.
"""

import os
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Add the project root (where the `app` package lives) to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ""))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True, reload_dirs=[os.path.join(project_root, "app")])
