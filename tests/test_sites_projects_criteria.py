"""Sites, implementation and projects, criteria and Target 2 (Phase 7)."""

import copy
import subprocess
import sys

import pytest
import yaml
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

import check_sites
import check_statements
import derive_projects as dpj
import export_rdf
import project_owl
import report_target2 as t2
from conftest import EXAMPLES, ROOT, SCHEMA, SCRIPTS, load_yaml

WARP = Namespace("https://w3id.org/ecoweaver/warp/")
NODE = Namespace("https://w3id.org/causal-mosaic/node/")
SITE = Namespace("https://w3id.org/ecoweaver/warp/site/")
PROJ = Namespace("https://w3id.org/ecoweaver/warp/project/")
CRIT = "https://w3id.org/ecoweaver/warp/criteria/"
CONCEPT = Namespace("https://w3id.org/ecoweaver/warp/concept/")
OBO = Namespace("http://purl.obolibrary.org/obo/")
STRATEGY = "node:strategy-f38f3a2661ee"


@pytest.fixture(scope="module")
def derived():
    return load_yaml(EXAMPLES / "implementation_statements.derived.yaml")


@pytest.fixture(scope="module")
def strategies():
    return load_yaml(EXAMPLES / "strategy_statements.derived.yaml")


def project(data, pid):
    return next(p for p in data["implementation_propositions"] if p["id"] == pid)


# --- 7.1 sites ----------------------------------------------------------------------

@pytest.fixture(scope="module")
def sites_graph(tmp_path_factory, derived):
    d = tmp_path_factory.mktemp("sites")
    src = d / "i.yaml"
    src.write_text(yaml.safe_dump(derived), encoding="utf-8")
    out = d / "sites.ttl"
    subprocess.run([sys.executable, str(SCRIPTS / "expand_nodes.py"), str(ROOT / "templates" / "node_templates.yaml"),
                    str(src), "--sites", str(out)], check=True, capture_output=True)
    return Graph().parse(out)


def test_sites_are_individuals_typed_by_ecosystem(sites_graph):
    s = SITE["0412"]
    assert (s, RDF.type, OWL.NamedIndividual) in sites_graph
    assert (s, RDF.type, URIRef("https://w3id.org/ecoweaver/warp/TODO/grassland")) in sites_graph
    assert (s, RDF.type, OWL.Class) not in sites_graph
    assert sites_graph.value(s, RDFS.label) == Literal("Agreement site 0412")
    assert sites_graph.value(s, WARP.in_jurisdiction) == URIRef("https://www.iso.org/obp/ui/#iso:code:3166:CA-SK")


def test_geometry_never_reaches_a_generated_file(sites_graph):
    assert not any("Polygon" in str(o) or "coordinates" in str(o) for o in sites_graph.objects())
    for f in (ROOT / "project").glob("*.ttl"):
        assert "Polygon" not in f.read_text(encoding="utf-8"), f.name


def test_jurisdiction_without_a_code_is_a_literal(tmp_path, derived):
    data = copy.deepcopy(derived)
    data["site_definitions"][1]["jurisdiction"] = "TODO: a treaty territory"
    src = tmp_path / "i.yaml"
    src.write_text(yaml.safe_dump(data), encoding="utf-8")
    out = tmp_path / "sites.ttl"
    subprocess.run([sys.executable, str(SCRIPTS / "expand_nodes.py"), str(ROOT / "templates" / "node_templates.yaml"),
                    str(src), "--sites", str(out)], check=True, capture_output=True)
    g = Graph().parse(out)
    assert g.value(SITE["0517"], WARP.jurisdiction_name) == Literal("TODO: a treaty territory")
    assert g.value(SITE["0517"], WARP.in_jurisdiction) is None


@pytest.mark.parametrize("change, message, kind", [
    (lambda d: d["site_definitions"][1].__setitem__("geometry", "POINT (1 2)"), "withheld", "error"),
    (lambda d: d["site_definitions"][0].__setitem__("geometry", "{not json"), "does not parse", "error"),
    (lambda d: d["site_definitions"][0].__setitem__("geometry_precision", "exact"), "exact geometry", "warning"),
    (lambda d: d["site_definitions"][0].__setitem__("node", "node:site_0412"), "under site:", "error"),
    (lambda d: d["implementation_statements"][0].__setitem__("object", "node:fill_removal"), "needs a site", "error"),
])
def test_check_sites(derived, strategies, change, message, kind):
    data = copy.deepcopy(derived)
    change(data)
    errors, warnings = check_sites.check([data, strategies])
    found = errors if kind == "error" else warnings
    assert any(message in m for m in found), (errors, warnings)


def test_examples_pass_check_sites(derived, strategies):
    assert check_sites.check([derived, strategies]) == ([], [])


# --- 7.2 implementation and projects ---------------------------------------------

def test_two_reports_of_one_agreement_are_one_project(derived):
    p = project(derived, "prop:agreement-0412")
    assert p["about_project"] == "proj:agreement-0412"
    assert sorted(p["derived_from_statements"]) == ["stmt:funder-0412", "stmt:land-trust-0412"]
    areas = {a["claimant"]: a["area"]["value"] for a in p["area_by_claimant"]}
    assert areas == {"org:land-trust-a": 42, "org:funder-b": 40}          # kept, attributed
    assert p["implemented_by"] == ["org:land-trust-a"] and p["funded_by"] == ["org:funder-b"]
    assert p["period"] == {"start": "2024-05"}                            # open: the land trust's is ongoing
    assert p["identity_rule_version"] == "warp-impl-identity/1"


def test_same_strategy_on_another_site_is_another_project(derived):
    ids = {p["about_project"] for p in derived["implementation_propositions"]}
    assert len(ids) == 2 and "proj:agreement-0412" in ids


def test_project_nodes_exist_for_criteria_statements(derived):
    assert {"proj:agreement-0412"} <= {n["id"] for n in derived["nodes"]}


def impl(sid, site="site:0412", period=None, ext=None, claimant="org:land-trust-a", status="in_progress",
         reported="2026-01-01", area=None):
    q = {"period": period or {"start": "2024"}, "status": status, "reported_on": reported}
    if ext:
        q["external_ids"] = [{"scheme": s, "value": v} for s, v in ext]
    if area:
        q["area_treated"] = {"value": area, "unit": "TODO:unit_hectare"}
    return {"id": sid, "type": "ImplementationStatement", "subject": STRATEGY, "predicate": "carried_out_at",
            "object": site, "scope": "assertional", "predicate_qualifiers": q,
            "contributions": [{"id": f"warp:contrib/{sid}", "type": "EcoContribution", "role": "author",
                               "contributor": claimant}]}


def run(statements, previous=None):
    data = {"implementation_statements": copy.deepcopy(statements)}
    report = dpj.derive(data, previous)
    return data, report


def test_overlapping_periods_link_without_external_ids():
    data, _ = run([impl("s1", period={"start": "2023"}), impl("s2", period={"start": "2024-05", "end": "2025"})])
    assert len(data["implementation_propositions"]) == 1


def test_non_overlapping_periods_stay_apart():
    data, _ = run([impl("s1", period={"start": "2020", "end": "2021"}), impl("s2", period={"start": "2024-05"})])
    assert len(data["implementation_propositions"]) == 2


def test_string_order_would_get_overlap_wrong():
    """'2024-05' > '2023' as strings, yet a period from 2023 (open) covers it."""
    data, _ = run([impl("s1", period={"start": "2024-05", "end": "2024-05"}), impl("s2", period={"start": "2023"})])
    assert len(data["implementation_propositions"]) == 1


def test_project_id_is_stable_when_a_claim_joins():
    base = [impl("s1", ext=[("agreement", "0412")])]
    before, _ = run(base)
    after, _ = run(base + [impl("s2", period={"start": "2024-06"})], previous=before)
    assert [p["about_project"] for p in after["implementation_propositions"]] == ["proj:agreement-0412"]
    assert "replaces" not in after["implementation_propositions"][0]


def test_moved_project_id_is_recorded_and_deprecated(schemaview):
    base = [impl("s1", ext=[("agreement", "0412")])]
    before, _ = run(base)
    after, report = run(base + [impl("s2", ext=[("agreement", "0001")], period={"start": "2024-06"})], previous=before)
    p = after["implementation_propositions"][0]
    assert p["about_project"] == "proj:agreement-0001" and p["replaces"] == ["proj:agreement-0412"]
    assert report["bad_merges"] == [("prop:agreement-0001", {"agreement": ["0001", "0412"]})]
    g, n = project_owl.project_individuals(project_owl.Projector(schemaview), [after])
    assert (PROJ["agreement-0412"], OWL.deprecated, Literal(True)) in g
    assert g.value(PROJ["agreement-0412"], OBO.IAO_0100001) == PROJ["agreement-0001"]


def test_latest_status_within_one_claimant_only():
    data, _ = run([impl("s1", ext=[("a", "1")], status="planned", reported="2024-01"),
                   impl("s2", ext=[("a", "1")], status="in_progress", reported="2025-03"),
                   impl("s3", ext=[("a", "1")], status="completed", reported="2023", claimant="org:funder-b")])
    statuses = {e["claimant"]: e["status"] for e in data["implementation_propositions"][0]["status_by_claimant"]}
    assert statuses == {"org:land-trust-a": "in_progress", "org:funder-b": "completed"}


def test_implementation_scope_must_be_assertional(validator):
    data = load_yaml(EXAMPLES / "implementation_statements.yaml")
    data["implementation_statements"][0]["scope"] = "prototypical"
    assert validator.validate(data, "StatementSet").results


def test_projects_ttl(schemaview, derived):
    g, n = project_owl.project_individuals(project_owl.Projector(schemaview), [derived])
    p = PROJ["agreement-0412"]
    assert n == 2
    assert (p, RDF.type, OWL.NamedIndividual) in g
    assert (p, RDF.type, URIRef(NODE + "strategy-f38f3a2661ee")) in g
    assert (p, OBO.RO_0001025, SITE["0412"]) in g
    assert str(g.value(p, WARP.period_start)) == "2024-05-01T00:00:00Z"
    assert g.value(p, WARP.period_end) is None
    assert (p, RDF.type, OWL.Class) not in g


# --- RDF for implementation and criteria --------------------------------------------

@pytest.fixture(scope="module")
def graph(schemaview, derived, strategies):
    g, _ = export_rdf.export(schemaview, [derived, strategies])
    return g


def test_carried_out_at_and_is_about(graph):
    assert (URIRef(NODE + "strategy-f38f3a2661ee"), WARP.carried_out_at, SITE["0412"]) in graph
    assert (URIRef("https://w3id.org/ecoweaver/warp/prop/agreement-0412"), OBO.IAO_0000136,
            PROJ["agreement-0412"]) in graph
    assert not list(graph.triples((SITE["0412"], RDF.type, None)))       # site records are not exported


def test_criteria_object_is_the_set_and_the_verdict_picks_the_predicate(graph):
    fed = URIRef(CRIT + "degraded-area/fed-draft-1")
    assert (SITE["0412"], WARP.qualifies_as, fed) in graph
    assert (SITE["0412"], WARP.does_not_qualify_as, fed) in graph      # assessor E disagrees
    assert (SITE["0517"], WARP.does_not_qualify_as, fed) in graph
    assert not list(graph.triples((None, WARP.qualifies_as, CONCEPT.degraded_area)))
    assert not list(graph.triples((None, WARP.assessed_against, None)))


def test_neutral_verdict_has_a_record_and_no_triple(graph):
    s = URIRef("https://w3id.org/ecoweaver/warp/statement/ecoweaver-project-0517-effective")
    assert graph.value(s, WARP.predicate) == WARP.assessed_against
    subj = graph.value(s, WARP.subject)
    assert not list(graph.triples((subj, WARP.qualifies_as, None)))
    assert not list(graph.triples((subj, WARP.does_not_qualify_as, None)))


# --- 7.3 criteria ----------------------------------------------------------------------

def test_criteria_concepts_are_skos_and_match_the_enum(schemaview):
    g = Graph().parse(ROOT / "project" / "criteria_concepts.ttl")
    for name, pv in schemaview.get_enum("CriteriaConceptEnum").permissible_values.items():
        iri = URIRef(schemaview.expand_curie(pv.meaning))
        assert (iri, RDF.type, SKOS.Concept) in g and (iri, RDF.type, OWL.Class) not in g
    owl = Graph().parse(ROOT / "project" / "warp.owl.ttl")
    assert (CONCEPT.degraded_area, RDF.type, OWL.Class) not in owl
    assert not [s for s in owl.subjects() if str(s).endswith("CriteriaConceptEnum#degraded_area")]


def test_disagreeing_assessors_share_a_proposition(derived):
    p = next(x for x in derived["criteria_propositions"] if "stmt:assessor-c-0412-fed" in x["derived_from_statements"])
    assert sorted(p["derived_from_statements"]) == ["stmt:assessor-c-0412-fed", "stmt:assessor-e-0412-fed"]
    assert p["identity_rule_version"] == "warp-criteria-identity/1"
    other = next(x for x in derived["criteria_propositions"] if "stmt:assessor-d-0412-ref" in x["derived_from_statements"])
    assert other["id"] != p["id"]                         # another definition, another proposition


@pytest.mark.parametrize("change, message, kind", [
    (lambda s: s.__setitem__("object", "effective_restoration"), "operationalizes", "error"),
    (lambda s: s.__setitem__("subject", "node:fill_removal"), "subject is a site", "error"),
    (lambda s: s["predicate_qualifiers"].__setitem__("criteria_set", "crit:effective-restoration/fed-draft-1"),
     "assessment unit", "warning"),
])
def test_check_criteria(derived, strategies, change, message, kind):
    data = copy.deepcopy(derived)
    change(data["criteria_statements"][0])
    errors, warnings = check_sites.check([data, strategies])
    assert any(message in m for m in (errors if kind == "error" else warnings)), (errors, warnings)


def test_direction_is_allowed_only_where_it_is_the_verdict(schemaview):
    import derive_propositions as dp
    groups = dp.load_groups(SCHEMA, all_groups=True)
    slots = check_statements.verdict_slots(SCHEMA, groups)
    assert slots["CriteriaStatement"] == {"direction"}
    assert slots["CausalStatement"] == set()


def test_criteria_never_project(schemaview, derived):
    data = copy.deepcopy(derived)
    for p in data["criteria_propositions"]:
        p["scope"] = "universal"
    a = {"assessments": [{"id": "warp:assessment/x", "type": "SynthesisAssessment",
                          "proposition": data["criteria_propositions"][0]["id"], "direction": "supports",
                          "strength": "high"}]}
    g, report = project_owl.Projector(schemaview).run([data, a])
    assert not list(g.triples((None, RDFS.subClassOf, None)))


# --- Target 2 --------------------------------------------------------------------------

FED, REF = "crit:degraded-area/fed-draft-1", "crit:degraded-area/ref-ecosystem-1"
EFF = "crit:effective-restoration/fed-draft-1"


def test_three_buckets_and_the_effect_of_a_definition(derived):
    results, _ = t2.compute([derived], "CA-SK", 2026, [FED, REF], [EFF])
    by = {r["degraded"]: r for r in results}
    assert by[FED]["sites"] == {"supported": [], "contested": ["site:0412"], "unsupported": ["site:0517"]}
    assert by[REF]["sites"]["supported"] == ["site:0412", "site:0517"]
    assert by[REF]["projects"]["supported"] == [("proj:agreement-0412", "site:0412")]
    assert by[REF]["area"] == {"lower": 42.0, "upper": 42.0, "units": ["TODO:unit_hectare"]}
    assert by[FED]["area"]["upper"] == 0


def test_one_dispute_moves_a_site_to_contested_not_out(derived):
    data = copy.deepcopy(derived)
    data["criteria_statements"].append({**copy.deepcopy(data["criteria_statements"][2]),
                                        "id": "stmt:extra-dispute", "direction": "disputes"})
    import derive_propositions as dp
    dp.derive_all(data, SCHEMA)
    results, _ = t2.compute([data], "CA-SK", 2026, [REF], [EFF])
    assert "site:0412" in results[0]["sites"]["contested"]


def test_planned_work_needs_the_flag(derived):
    data = copy.deepcopy(derived)
    for p in data["implementation_propositions"]:
        for e in p["status_by_claimant"]:
            e["status"] = "planned"
    without, _ = t2.compute([data], "CA-SK", 2026, [REF], [EFF])
    with_flag, _ = t2.compute([data], "CA-SK", 2026, [REF], [EFF], include_planned=True)
    assert without[0]["projects"]["supported"] == [] and with_flag[0]["projects"]["supported"]


def test_upper_bound_is_capped_at_the_site_area(derived):
    data = copy.deepcopy(derived)
    p = next(x for x in data["implementation_propositions"] if x["about_project"] == "proj:agreement-0412")
    p["area_by_claimant"][0]["area"]["value"] = 500
    results, _ = t2.compute([data], "CA-SK", 2026, [REF], [EFF])
    assert results[0]["area"]["upper"] == 64.0 and results[0]["area"]["lower"] == 500.0


def test_restricted_sites_count_but_are_not_listed(derived):
    results, sites = t2.compute([derived], "CA-SK", 2026, [REF], [EFF])
    hidden = t2.render(results, sites, "CA-SK", 2026, show_restricted=False, include_planned=False)
    shown = t2.render(results, sites, "CA-SK", 2026, show_restricted=True, include_planned=False)
    assert "site:0412" not in hidden and "under restricted care" in hidden
    assert "site:0412" in shown
