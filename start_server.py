#!/usr/bin/env python

"""
Start the FastAPI application with the correct import path.
The codebase expects the `app` package to be importable, which lives in `backend/app`.
Adding the `backend` directory to `sys.path` resolves the `ModuleNotFoundError: No module named 'app'`.

Usage:
    python start_server.py
"""
import os
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Ensure the backend directory (containing the `app` package) is on the path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
