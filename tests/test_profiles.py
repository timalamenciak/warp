"""Predicate-group profiles: scripts/subset_schema.py, config/profiles.yaml.

`make profile-check` runs the whole pipeline on every profile; these tests
cover the subsetting rules themselves and the committed outputs.
"""

import copy
from pathlib import Path

import pytest
from rdflib import URIRef
from rdflib.namespace import OWL, RDF

from conftest import EXAMPLES, ROOT, SCHEMA, load_yaml

import subset_schema as ss

CONFIG = ROOT / "config" / "profiles.yaml"
PROFILES = ROOT / "project" / "profiles"
OPTIONAL = ["strategy_definitions", "site_definitions", "criteria_sets"]
SHARED_LISTS = {"id", "profile_version", "agents", "nodes", "node_definitions",
                "assessments", "study_results", "documents"}
WARP = "https://w3id.org/ecoweaver/warp/"


@pytest.fixture(scope="module")
def schema():
    return load_yaml(SCHEMA)


def make(schema, groups, lists=(), name="test"):
    out, dropped = ss.subset(schema, name, {"groups": list(groups), "lists": list(lists)},
                             OPTIONAL, SCHEMA, PROFILES.resolve())
    return out, dropped


def test_committed_profiles_are_current(tmp_path):
    """project/profiles/ equals a fresh run of subset_schema.py."""
    ss.main([str(CONFIG), "--out-dir", str(tmp_path)])
    config = load_yaml(CONFIG)
    for name in config["profiles"]:
        for f in (f"warp_{name}.yaml", f"warp-relations_{name}.ttl"):
            fresh = (tmp_path / f).read_text(encoding="utf-8")
            committed = (PROFILES / f).read_text(encoding="utf-8")
            if f.endswith(".yaml"):
                # imports are relative to the output directory
                fresh = load_yaml(tmp_path / f)
                committed = load_yaml(PROFILES / f)
                fresh.pop("imports"), committed.pop("imports")
            assert fresh == committed, f"{f} is stale: run make profiles"


def test_every_group_and_list_gives_the_whole_schema(schema):
    """The closure misses nothing: all groups and lists keep every element."""
    out, dropped = make(schema, ss.registry(schema), OPTIONAL)
    assert dropped == []
    for k in ("classes", "enums", "slots"):
        assert set(out[k]) == set(schema[k]), k
    assert out["classes"]["StatementSet"] == schema["classes"]["StatementSet"]


def test_causal_profile_keeps_only_the_core_and_causal(schema):
    out, dropped = make(schema, ["causal"])
    assert set(out["classes"]["StatementSet"]["attributes"]) == SHARED_LISTS | {
        "causal_statements", "causal_propositions"}
    assert "CausalStatement" in out["classes"] and "SynthesisAssessment" in out["classes"]
    for gone in ("InteractionStatement", "CostStatement", "SiteDefinition", "CriteriaSet",
                 "StrategyDefinition", "MonetaryAmount"):
        assert gone not in out["classes"]
    assert "InteractionPredicateEnum" not in out["enums"]
    assert "justified_by" not in out["slots"] and "scope" in out["slots"]
    assert sorted(dropped) == sorted(set(ss.registry(schema)) - {"causal"})


def test_profile_changes_no_iri(schema):
    """Same prefixes, default prefix and element definitions as warp.yaml."""
    out, _ = make(schema, ["causal", "interaction"])
    assert out["default_prefix"] == schema["default_prefix"]
    assert out["prefixes"] == schema["prefixes"]
    for name, cls in out["classes"].items():
        if name != "StatementSet":
            assert cls == schema["classes"][name]
    assert out["version"] == schema["version"]


def test_profile_errors(schema):
    with pytest.raises(ss.ProfileError, match="unknown group"):
        make(schema, ["causal", "nonesuch"])
    with pytest.raises(ss.ProfileError, match="not optional lists"):
        make(schema, ["causal"], ["causal_statements"])
    with pytest.raises(ss.ProfileError, match="criteria_sets"):
        make(schema, ["criteria"])
    make(schema, ["criteria"], ["criteria_sets", "site_definitions"])


def test_relations_subset(schema):
    rel, removed = ss.subset_relations(ss.DEFAULT_RELATIONS, schema,
                                       sorted(set(ss.registry(schema)) - {"causal"}))
    ops = {str(p) for p in rel.subjects(RDF.type, OWL.ObjectProperty)}
    for gone in ("incurs_cost", "incurs_labour_cost", "suggested_to", "recommended_to_achieve",
                 "qualifies_as", "does_not_qualify_as", "assessed_against", "tolerates",
                 "carried_out_at"):
        assert WARP + gone not in ops and WARP + gone in removed
    assert (URIRef(WARP + "subject"), RDF.type, OWL.AnnotationProperty) in rel
    assert not list(rel.triples((URIRef(WARP + "incurs_cost"), None, None)))


def test_relations_keep_a_kept_groups_predicate_family(schema):
    keep = {"causal", "recommendation"}
    rel, removed = ss.subset_relations(ss.DEFAULT_RELATIONS, schema,
                                       sorted(set(ss.registry(schema)) - keep))
    ops = {str(p) for p in rel.subjects(RDF.type, OWL.ObjectProperty)}
    for kept in ("suggested_to", "recommended_to_achieve", "advised_against_for",
                 "suggested_for_consideration"):
        assert WARP + kept in ops
    full, none_removed = ss.subset_relations(ss.DEFAULT_RELATIONS, schema, [])
    assert none_removed == []


def test_scripts_run_against_a_profile():
    """The registry, derivation and project derivation work on a profile schema,
    and give the full build's propositions."""
    import derive_projects
    import derive_propositions as dp
    profile = PROFILES / "warp_causal.yaml"
    groups = dp.load_groups(profile)
    assert [g["group"] for g in groups] == ["causal"]
    data = load_yaml(EXAMPLES / "kramer1995_statements.yaml")
    names = {n["id"]: n.get("name", n["id"]) for n in data.get("nodes") or []}
    for g in groups:
        dp.derive_group(data, g, names)
    full = load_yaml(EXAMPLES / "kramer1995_statements.derived.yaml")
    assert data["causal_propositions"] == full["causal_propositions"]
    before = copy.deepcopy(data)
    report = derive_projects.derive(data, None, profile)
    assert report["no_group"] and data == before


def test_build_profile_compares_without_the_header(tmp_path):
    import build_profile
    a, b = tmp_path / "a.yaml", tmp_path / "b.yaml"
    a.write_text("# GENERATED by one script\nid: x\n", encoding="utf-8")
    b.write_text("# GENERATED by another\nid: x\n", encoding="utf-8")
    assert build_profile.body(a) == build_profile.body(b)
