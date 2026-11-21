"""The cost group (Phase 6, warp-proposals-0.4.html section 8)."""

import copy

import pytest
from rdflib import Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD

import check_cost
import derive_propositions as dp
import export_rdf
import project_owl
import report_cost_completeness as rcc
import transfer_costs as tc
from conftest import EXAMPLES, ROOT, SCHEMA, load_yaml

WARP = Namespace("https://w3id.org/ecoweaver/warp/")
NODE = Namespace("https://w3id.org/causal-mosaic/node/")
STMT = "https://w3id.org/ecoweaver/warp/statement/"


@pytest.fixture(scope="module")
def derived():
    return load_yaml(EXAMPLES / "cost_statements.derived.yaml")


@pytest.fixture(scope="module")
def strategies():
    return load_yaml(EXAMPLES / "strategy_statements.derived.yaml")


@pytest.fixture(scope="module")
def rule():
    return tc.load_rule(ROOT / "config" / "cost_transfer" / "warp-cost-transfer-1.yaml")


def stmt(data, sid):
    return next(s for s in data["cost_statements"] if s["id"] == sid)


def prop_of(data, sid):
    return next(p for p in data["cost_propositions"] if sid in p["derived_from_statements"])


# --- identity ---------------------------------------------------------------------

def test_group_key_has_place_phase_and_level():
    g = {x["group"]: x for x in dp.load_groups(SCHEMA)}["cost"]
    assert g["extras"] == ["place", "predicate_qualifiers.phase", "predicate_qualifiers.reporting_level"]


def test_two_initial_costings_meet_and_maintenance_stays_apart(derived):
    initial = prop_of(derived, "stmt:agency-c-removal-initial-1")
    assert sorted(initial["derived_from_statements"]) == ["stmt:agency-c-removal-initial-1",
                                                          "stmt:agency-c-removal-initial-2"]
    assert initial["predicate_qualifiers"] == {"phase": "initial", "reporting_level": "intervention"}
    assert prop_of(derived, "stmt:agency-c-removal-maintenance")["id"] != initial["id"]


# --- validation and checks ------------------------------------------------------

def test_examples_pass_check_cost(derived, strategies):
    transferred = load_yaml(EXAMPLES / "cost_statements.transferred.yaml")
    assert check_cost.check([derived, strategies, transferred]) == []


@pytest.mark.parametrize("sid, change, message", [
    ("stmt:inpa-wattle-cost", lambda s: s["predicate_qualifiers"].pop("scale"), "needs scale"),
    ("stmt:inpa-wattle-cost", lambda s: s["predicate_qualifiers"].pop("includes_categories"), "needs includes_categories"),
    ("stmt:inpa-wattle-cost", lambda s: s.__setitem__("object", "unknown"), "not an object"),
    ("stmt:inpa-wattle-cost", lambda s: s["predicate_qualifiers"]["amount"].pop("price_year"), "needs price_year"),
    ("stmt:inpa-wattle-cost", lambda s: s.__setitem__("object", "node:manual_removal_of_acacia_saligna"), "needs a cost category"),
    ("stmt:inpa-wattle-cost", lambda s: s.__setitem__("transferred_from", "stmt:x"), "requires transfer_rule"),
    ("stmt:practitioner-drill-vs-plugs", lambda s: s["predicate_qualifiers"].pop("ratio"), "needs a ratio"),
    ("stmt:practitioner-drill-vs-plugs", lambda s: s.__setitem__("object", "total"), "not the category"),
    ("stmt:land-trust-strategy-follow-up-labour",
     lambda s: s["predicate_qualifiers"].__setitem__("covers_roles", ["monitoring"]), "are not roles"),
    ("stmt:inpa-wattle-cost", lambda s: s["predicate_qualifiers"].__setitem__("covers_roles", ["follow_up"]),
     "needs a strategy subject"),
])
def test_check_cost_rules(derived, strategies, sid, change, message):
    data = copy.deepcopy(derived)
    change(stmt(data, sid))
    errors = check_cost.check([data, strategies])
    assert any(message in e for e in errors), errors


def test_cost_qualifiers_need_amount_effort_or_ratio(validator):
    data = load_yaml(EXAMPLES / "cost_statements.yaml")
    q = stmt(data, "stmt:practitioner-drill-vs-plugs")["predicate_qualifiers"]
    q.pop("ratio")
    assert validator.validate(data, "StatementSet").results


def test_currency_is_iso_4217(validator):
    data = load_yaml(EXAMPLES / "cost_statements.yaml")
    stmt(data, "stmt:inpa-wattle-cost")["predicate_qualifiers"]["amount"]["currency"] = "nis"
    assert validator.validate(data, "StatementSet").results


# --- RDF ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def graph(schemaview, derived, strategies):
    g, _ = export_rdf.export(schemaview, [derived, strategies,
                                          load_yaml(EXAMPLES / "cost_statements.transferred.yaml")])
    return g


def test_category_moves_into_the_predicate_and_the_amount_is_the_object(graph):
    amount = URIRef(STMT + "inpa-wattle-cost/predicate_qualifiers/amount")
    assert (NODE.cut_treat_acacia_saligna_coastal_reserves, WARP.incurs_total_cost, amount) in graph
    assert (amount, RDF.type, WARP.MonetaryAmount) in graph
    assert graph.value(amount, WARP.value).datatype == XSD.decimal
    assert graph.value(amount, WARP.price_year) == Literal(2008, datatype=XSD.integer)
    assert not list(graph.triples((None, WARP.incurs_cost, None)))


def test_no_costcat_iris_and_no_unknown(graph):
    assert not any("costcat" in str(t) for triple in graph for t in triple)
    assert not any(str(t).endswith("CostCategoryEnum#unknown") for triple in graph for t in triple)


def test_records_name_the_sub_property_and_the_category(graph):
    s = URIRef(STMT + "land-trust-strategy-follow-up-labour")
    assert graph.value(s, WARP.predicate) == WARP.incurs_labour_cost
    assert graph.value(s, WARP.object) == URIRef(f"{WARP}CostCategoryEnum#labour")
    # effort-only costing: the relation's object is the effort quantity
    assert (None, WARP.incurs_labour_cost, URIRef(f"{s}/predicate_qualifiers/effort/0")) in graph


def test_relative_cost_relates_two_nodes(graph):
    assert (NODE.drill_seeding_native_grassland_mix, WARP.costs_relative_to,
            NODE.planting_plugs_native_grassland) in graph


def test_transferred_amount_cites_its_source_amount(graph):
    derived_amount = URIRef(STMT + "transfer/warp-cost-transfer-1/inpa-wattle-cost/predicate_qualifiers/amount")
    source_amount = graph.value(derived_amount, WARP.derived_from_amount)
    assert source_amount == URIRef(STMT + "inpa-wattle-cost/predicate_qualifiers/amount")
    assert (source_amount, RDF.type, WARP.MonetaryAmount) in graph


def test_costs_never_project(schemaview, derived):
    data = copy.deepcopy(load_yaml(EXAMPLES / "cost_statements.yaml"))
    for s in data["cost_statements"]:
        s["scope"], s["modality"] = "universal", "observed"
    dp.derive_all(data, SCHEMA)
    a = {"assessments": [{"id": f"warp:assessment/c{i}", "type": "SynthesisAssessment", "proposition": p["id"],
                          "direction": "supports", "strength": "high"} for i, p in enumerate(data["cost_propositions"])]}
    g, report = project_owl.Projector(schemaview).run([data, a])
    assert report["no_projection"]["cost"] and not list(g.triples((None, RDFS.subClassOf, None)))


# --- transfer -----------------------------------------------------------------------

def test_cpi_only_transfer(derived, rule):
    out = tc.transfer(stmt(derived, "stmt:land-trust-strategy-total"), rule)
    amount = out["predicate_qualifiers"]["amount"]
    assert amount == {"value": 48960.0, "currency": "CAD", "price_year": 2026, "adjustment": "inflation",
                      "derived_from_amount": "stmt:land-trust-strategy-total/predicate_qualifiers/amount"}
    assert out["transfer_steps"] == ["indexed CAD 2025 to 2026 (x1.0200)"]


def test_currency_conversion(derived, rule):
    out = tc.transfer(stmt(derived, "stmt:inpa-wattle-cost"), rule)
    amount = out["predicate_qualifiers"]["amount"]
    assert amount["value"] == 13200.0 and amount["conversion_rate"] == 0.5
    assert out["transfer_steps"] == ["indexed ILS 2008 to 2026 (x1.5000)", "converted ILS to CAD at 0.5"]
    assert out["place"] == ["ISO3166-2:CA-SK"] and out["modality"] == "inferred"
    assert out["transferred_from"] == "stmt:inpa-wattle-cost" and out["transfer_rule"] == "warp-cost-transfer/1"
    assert out["contributions"][0]["contributor"] == "warp:agent/ecoweaver-synthesis"


def test_labour_is_repriced_from_effort(derived, rule):
    out = tc.transfer(stmt(derived, "stmt:land-trust-strategy-follow-up-labour"), rule)
    assert out["predicate_qualifiers"]["amount"]["value"] == 4800.0
    assert out["transfer_steps"][0].startswith("labour re-priced from effort: 12 person-days")
    assert "derived_from_amount" not in out["predicate_qualifiers"]["amount"]


@pytest.mark.parametrize("change, why", [
    (lambda q: q["amount"].pop("price_year"), "price_year"),
    (lambda q: q["amount"].pop("value"), "no amount value"),
    (lambda q: q["amount"].__setitem__("currency", "EUR"), "no EUR price index"),
])
def test_refusals(derived, rule, change, why):
    source = copy.deepcopy(stmt(derived, "stmt:inpa-wattle-cost"))
    change(source["predicate_qualifiers"])
    with pytest.raises(tc.TransferRefused, match=why):
        tc.transfer(source, rule)


def test_sources_are_never_modified_and_refusals_are_reported(derived, rule):
    before = copy.deepcopy(derived)
    selection = {"statements": ["stmt:inpa-wattle-cost", "stmt:fwc-invasive-program", "stmt:no-such"]}
    out, refused = tc.run([derived], selection, rule)
    assert derived == before
    assert [s["transferred_from"] for s in out] == ["stmt:inpa-wattle-cost"]
    assert {sid for sid, _ in refused} == {"stmt:fwc-invasive-program", "stmt:no-such"}


def test_new_rule_version_means_new_ids(derived, rule):
    v2 = dict(rule, id="warp-cost-transfer/2")
    a = tc.transfer(stmt(derived, "stmt:inpa-wattle-cost"), rule)
    b = tc.transfer(stmt(derived, "stmt:inpa-wattle-cost"), v2)
    assert a["id"] != b["id"] and b["transfer_rule"] == "warp-cost-transfer/2"


def test_transferred_file_is_current(derived, rule):
    selection = load_yaml(ROOT / "config" / "cost_transfer" / "selection.yaml")
    out, _ = tc.build_set([derived], selection, rule)
    assert out == load_yaml(EXAMPLES / "cost_statements.transferred.yaml"), "run make derive"



# --- completeness ---------------------------------------------------------------------

def test_completeness_report(derived):
    results = {r["statement"]: r for r in rcc.analyse([derived])}
    inpa = results["stmt:inpa-wattle-cost"]
    assert inpa["missing_required"] == []
    assert any("[unknown]" in f for f in inpa["flags"])
    fwc = results["stmt:fwc-invasive-program"]
    assert "amount.price_year" in fwc["missing_required"] and any("no value" in f for f in fwc["flags"])
    assert inpa["score"] > fwc["score"]
    # stated_goal is found through reportedIn and the study result
    assert ("1 Objective and outcome", "stated_goal (study result)", "recommended", True) in inpa["rows"]


def test_payment_rate_is_flagged(derived):
    data = copy.deepcopy(derived)
    stmt(data, "stmt:inpa-wattle-cost")["predicate_qualifiers"]["cost_basis"] = "payment_rate"
    r = {x["statement"]: x for x in rcc.analyse([data])}["stmt:inpa-wattle-cost"]
    assert any("payment is not necessarily a cost" in f and "no cost_bearer" in f for f in r["flags"])
