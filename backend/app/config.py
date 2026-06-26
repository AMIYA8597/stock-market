import os

# Simple config module to expose global settings for the app
# This module is imported by services that need lightweight configuration values.

# Flag to toggle mock data usage. Defaults to true for local development.
USE_MOCK_DATA = os.getenv("USE_MOCK_DATA", "true").lower() in {"1", "true", "yes"}
