"""The RDF and OWL contract (decisions D11 to D20)."""

import copy

import pytest
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS, XSD

import check_owl
import clean_owl
import derive_propositions as dp
import export_rdf
import project_owl
from conftest import EXAMPLES, ROOT, SCHEMA, load_yaml

WARP = Namespace("https://w3id.org/ecoweaver/warp/")
NODE = Namespace("https://w3id.org/causal-mosaic/node/")
CAMO = Namespace("https://w3id.org/camo/")
STMT = Namespace("https://w3id.org/ecoweaver/warp/statement/")


# --- a fixture statement set --------------------------------------------------------

def statement(sid, **kw):
    s = {
        "id": f"warp:statement/{sid}", "type": "CausalStatement",
        "subject": "node:planting_of_sanguinaria_canadensis", "predicate": "prevents",
        "object": "node:rate_of_population_growth_of_alliaria_petiolata",
        "scope": "universal", "modality": "observed", "causal_language": "direct_causal",
        "contributions": [{"id": f"warp:contrib/{sid}", "type": "EcoContribution", "role": "author",
                           "contributor": "warp:agent/a", "date": "2024-05"}],
        "predicate_qualifiers": {"reversibility": "not_addressed", "philosophical_accounts": ["interventionist"]},
        "hasEvidenceLines": [{"id": f"warp:el/{sid}", "type": "EcoEvidenceLine",
                              "evidence_type": "randomized_experiment", "directionOfEvidenceProvided": "supports"}],
    }
    s.update(kw)
    return s


def fixture_set(*statements):
    base = load_yaml(EXAMPLES / "bloodroot_statements.yaml")
    return {
        "id": "warp:statementset/fixture",
        "agents": [{"id": "warp:agent/a", "type": "EcoAgent", "name": "A", "agent_kind": "researcher"}],
        "nodes": copy.deepcopy(base["nodes"]),
        "causal_statements": list(statements),
    }


def derived(*statements):
    data = fixture_set(*statements)
    dp.derive_all(data, SCHEMA)
    return data


def assessment(prop_id, direction="supports"):
    return {"id": "warp:statementset/fixture-assessment", "assessments": [{
        "id": "warp:assessment/fixture", "type": "SynthesisAssessment", "proposition": prop_id,
        "direction": direction, "strength": "moderate",
        "contributions": [{"id": "warp:contrib/fx-assess", "type": "EcoContribution", "role": "author",
                           "contributor": "warp:agent/ecoweaver-synthesis"}]}]}


@pytest.fixture(scope="module")
def sv(schemaview):
    return schemaview


# --- export_rdf ----------------------------------------------------------------------

def test_fixture_set_validates(validator):
    data = derived(statement("s1"))
    assert not validator.validate(data, "StatementSet").results


def test_export_has_no_blank_nodes_and_uses_annotation_properties(sv):
    g, counts = export_rdf.export(sv, [derived(statement("s1"))])
    assert not any(isinstance(t, BNode) for triple in g for t in triple)
    s = STMT.s1
    assert (s, WARP.subject, NODE.planting_of_sanguinaria_canadensis) in g
    assert (s, WARP.predicate, CAMO.prevents) in g
    # qualifier bundles get IRIs under their owner
    assert (s, WARP.predicate_qualifiers, URIRef(f"{s}/predicate_qualifiers")) in g


def test_enum_values_export_as_iris_and_sentinels_not_at_all(sv):
    g, counts = export_rdf.export(sv, [derived(statement("s1"))])
    assert (STMT.s1, WARP.scope, URIRef(f"{WARP}SemanticUnitScopeEnum#universal")) in g
    assert not list(g.objects(URIRef(f"{STMT.s1}/predicate_qualifiers"), WARP.reversibility))
    assert counts["sentinels"] >= 1
    assert not any(isinstance(o, Literal) for o in g.objects(None, WARP.scope))


def test_relation_triple_and_negation(sv):
    neg = statement("s2", negated=True, causal_language="no_relationship")
    g, counts = export_rdf.export(sv, [derived(statement("s1"), neg)])
    relation = (NODE.planting_of_sanguinaria_canadensis, CAMO.prevents,
                NODE.rate_of_population_growth_of_alliaria_petiolata)
    assert relation in g
    assert counts["relations"] == 1 and counts["negated"] == 1
    # the negated statement still has its record
    assert (STMT.s2, RDF.type, WARP.CausalStatement) in g
    assert (STMT.s2, WARP.negated, Literal(True)) in g


def test_only_negated_statements_give_no_relation_triple(sv):
    neg = statement("s2", negated=True, causal_language="no_relationship")
    g, _ = export_rdf.export(sv, [derived(neg)])
    assert not list(g.triples((None, CAMO.prevents, None)))


def test_dates_are_strings_with_datetime_bounds(sv):
    g, _ = export_rdf.export(sv, [derived(statement("s1"))])
    c = URIRef(f"{WARP}contrib/s1")
    assert (c, WARP.date, Literal("2024-05")) in g
    lo = g.value(c, URIRef(f"{WARP}date_lower_bound"))
    hi = g.value(c, URIRef(f"{WARP}date_upper_bound"))
    assert lo.datatype == XSD.dateTime and str(lo) == "2024-05-01T00:00:00Z"
    assert str(hi) == "2024-06-01T00:00:00Z"
    assert not any(isinstance(o, Literal) and o.datatype in (XSD.date, XSD.gYear, XSD.duration) for o in g.objects())


def test_node_records_are_not_exported_as_individuals(sv):
    g, _ = export_rdf.export(sv, [derived(statement("s1"))])
    assert not list(g.triples((NODE.planting_of_sanguinaria_canadensis, RDF.type, None)))


def test_no_sepio_placeholder_iris_in_export(sv):
    sets = [load_yaml(p) for p in sorted(EXAMPLES.glob("*.yaml"))]
    g, _ = export_rdf.export(sv, sets)
    assert not any("example.org" in str(t) for triple in g for t in triple)


# --- project_owl: the gate ------------------------------------------------------------

def project(sv, statements, assessed=True, direction="supports"):
    d = derived(*statements)
    props = d.get("causal_propositions") or []
    sets = [d] + ([assessment(props[0]["id"], direction)] if assessed and props else [])
    return project_owl.Projector(sv).run(sets)


def rejected_reasons(report):
    return [r for _, reasons in report["rejected"].get("causal", []) for r in reasons]


def test_gate_accepts_universal_observed_supported(sv):
    g, report = project(sv, [statement("s1")])
    assert len(report["passed"]) == 1
    restriction = g.value(NODE.planting_of_sanguinaria_canadensis, RDFS.subClassOf)
    assert (restriction, OWL.onProperty, CAMO.prevents) in g
    assert (restriction, OWL.someValuesFrom, NODE.rate_of_population_growth_of_alliaria_petiolata) in g
    assert not list(g.triples((None, OWL.equivalentClass, None)))
    # the axiom names the proposition it came from
    ax = g.value(predicate=OWL.annotatedTarget, object=restriction)
    assert g.value(ax, project_owl.DERIVED_FROM) is not None
    assert (project_owl.AXIOMS_ONTOLOGY, OWL.imports, project_owl.NODES_ONTOLOGY) in g


@pytest.mark.parametrize("kw, reason", [
    ({"scope": "assertional"}, "scope is assertional"),
    ({"scope": "prototypical"}, "scope is prototypical"),
    ({"negated": True, "causal_language": "no_relationship"}, "negated"),
    ({"modality": "anticipated"}, "not modality observed"),
    ({"modality": None}, "not modality observed"),
])
def test_gate_rejects(sv, kw, reason):
    s = statement("s1", **kw)
    s = {k: v for k, v in s.items() if v is not None}
    g, report = project(sv, [s])
    assert not report["passed"]
    assert any(reason in r for r in rejected_reasons(report))
    assert not list(g.triples((None, RDFS.subClassOf, None)))


def test_gate_rejects_unassessed_and_disputed(sv):
    _, unassessed = project(sv, [statement("s1")], assessed=False)
    _, disputed = project(sv, [statement("s1")], direction="disputes")
    for report in (unassessed, disputed):
        assert not report["passed"]
        assert "no supporting SynthesisAssessment" in rejected_reasons(report)


def test_one_anticipated_statement_blocks_the_proposition(sv):
    _, report = project(sv, [statement("s1"), statement("s2", modality="anticipated")])
    assert not report["passed"] and "1 of 2 statement(s) not modality observed" in rejected_reasons(report)


def test_examples_pass_nothing(sv):
    sets = [load_yaml(p) for p in sorted(EXAMPLES.glob("*.derived.yaml"))] + \
           [load_yaml(p) for p in sorted(EXAMPLES.glob("*_assessment.yaml"))]
    g, report = project_owl.Projector(sv).run(sets)
    assert report["considered"] >= 5 and not report["passed"]
    assert "Nothing passed" in project_owl.render_report(report)


# --- check_owl ----------------------------------------------------------------------

def lint(*graphs):
    return check_owl.OwlChecker(list(graphs)).run()


def ttl(text):
    return Graph().parse(data="@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
                              "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
                              "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n"
                              "@prefix warp: <https://w3id.org/ecoweaver/warp/> .\n"
                              "@prefix node: <https://w3id.org/causal-mosaic/node/> .\n" + text, format="turtle")


def test_lint_catches_class_used_as_individual():
    nodes = ttl("node:x a owl:Class .")
    stmts = ttl("node:x a warp:CausalStatement .")
    errs = lint(("nodes.ttl", nodes), ("statements.ttl", stmts))
    assert any("[kinds]" in e and "node/x" in e for e in errs)


def test_lint_allows_relation_triples_between_classes_in_the_reification_layer():
    nodes = ttl("node:x a owl:Class . node:y a owl:Class .")
    stmts = ttl("node:x <https://w3id.org/camo/prevents> node:y .")
    assert lint(("nodes.ttl", nodes), ("statements.ttl", stmts)) == []


def test_lint_catches_predicate_typed_as_class():
    schema = ttl("<http://purl.obolibrary.org/obo/RO_0002470> a owl:Class .")
    axioms = ttl("node:x rdfs:subClassOf [ a owl:Restriction ; owl:onProperty <http://purl.obolibrary.org/obo/RO_0002470> ; owl:someValuesFrom node:y ] ."
                 "<http://purl.obolibrary.org/obo/RO_0002470> a owl:ObjectProperty .")
    errs = lint(("warp.owl.ttl", schema), ("axioms.ttl", axioms))
    assert any("[kinds]" in e and "RO_0002470" in e for e in errs)


def test_lint_catches_xsd_date_literal():
    errs = lint(("statements.ttl", ttl('warp:x warp:when "2024-05-01"^^xsd:date .')))
    assert any("[datatypes]" in e for e in errs)


def test_lint_catches_placeholder_under_real_prefix_and_relative_iris():
    g = ttl("node:x rdfs:label 'x' . <https://w3id.org/elmo/elmo_TODO_planting> rdfs:label 'p' .")
    g.add((URIRef("file:///tmp/ha"), RDFS.label, Literal("ha")))
    errs = lint(("nodes.ttl", g))
    assert any("placeholder" in e for e in errs) and any("relative IRI" in e for e in errs)


def test_lint_catches_exported_sentinel():
    g = ttl("warp:x warp:evidence_type <https://w3id.org/ecoweaver/warp/WarpEvidenceTypeEnum#not_stated> .")
    assert any("[sentinels]" in e for e in lint(("statements.ttl", g)))


def test_lint_catches_undeclared_warp_predicate_and_abstract_use():
    relations = ttl("warp:suggested_to a owl:ObjectProperty ; warp:abstract_predicate true .")
    stmts = ttl("node:x warp:suggested_to node:y . node:x warp:made_up node:y .")
    errs = lint(("warp-relations.ttl", relations), ("statements.ttl", stmts))
    assert any("abstract predicate" in e for e in errs)
    assert any("made_up" in e and "not declared" in e for e in errs)


def test_lint_catches_literal_on_object_property():
    schema = ttl("warp:scope a owl:ObjectProperty .")
    stmts = ttl('warp:s warp:scope "assertional" .')
    errs = lint(("warp.owl.ttl", schema), ("statements.ttl", stmts))
    assert any("literal value" in e for e in errs)


def test_generated_files_are_clean():
    files = [ROOT / "project" / f for f in ("nodes.ttl", "axioms.ttl", "statements.ttl", "warp.owl.ttl", "scales.ttl", "local_terms.ttl")]
    files.append(ROOT / "src" / "warp" / "owl" / "warp-relations.ttl")
    missing = [f for f in files if not f.exists()]
    if missing:
        pytest.fail(f"run make all first: missing {missing}")
    assert check_owl.check_files(files) == []


# --- clean_owl ------------------------------------------------------------------------

def test_clean_owl_moves_covering_axioms_drops_sentinels_and_nothing_else(sv):
    g = Graph()
    scope = URIRef(f"{WARP}SemanticUnitScopeEnum")
    vals = [URIRef(f"{scope}#{v}") for v in ("assertional", "universal", "unclear")]
    g.add((scope, RDF.type, OWL.Class))
    lst = BNode()
    Collection(g, lst, vals)
    g.add((scope, OWL.oneOf, lst))
    for v in vals:
        g.add((v, RDF.type, OWL.NamedIndividual))
        g.add((v, RDF.type, scope))
    union_enum = URIRef(f"{WARP}SomeClassEnum")
    ul = BNode()
    Collection(g, ul, [URIRef(f"{WARP}A"), URIRef(f"{WARP}B")])
    g.add((union_enum, OWL.unionOf, ul))
    bystander = (URIRef(f"{WARP}Thing"), RDFS.label, Literal("left alone"))
    g.add(bystander)

    report = clean_owl.Cleaner(g, sv, Graph()).run()
    assert not list(g.triples((scope, OWL.oneOf, None)))
    anon = g.value(scope, OWL.equivalentClass)
    assert isinstance(anon, BNode) and (anon, RDF.type, OWL.Class) in g
    members = list(Collection(g, g.value(anon, OWL.oneOf)))
    assert members == vals[:2]                       # 'unclear' is a sentinel, gone
    assert not list(g.triples((vals[2], None, None)))
    assert isinstance(g.value(union_enum, OWL.equivalentClass), BNode)
    assert bystander in g
    assert report["sentinels"] and report["covering_axioms"]


def test_clean_owl_retypes_upstream_predicate_enum(sv):
    g = Graph()
    enum = URIRef(f"{WARP}CausalPredicateEnum")
    for v in ("associated_with", "correlated_with"):
        g.add((CAMO[v], RDF.type, OWL.NamedIndividual))
        g.add((CAMO[v], RDF.type, enum))
    g.add((CAMO.correlated_with, RDFS.subClassOf, CAMO.associated_with))
    clean_owl.Cleaner(g, sv, Graph()).predicate_enums()
    assert (CAMO.correlated_with, RDF.type, OWL.ObjectProperty) in g
    assert (CAMO.correlated_with, RDF.type, OWL.NamedIndividual) not in g
    assert (CAMO.correlated_with, RDFS.subPropertyOf, CAMO.associated_with) in g
    assert (CAMO.correlated_with, RDFS.subClassOf, CAMO.associated_with) not in g


def test_clean_owl_strips_restrictions_on_annotation_properties(sv):
    g = Graph()
    r = BNode()
    g.add((r, RDF.type, OWL.Restriction))
    g.add((r, OWL.onProperty, WARP.subject))
    g.add((r, OWL.allValuesFrom, URIRef("https://w3id.org/causal-mosaic/CausalNode")))
    g.add((WARP.CausalStatement, RDFS.subClassOf, r))
    clean_owl.Cleaner(g, sv, Graph()).annotation_restrictions()
    assert len(g) == 0


def test_clean_owl_single_value_enum_gets_explicit_list(sv):
    g = Graph()
    enum = URIRef(f"{WARP}OneEnum")
    lst = BNode()
    Collection(g, lst, [URIRef(f"{enum}#only")])
    g.add((enum, OWL.oneOf, lst))
    clean_owl.Cleaner(g, sv, Graph()).covering_axioms()
    anon = g.value(enum, OWL.equivalentClass)
    assert isinstance(anon, BNode)
    assert list(Collection(g, g.value(anon, OWL.oneOf))) == [URIRef(f"{enum}#only")]


def test_schema_owl_has_no_named_covering_axioms_or_class_typed_predicates():
    g = Graph().parse(ROOT / "project" / "warp.owl.ttl")
    assert not [s for s in g.subjects(OWL.oneOf, None) if isinstance(s, URIRef)]
    assert not [s for s in g.subjects(OWL.unionOf, None) if isinstance(s, URIRef)]
    assert (CAMO.prevents, RDF.type, OWL.ObjectProperty) in g
    assert (CAMO.prevents, RDF.type, OWL.Class) not in g
    assert (CAMO.prevents, RDF.type, OWL.NamedIndividual) not in g
