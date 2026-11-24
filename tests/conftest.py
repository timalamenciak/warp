"""Shared fixtures for the WARP test suite.

The scripts in scripts/ are plain modules that import each other by name, so
the directory goes on sys.path here rather than being packaged.
"""

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
SCHEMA = ROOT / "src" / "warp" / "schema" / "warp.yaml"
EXAMPLES = ROOT / "examples"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load_yaml(path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


@pytest.fixture(scope="session")
def schemaview():
    from linkml_runtime.utils.schemaview import SchemaView
    return SchemaView(str(SCHEMA))


@pytest.fixture(scope="session")
def validator(schemaview):
    """A LinkML validator built once per session (loading the schema is the slow part)."""
    from linkml.validator import Validator
    from linkml.validator.plugins import JsonschemaValidationPlugin
    return Validator(schemaview.schema, validation_plugins=[JsonschemaValidationPlugin(closed=True)])
