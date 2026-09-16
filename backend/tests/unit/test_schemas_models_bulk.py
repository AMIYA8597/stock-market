import pytest
import importlib
import pkgutil
import app.schemas
import app.models

def test_import_all_schemas_and_models():
    for _, name, _ in pkgutil.iter_modules(app.schemas.__path__):
        importlib.import_module(f'app.schemas.{name}')
    for _, name, _ in pkgutil.iter_modules(app.models.__path__):
        importlib.import_module(f'app.models.{name}')
    assert True

