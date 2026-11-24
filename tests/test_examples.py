"""Smoke test: every example StatementSet validates against the profile."""

import pytest

from conftest import EXAMPLES, load_yaml

EXAMPLE_FILES = sorted(EXAMPLES.glob("*.yaml"))


def test_there_are_examples():
    assert EXAMPLE_FILES, "no example files found"


@pytest.mark.parametrize("path", EXAMPLE_FILES, ids=lambda p: p.name)
def test_example_validates(validator, path):
    report = validator.validate(load_yaml(path), "StatementSet")
    assert not report.results, "\n".join(r.message for r in report.results)


def test_invalid_example_is_rejected(validator):
    """The validator is really checking: a bad enum value must fail."""
    data = load_yaml(EXAMPLES / "bloodroot_statements.yaml")
    data["causal_statements"][0]["scope"] = "not-a-scope"
    report = validator.validate(data, "StatementSet")
    assert report.results
