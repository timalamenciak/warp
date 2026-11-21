"""Proposition IDs of the worked examples must not move without a reason.

Every phase of the 0.4 work promises that groups which declare no identity
extras keep their proposition IDs (decision D4). These are the IDs as of
0.5.0. If one changes, the change must be deliberate, explained in
CHANGELOG.md, and this list updated in the same commit.
"""

import copy

import pytest

from conftest import EXAMPLES, SCHEMA, load_yaml

EXPECTED = {
    "bloodroot_statements": {
        "causal_propositions": {"warp:prop/aea4ac8269ae", "warp:prop/question-bloodroot-garlic-mustard"},
        "interaction_propositions": {"warp:prop/6ac6fc0d7703"},
    },
    "kramer1995_statements": {
        "causal_propositions": {"warp:prop/9f0b068ca33b", "warp:prop/question-tidal-restoration-aedes-dorsalis"},
    },
}


def derive(name):
    import derive_propositions as dp
    data = load_yaml(EXAMPLES / f"{name}.yaml")
    groups = dp.load_groups(SCHEMA)
    node_names = {n["id"]: n.get("name", n["id"]) for n in data.get("nodes") or []}
    for g in groups:
        dp.derive_group(data, g, node_names)
    return data


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_proposition_ids_are_stable(name):
    data = derive(name)
    for slot, ids in EXPECTED[name].items():
        assert {p["id"] for p in data.get(slot) or []} == ids


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_committed_derived_file_is_current(name):
    """examples/*.derived.yaml is what derivation produces today."""
    fresh = derive(name)
    committed = load_yaml(EXAMPLES / f"{name}.derived.yaml")
    for slot in EXPECTED[name]:
        assert copy.deepcopy(fresh.get(slot)) == committed.get(slot), f"re-run make derive ({slot})"


INPUTS = sorted(p for p in EXAMPLES.glob("*_statements.yaml"))


@pytest.mark.parametrize("path", INPUTS, ids=lambda p: p.name)
def test_every_derived_file_is_current(schemaview, path):
    """Every committed *.derived.yaml is exactly what make derive produces:
    strategies first, then propositions, then projects."""
    import derive_projects as dpj
    import derive_strategies as ds
    import derive_propositions as dp
    derived = path.with_name(path.stem + ".derived.yaml")
    assert derived.exists(), f"missing {derived.name}: run make derive"
    committed = load_yaml(derived)
    fresh = load_yaml(path)
    ds.derive(fresh, schemaview, previous=committed)
    dp.derive_all(fresh, SCHEMA)
    dpj.derive(fresh, previous=committed)
    assert fresh == committed, f"{derived.name} is stale: run make derive"
