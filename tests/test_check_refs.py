"""scripts/check_refs.py: every non-inlined reference resolves (Phase 2)."""

import copy

import check_refs
from conftest import EXAMPLES, load_yaml


def sets(*names):
    return [(n, load_yaml(EXAMPLES / n)) for n in names]


def test_examples_resolve(schemaview):
    names = sorted(p.name for p in EXAMPLES.glob("*.yaml"))
    assert check_refs.check(schemaview, sets(*names)) == []


def test_dangling_subject_is_caught(schemaview):
    data = copy.deepcopy(load_yaml(EXAMPLES / "bloodroot_statements.yaml"))
    data["causal_statements"][0]["subject"] = "node:no_such_node"
    problems = check_refs.check(schemaview, [("x.yaml", data)])
    assert len(problems) == 1
    assert "causal_statements[0]" in problems[0] and "subject" in problems[0] and "node:no_such_node" in problems[0]


def test_dangling_contributor_in_nested_record_is_caught(schemaview):
    data = copy.deepcopy(load_yaml(EXAMPLES / "bloodroot_statements.yaml"))
    data["causal_statements"][1]["hasEvidenceLines"][0]["contributions"][0]["contributor"] = "orcid:9999"
    problems = check_refs.check(schemaview, [("x.yaml", data)])
    assert len(problems) == 1 and "contributor" in problems[0]


def test_node_definition_for_missing_node_is_caught(schemaview):
    """NodeDefinition.node is an identifier that points at a CausalNode, so it
    is checked as a reference, not counted as a definition."""
    data = copy.deepcopy(load_yaml(EXAMPLES / "bloodroot_statements.yaml"))
    data["node_definitions"][0]["node"] = "node:undeclared"
    problems = check_refs.check(schemaview, [("x.yaml", data)])
    assert any("node:undeclared" in p for p in problems)


def test_assessment_resolves_only_with_its_derived_set(schemaview):
    alone = check_refs.check(schemaview, sets("bloodroot_assessment.yaml"))
    assert any("warp:prop/question-bloodroot-garlic-mustard" in p for p in alone)
    together = check_refs.check(schemaview, sets("bloodroot_assessment.yaml", "bloodroot_statements.derived.yaml"))
    assert together == []


def test_new_reference_slots_are_checked_without_code_changes(schemaview):
    """specified_in arrived in Phase 1; check_refs covers it because it is schema-driven."""
    data = copy.deepcopy(load_yaml(EXAMPLES / "bloodroot_statements.yaml"))
    data["causal_statements"][0]["specified_in"] = ["warp:doc/no-such-plan"]
    problems = check_refs.check(schemaview, [("x.yaml", data)])
    assert len(problems) == 1 and "specified_in" in problems[0]
