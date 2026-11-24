"""scripts/check_values.py: CURIEs, units, places, scales and dates (D18-D20)."""

import copy

import pytest

from conftest import EXAMPLES, load_yaml
from check_values import ValueChecker


@pytest.fixture(scope="module")
def checker_factory(schemaview):
    def make():
        return ValueChecker(schemaview)
    return make


def errors(checker_factory, data):
    c = checker_factory()
    c.check_set("test", data)
    return c.errors


def base():
    return copy.deepcopy(load_yaml(EXAMPLES / "bloodroot_statements.yaml"))


def with_statement(**extra):
    data = base()
    data["causal_statements"][0].update(extra)
    return data


@pytest.mark.parametrize("name", sorted(p.name for p in EXAMPLES.glob("*.yaml")))
def test_examples_are_clean(checker_factory, name):
    assert errors(checker_factory, load_yaml(EXAMPLES / name)) == []


def test_placeholder_under_real_prefix(checker_factory):
    data = base()
    data["node_definitions"][1]["fillers"][0]["value"] = "ELMO:TODO_planting"
    errs = errors(checker_factory, data)
    assert len(errs) == 1 and "real prefix 'ELMO'" in errs[0] and "TODO:planting" in errs[0]


def test_undeclared_prefix(checker_factory):
    data = base()
    data["causal_statements"][0]["subject"] = "nope:thing"
    assert any("undeclared prefix 'nope'" in e for e in errors(checker_factory, data))


def test_obo_ids_are_numeric(checker_factory):
    data = base()
    data["node_definitions"][0]["fillers"][0]["value"] = "PATO:rate"
    assert any("IDs are numeric" in e for e in errors(checker_factory, data))


@pytest.mark.parametrize("place, ok", [
    (["ISO3166-2:US-FL"], True),
    (["wd:Q812"], True),
    (["geonames:4155751"], True),
    (["place:mediterranean-coastal-israel"], True),
    (["florida-usa"], False),                 # bare token: not a CURIE
    (["node:planting_of_sanguinaria_canadensis"], False),   # not a place scheme
])
def test_place_schemes(checker_factory, place, ok):
    errs = errors(checker_factory, with_statement(place=place))
    assert (errs == []) is ok, errs


def test_unit_must_be_a_curie(checker_factory, schemaview):
    c = checker_factory()
    from warp_schema import induced_slots
    unit_slot = induced_slots(schemaview, "Quantity")["unit"]
    allowed = set("UO unit scale TODO".split())
    c.curie("q.unit", "ha", allowed)
    c.curie("q.unit", "UO:hectare", allowed)
    c.curie("q.unit", "node:x", allowed)
    c.curie("q.unit", "TODO:unit_hectare", allowed)
    c.curie("q.unit", "scale:eive-1.0-reaction", allowed)
    assert unit_slot.range == "uriorcurie"
    assert len(c.errors) == 3
    assert "not a CURIE" in c.errors[0]
    assert "numeric" in c.errors[1]
    assert "allowed here" in c.errors[2]


def test_quantity_range(checker_factory):
    c = checker_factory()
    c.quantity_range("r", {"min": 8.0, "max": 5.5, "unit": "TODO:unit_pH"})
    c.quantity_range("r", {"unit": "TODO:unit_pH"})
    c.quantity_range("r", {"min": 5.5, "unit": "TODO:unit_pH"})   # one-sided is fine
    assert len(c.errors) == 2


@pytest.mark.parametrize("value, problem", [
    ({"value": "medium", "scale": "scale:dfo-recovery-priority", "concept": "scale:dfo-recovery-priority/medium"}, None),
    ({"value": "wet"}, None),
    ({"value": "medium", "scale": "scale:no-such-scale", "concept": "scale:no-such-scale/medium"}, "not registered"),
    ({"value": "medium", "scale": "scale:dfo-recovery-priority", "concept": "scale:dfo-recovery-priority/huge"}, "not in scale"),
    ({"value": "medium", "scale": "scale:dfo-recovery-priority"}, "concept is required"),
    ({"value": "medium", "concept": "scale:dfo-recovery-priority/medium"}, "no scale"),
    ({"value": "wet", "scale": "scale:practitioner-free"}, "not a scale"),
])
def test_scaled_values(checker_factory, value, problem):
    c = checker_factory()
    c.scaled_value("v", value)
    if problem is None:
        assert c.errors == []
    else:
        assert len(c.errors) == 1 and problem in c.errors[0]


@pytest.mark.parametrize("period, ok", [
    ({"start": "2023", "end": "2024-05"}, True),
    ({"start": "2024-05"}, True),
    ({"start": "2024-05", "end": "2023"}, False),
    ({"start": "May 2024"}, False),
])
def test_periods(checker_factory, period, ok):
    c = checker_factory()
    c.period("p", period)
    assert (c.errors == []) is ok
