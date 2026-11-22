"""Management strategy nodes (proposals section 6)."""

import copy
import subprocess
import sys

import pytest
import yaml
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

import derive_propositions as dp
import derive_strategies as ds
import export_rdf
from conftest import EXAMPLES, ROOT, SCHEMA, SCRIPTS, load_yaml

NODE = Namespace("https://w3id.org/causal-mosaic/node/")
OBO = Namespace("http://purl.obolibrary.org/obo/")
WARP = Namespace("https://w3id.org/ecoweaver/warp/")


def comp(action, step, **kw):
    return {"action": action, "step": step, **kw}


def strategy(node, *components):
    return {"node": node, "template": "management_strategy", "components": list(components)}


def defs(*ds_):
    return {d["node"]: d for d in ds_}


# --- flattening and keys ----------------------------------------------------------

def test_flat_strategy_key_ignores_lag_role_repeat_and_optional():
    a = strategy("node:a", comp("node:x", 1, role="site_preparation"), comp("node:y", 2, lag="P2W"),
                 comp("node:z", 3, repeat={"every": "P1Y", "times": 3}), comp("node:w", 4, optional=True))
    b = strategy("node:b", comp("node:x", 1), comp("node:y", 2, lag="P3W"), comp("node:z", 3))
    ka = ds.identity_key(ds.flatten(a, defs(a)))
    kb = ds.identity_key(ds.flatten(b, defs(b)))
    assert ka == kb == '[[1,"node:x"],[2,"node:y"],[3,"node:z"]]'


def test_order_is_part_of_identity():
    a = strategy("node:a", comp("node:x", 1), comp("node:y", 2))
    b = strategy("node:b", comp("node:y", 1), comp("node:x", 2))
    assert ds.canonical_id(ds.identity_key(ds.flatten(a, defs(a)))) != \
        ds.canonical_id(ds.identity_key(ds.flatten(b, defs(b))))


def test_parallel_parts_share_a_step():
    s = strategy("node:s", comp("node:x", 1), comp("node:y", 1), comp("node:z", 2, optional=True))
    assert ds.identity_key(ds.flatten(s, defs(s))) == '[[1,"node:x"],[1,"node:y"]]'


def test_nested_strategy_is_flattened_and_later_steps_shift():
    inner = strategy("node:inner", comp("node:a", 1), comp("node:b", 2), comp("node:c", 2))
    outer = strategy("node:outer", comp("node:start", 1), comp("node:inner", 2), comp("node:end", 3))
    flat = ds.flatten(outer, defs(inner, outer))
    assert [(c["step"], c["action"]) for c in flat] == [
        (1, "node:start"), (2, "node:a"), (3, "node:b"), (3, "node:c"), (4, "node:end")]


def test_nested_and_flat_descriptions_meet():
    inner = strategy("node:inner", comp("node:a", 1), comp("node:b", 2))
    nested = strategy("node:nested", comp("node:inner", 1), comp("node:c", 2))
    flat = strategy("node:flat", comp("node:a", 1), comp("node:b", 2), comp("node:c", 3))
    d = defs(inner, nested, flat)
    assert ds.identity_key(ds.flatten(nested, d)) == ds.identity_key(ds.flatten(flat, d))


def test_optional_nested_strategy_makes_its_parts_optional():
    inner = strategy("node:inner", comp("node:a", 1), comp("node:b", 2))
    outer = strategy("node:outer", comp("node:x", 1), comp("node:inner", 2, optional=True))
    flat = ds.flatten(outer, defs(inner, outer))
    assert all(c["optional"] for c in flat if c["action"] in ("node:a", "node:b"))
    assert ds.identity_key(flat) == '[[1,"node:x"]]'


def test_deeper_nesting_is_an_error():
    a = strategy("node:a", comp("node:x", 1), comp("node:y", 2))
    b = strategy("node:b", comp("node:a", 1), comp("node:z", 2))
    c = strategy("node:c", comp("node:b", 1), comp("node:w", 2))
    with pytest.raises(ds.StrategyError, match="one level"):
        ds.flatten(c, defs(a, b, c))


@pytest.mark.parametrize("pair", [
    (strategy("node:a", comp("node:a", 1), comp("node:x", 2)),),
    (strategy("node:a", comp("node:b", 1), comp("node:x", 2)), strategy("node:b", comp("node:a", 1), comp("node:y", 2))),
])
def test_cycles_are_errors(pair):
    with pytest.raises(ds.StrategyError, match="cycle"):
        ds.flatten(pair[0], defs(*pair))


# --- derivation on the worked example ------------------------------------------------

@pytest.fixture(scope="module")
def derived(schemaview):
    data = load_yaml(EXAMPLES / "strategy_statements.yaml")
    ds.derive(data, schemaview)
    dp.derive_all(data, SCHEMA)
    return data


def canon(data, local):
    return next(d["canonical_node"] for d in data["strategy_definitions"] if d["node"] == local)


def test_two_sources_describing_one_strategy_merge(derived):
    assert canon(derived, "node:earthworks-seed-mow") == canon(derived, "node:recontour-seed-mow-b")
    assert canon(derived, "node:earthworks-seed-mow").startswith("node:strategy-")
    assert all(d["identity_rule_version"] == ds.RULE_VERSION for d in derived["strategy_definitions"])


def test_statements_about_merged_strategies_derive_one_proposition(derived):
    props = derived["causal_propositions"]
    assert len(props) == 1
    assert sorted(props[0]["derived_from_statements"]) == ["stmt:strategy-a-native-cover", "stmt:strategy-b-native-cover"]
    assert props[0]["subject"] == canon(derived, "node:earthworks-seed-mow")


def test_canonical_nodes_get_node_records(derived):
    ids = {n["id"] for n in derived["nodes"]}
    assert {d["canonical_node"] for d in derived["strategy_definitions"]} <= ids


def test_derived_example_is_committed_and_current(schemaview):
    committed = load_yaml(EXAMPLES / "strategy_statements.derived.yaml")
    fresh = load_yaml(EXAMPLES / "strategy_statements.yaml")
    ds.derive(fresh, schemaview, previous=committed)
    dp.derive_all(fresh, SCHEMA)
    for slot in ("strategy_definitions", "causal_propositions", "causal_statements", "nodes"):
        assert fresh.get(slot) == committed.get(slot), slot


def test_superseded_canonical_ids_are_recorded(schemaview):
    data = load_yaml(EXAMPLES / "strategy_statements.yaml")
    ds.derive(copy.deepcopy(data), schemaview)
    previous = copy.deepcopy(data)
    ds.derive(previous, schemaview)
    old = canon(previous, "node:earthworks-seed-mow")
    changed = copy.deepcopy(data)
    changed["strategy_definitions"][0]["components"][2]["action"] = "node:fill_removal"
    ds.derive(changed, schemaview, previous=previous)
    d = changed["strategy_definitions"][0]
    assert d["canonical_node"] != old and d["replaces"] == [old]


# --- validation --------------------------------------------------------------------

def test_a_strategy_needs_two_components(validator):
    data = load_yaml(EXAMPLES / "strategy_statements.yaml")
    data["strategy_definitions"][0]["components"] = data["strategy_definitions"][0]["components"][:1]
    assert validator.validate(data, "StatementSet").results


def test_lag_is_an_iso_duration(validator):
    data = load_yaml(EXAMPLES / "strategy_statements.yaml")
    data["strategy_definitions"][0]["components"][1]["lag"] = "two weeks"
    assert validator.validate(data, "StatementSet").results


def test_role_maps_to_cost_phase(schemaview):
    import warp_schema as ws
    phases = {k: ws.annotation(v, "warp_cost_phase")
              for k, v in schemaview.get_enum("StrategyRoleEnum").permissible_values.items()}
    assert phases == {"site_preparation": "initial", "establishment": "initial", "follow_up": "follow_up",
                      "maintenance": "maintenance", "monitoring": "monitoring"}


# --- OWL and RDF -----------------------------------------------------------------------

@pytest.fixture(scope="module")
def nodes_graph(tmp_path_factory, derived):
    d = tmp_path_factory.mktemp("strat")
    src = d / "strategy.derived.yaml"
    src.write_text(yaml.safe_dump(derived), encoding="utf-8")
    out = d / "nodes.ttl"
    subprocess.run([sys.executable, str(SCRIPTS / "expand_nodes.py"), str(ROOT / "templates" / "node_templates.yaml"),
                    str(src), "--owl", str(out)], check=True, capture_output=True)
    return Graph().parse(out)


def test_strategy_is_a_subclass_never_an_equivalent_class(nodes_graph, derived):
    s = URIRef(NODE + canon(derived, "node:earthworks-seed-mow").split(":", 1)[1])
    assert (s, RDFS.subClassOf, OBO.OBI_0000011) in nodes_graph
    assert not list(nodes_graph.objects(s, OWL.equivalentClass))
    parts = {nodes_graph.value(r, OWL.someValuesFrom) for r in nodes_graph.objects(s, RDFS.subClassOf)
             if (r, OWL.onProperty, OBO.BFO_0000051) in nodes_graph}
    assert parts == {NODE.earthworks_recontouring, NODE.hand_seeding_native_mix_a, NODE.mowing_weed_control}
    assert (OBO.BFO_0000051, RDF.type, OWL.TransitiveProperty) in nodes_graph


def test_optional_parts_are_not_in_the_owl(nodes_graph, derived):
    s = URIRef(NODE + canon(derived, "node:fill-removal-plugs-spot-spray").split(":", 1)[1])
    parts = {nodes_graph.value(r, OWL.someValuesFrom) for r in nodes_graph.objects(s, RDFS.subClassOf)}
    assert NODE.spot_herbicide_phalaris not in parts and NODE.fill_removal in parts


def test_nested_strategy_owl_lists_the_flattened_parts(nodes_graph, derived):
    s = URIRef(NODE + canon(derived, "node:site-preparation-then-seeding").split(":", 1)[1])
    parts = {nodes_graph.value(r, OWL.someValuesFrom) for r in nodes_graph.objects(s, RDFS.subClassOf)}
    assert {NODE.removal_of_invasive_shrubs, NODE.earthworks_recontouring, NODE.hand_seeding_native_mix_a} <= parts


def test_superseded_iri_is_deprecated_in_owl(tmp_path, derived):
    data = copy.deepcopy(derived)
    data["strategy_definitions"][0]["replaces"] = ["node:strategy-000000000000"]
    src = tmp_path / "s.yaml"
    src.write_text(yaml.safe_dump(data), encoding="utf-8")
    out = tmp_path / "n.ttl"
    subprocess.run([sys.executable, str(SCRIPTS / "expand_nodes.py"), str(ROOT / "templates" / "node_templates.yaml"),
                    str(src), "--owl", str(out)], check=True, capture_output=True)
    g = Graph().parse(out)
    old = NODE["strategy-000000000000"]
    assert (old, OWL.deprecated, Literal(True)) in g
    assert g.value(old, OBO.IAO_0100001) == URIRef(NODE + data["strategy_definitions"][0]["canonical_node"].split(":", 1)[1])


def test_components_export_as_named_individuals(schemaview, derived):
    g, counts = export_rdf.export(schemaview, [derived])
    c = URIRef("https://w3id.org/ecoweaver/warp/component/earthworks-seed-mow/2")
    assert (c, RDF.type, WARP.StrategyComponent) in g
    assert (c, WARP.action, NODE.hand_seeding_native_mix_a) in g
    assert (c, WARP.lag, Literal("P2W")) in g
    assert (c, WARP.step, Literal(2, datatype=XSD.integer)) in g
    assert g.value(c, WARP.component_of) == URIRef(NODE + canon(derived, "node:earthworks-seed-mow").split(":", 1)[1])
    assert counts["components"] == sum(len(d["components"]) for d in derived["strategy_definitions"])
    # the definitions' strategy nodes are classes: never typed in the reification layer
    for d in derived["strategy_definitions"]:
        assert not list(g.triples((export_rdf.Exporter(schemaview).iri(d["canonical_node"]), RDF.type, None)))
    assert not any(isinstance(o, Literal) and o.datatype == XSD.duration for o in g.objects())
