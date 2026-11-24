"""The local term register (vocab/local/ -> project/local_terms.ttl and
project/local_classes.ttl, docs/terminology.md), and check_values.py's use of it."""

import copy

import pytest
import yaml
from rdflib import Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

import check_owl
import gen_vocab
from check_values import ValueChecker
from conftest import EXAMPLES, ROOT, load_yaml

LOCAL = ROOT / "vocab" / "local"
WARP = "https://w3id.org/ecoweaver/warp/"
PLACE = WARP + "place/"
TERM = WARP + "term/"


@pytest.fixture(scope="module")
def pm(schemaview):
    import warp_schema as ws
    return ws.prefix_map(schemaview)


def write_scheme(directory, name, scheme, terms):
    directory.mkdir(exist_ok=True)
    (directory / f"{name}.yaml").write_text(yaml.safe_dump({"scheme": scheme, "terms": terms}), encoding="utf-8")
    return directory


def term(tid, **extra):
    t = {"id": tid, "label": tid.replace("_", " "), "definition": f"Definition of {tid}.",
         "upstream": {"status": "not_checked"}}
    t.update(extra)
    return t


PLACES = {"id": "places", "label": "Places", "prefix": "place", "kind": "concept"}
ACTIONS = {"id": "actions", "label": "Actions", "prefix": "term", "kind": "class"}


# --- the committed register ------------------------------------------------------------

def test_register_prefixes_are_warp_spaces_in_the_profile(pm):
    for prefix in gen_vocab.REGISTER_PREFIXES:
        assert pm[prefix] == f"{WARP}{prefix}/"


def test_committed_register_loads_and_covers_every_local_place(pm):
    index = gen_vocab.register_index(gen_vocab.load_register(LOCAL, pm))
    used = set()
    for f in EXAMPLES.glob("*_statements.yaml"):
        for stmts in load_yaml(f).values():
            for s in stmts if isinstance(stmts, list) else []:
                if isinstance(s, dict):
                    used.update(p for p in s.get("place") or [] if p.startswith("place:"))
    assert used
    assert {PLACE + p.split(":", 1)[1] for p in used} <= set(index)


def test_criteria_concepts_stay_where_the_enum_points(pm, schemaview):
    index = gen_vocab.register_index(gen_vocab.load_register(LOCAL, pm))
    for pv in schemaview.get_enum("CriteriaConceptEnum").permissible_values.values():
        iri = schemaview.expand_curie(pv.meaning)
        assert index[iri]["kind"] == "concept"


def test_generated_local_terms_are_current(pm):
    from rdflib import Graph
    from rdflib.compare import isomorphic
    concepts, classes = gen_vocab.build_local_graphs(gen_vocab.load_register(LOCAL, pm), pm)
    out = ROOT / "project" / "local_terms.ttl"
    if not out.exists():
        pytest.fail("run make vocab first")
    assert isomorphic(Graph().parse(out), concepts), "project/local_terms.ttl is stale: run make vocab"
    assert (classes is None) == (not (ROOT / "project" / "local_classes.ttl").exists())


# --- generation ------------------------------------------------------------------------

def test_concepts_are_skos_and_classes_are_owl(tmp_path, pm):
    d = write_scheme(tmp_path / "local", "places", PLACES, [term("plains"), term("north_plains", broader="place:plains")])
    write_scheme(d, "actions", ACTIONS, [term("hand_seeding", broader="ELMO:0000001",
                                             upstream={"target": "ELMO", "status": "to_request"})])
    concepts, classes = gen_vocab.build_local_graphs(gen_vocab.load_register(d, pm), pm)
    plains, north = URIRef(PLACE + "plains"), URIRef(PLACE + "north_plains")
    assert (plains, RDF.type, SKOS.Concept) in concepts
    assert (north, SKOS.broader, plains) in concepts                 # in the scheme: skos:broader
    assert (URIRef(PLACE + "places"), SKOS.hasTopConcept, north) not in concepts
    seed = URIRef(TERM + "hand_seeding")
    assert (seed, RDF.type, OWL.Class) in classes
    assert (seed, RDFS.subClassOf, URIRef(pm["ELMO"] + "0000001")) in classes
    assert (seed, gen_vocab.DEFINITION, None) in classes
    assert not list(concepts.triples((seed, None, None)))            # never a concept as well
    assert "status to_request" in str(classes.value(seed, RDFS.comment))


def test_no_class_schemes_means_no_class_file(tmp_path, pm):
    d = write_scheme(tmp_path / "local", "places", PLACES, [term("plains")])
    assert gen_vocab.build_local_graphs(gen_vocab.load_register(d, pm), pm)[1] is None


def test_external_broader_is_a_broad_match(tmp_path, pm):
    d = write_scheme(tmp_path / "local", "places", PLACES, [term("plains", broader="wd:Q1")])
    concepts, _ = gen_vocab.build_local_graphs(gen_vocab.load_register(d, pm), pm)
    assert (URIRef(PLACE + "plains"), SKOS.broadMatch, URIRef(pm["wd"] + "Q1")) in concepts


def test_accepted_terms_are_deprecated_and_replaced(tmp_path, pm):
    up = {"target": "Wikidata", "status": "accepted", "replaced_by": "wd:Q1"}
    d = write_scheme(tmp_path / "local", "places", PLACES, [term("plains", upstream=up)])
    write_scheme(d, "actions", ACTIONS, [term("hand_seeding", broader="ELMO:0000001",
                                             upstream={"target": "ELMO", "status": "accepted",
                                                       "replaced_by": "ELMO:0000002"})])
    concepts, classes = gen_vocab.build_local_graphs(gen_vocab.load_register(d, pm), pm)
    plains, seed = URIRef(PLACE + "plains"), URIRef(TERM + "hand_seeding")
    assert (plains, OWL.deprecated, Literal(True)) in concepts
    assert (plains, gen_vocab.TERM_REPLACED_BY, URIRef(pm["wd"] + "Q1")) in concepts
    assert (plains, SKOS.exactMatch, URIRef(pm["wd"] + "Q1")) in concepts
    assert (seed, OWL.deprecated, Literal(True)) in classes
    assert not list(classes.triples((seed, RDFS.subClassOf, None)))  # no logical axioms once deprecated


def test_generated_files_pass_the_owl_lint(tmp_path, pm):
    d = write_scheme(tmp_path / "local", "places", PLACES, [term("plains")])
    write_scheme(d, "actions", ACTIONS, [term("hand_seeding", broader="ELMO:0000001")])
    concepts, classes = gen_vocab.build_local_graphs(gen_vocab.load_register(d, pm), pm)
    files = []
    for name, g in (("local_terms.ttl", concepts), ("local_classes.ttl", classes)):
        g.serialize(tmp_path / name, format="turtle")
        files.append(tmp_path / name)
    assert check_owl.check_files(files) == []


@pytest.mark.parametrize("scheme, terms, message", [
    (dict(PLACES, prefix="TODO"), [term("x")], "not a register prefix"),
    (dict(PLACES, prefix="scale"), [term("x")], "not a register prefix"),
    (dict(PLACES, kind="class"), [term("x")], "holds concept terms"),
    (dict(ACTIONS, kind="concept"), [term("x")], "holds class terms"),
    (dict(PLACES, label=None), [term("x")], "needs a label"),
    (PLACES, [], "at least one term"),
    (PLACES, [term("has space")], "IRI-safe"),
    (PLACES, [term("x"), term("x")], "already"),
    (PLACES, [term("places")], "already"),                            # collides with the scheme IRI
    (PLACES, [term("x", definition=None)], "needs a definition"),
    (PLACES, [term("x", upstream=None)], "needs upstream.status"),
    (PLACES, [term("x", upstream={"status": "maybe"})], "is not one of"),
    (PLACES, [term("x", upstream={"status": "to_request"})], "needs upstream.target"),
    (PLACES, [term("x", upstream={"status": "requested", "target": "Wikidata"})], "needs upstream.issue"),
    (PLACES, [term("x", upstream={"status": "requested", "target": "W", "issue": "#12"})], "must be a URL"),
    (PLACES, [term("x", upstream={"status": "accepted", "target": "Wikidata"})], "needs upstream.replaced_by"),
    (PLACES, [term("x", upstream={"status": "accepted", "target": "W", "replaced_by": "TODO:x"})], "TODO"),
    (PLACES, [term("x", upstream={"status": "accepted", "target": "W", "replaced_by": "nope:1"})], "undeclared"),
    (PLACES, [term("x", upstream={"status": "not_appropriate"})], "needs upstream.reason"),
    (PLACES, [term("x", upstream={"status": "to_request", "target": "W", "replaced_by": "wd:Q1"})],
     "only for status accepted"),
    (PLACES, [term("x", upstream={"status": "not_checked", "owner": "me"})], "unknown upstream field"),
    (PLACES, [term("x", broader="place:missing")], "not registered"),
])
def test_malformed_register_is_refused(tmp_path, pm, scheme, terms, message):
    d = write_scheme(tmp_path / "local", "bad", scheme, terms)
    with pytest.raises(gen_vocab.VocabError, match=message):
        gen_vocab.load_register(d, pm)


# --- check_values ----------------------------------------------------------------------

@pytest.fixture(scope="module")
def register_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("register") / "local"
    write_scheme(d, "places", PLACES, [term("plains"), term("old_plains", upstream={
        "target": "Wikidata", "status": "accepted", "replaced_by": "wd:Q1"})])
    return d


def place_errors(schemaview, register_dir, place):
    c = ValueChecker(schemaview, local_path=register_dir)
    data = copy.deepcopy(load_yaml(EXAMPLES / "bloodroot_statements.yaml"))
    data["causal_statements"][0]["place"] = place
    c.check_set("test", data)
    return c.errors


@pytest.mark.parametrize("place, message", [
    (["place:plains"], None),
    (["https://w3id.org/ecoweaver/warp/place/plains"], None),
    (["place:unregistered"], "not in the register"),
    (["https://w3id.org/ecoweaver/warp/place/unregistered"], "not in the register"),
    (["place:old_plains"], "deprecated"),
    (["wd:Q1"], None),                                                # not a local IRI
])
def test_local_terms_must_be_registered_and_current(schemaview, register_dir, place, message):
    errs = place_errors(schemaview, register_dir, place)
    if message is None:
        assert errs == []
    else:
        assert len(errs) == 1 and message in errs[0], errs
        if message == "deprecated":
            assert "wd:Q1" in errs[0]
