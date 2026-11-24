"""Whole statements in plain language (scripts/render_statements.py,
config/rosetta.yaml): every slot has a place, every value is rendered."""

import copy
from pathlib import Path

import pytest
import yaml

import render_statements as rs
from conftest import EXAMPLES, ROOT, load_yaml

CONFIG = ROOT / "config" / "rosetta.yaml"
FILES = sorted(EXAMPLES.glob("*.derived.yaml")) + [EXAMPLES / "cost_statements.transferred.yaml"] \
    + sorted(EXAMPLES.glob("*_assessment.yaml"))


def renderer(config=CONFIG, schema=rs.ws.DEFAULT_SCHEMA):
    r = rs.Renderer(schema, config)
    r.add_files(load_yaml(f) for f in FILES)
    return r


@pytest.fixture(scope="module")
def r():
    return renderer()


def statement(sid):
    for f in FILES:
        data = load_yaml(f)
        for key, items in data.items():
            if key.endswith("_statements"):
                for st in items:
                    if st.get("id") == sid:
                        return copy.deepcopy(st)
    raise KeyError(sid)


def render(r, sid, **changes):
    st = statement(sid)
    st.update(changes)
    return r.render_statement(st, st["type"])


def edited_config(tmp_path, edit):
    data = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    edit(data)
    path = tmp_path / "rosetta.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


# --- coverage --------------------------------------------------------------------

def test_config_covers_every_slot(r):
    assert rs.check_config(r) == []


@pytest.mark.parametrize("profile", sorted((ROOT / "project" / "profiles").glob("warp_*.yaml")),
                         ids=lambda p: p.stem)
def test_config_covers_every_profile(profile):
    assert rs.check_config(renderer(schema=profile)) == []


def test_every_example_value_is_rendered(r):
    count = 0
    for f in FILES:
        for g, cls, st in rs.statement_sets(r, f, load_yaml(f)):
            res = r.render_statement(st, cls)
            assert res["missing"] == [], (st["id"], res["missing"])
            assert res["sentence"].endswith(".")
            count += 1
    assert count >= 49


def test_cited_study_results_are_rendered(r):
    st = statement("warp:statement/kramer1995-c1")
    refs = list(rs.evidence_items(r, st))
    assert "warp:result/kramer1995-site-1992" in refs
    cls, obj = r.index["warp:result/kramer1995-site-1992"]
    out = r.render_object(obj, cls, "")
    assert "mean 0.05 larvae per dip" in out.text
    assert [p for p in rs.leaves(obj, "") if p not in out.used] == []


def test_a_slot_without_a_place_is_reported(tmp_path):
    def drop_place(data):
        data["classes"]["EcoStatement"]["sentence"].remove("in {place}")
    problems = rs.check_config(renderer(config=edited_config(tmp_path, drop_place)))
    assert any(p.startswith("CausalStatement.place:") for p in problems)


def test_a_template_naming_no_slot_is_reported(tmp_path):
    def typo(data):
        data["classes"]["Quantity"]["template"] = "{valeu}[ {unit}]"
    problems = rs.check_config(renderer(config=edited_config(tmp_path, typo)))
    assert any("'valeu'" in p for p in problems)


def test_a_predicate_without_tenses_is_reported(tmp_path):
    def forget(data):
        del data["verbs"]["prevents"]
    problems = rs.check_config(renderer(config=edited_config(tmp_path, forget)))
    assert any("predicate prevents" in p for p in problems)


def test_a_value_in_an_unused_slot_is_not_rendered(r):
    res = render(r, "stmt:burn-study-c1", score=0.5, description="a note")
    assert {"score", "description"} <= set(res["missing"])


# --- templates ----------------------------------------------------------------------

def test_optional_segments_defaults_and_filters(r):
    q = {"value": 42, "unit": "TODO:unit_hectare"}
    assert r.render_object(q, "Quantity", "").text == "42 TODO:unit_hectare"
    assert r.render_object({"value": 42}, "Quantity", "").text == "42"
    amount = {"currency": "USD"}
    assert r.render_object(amount, "MonetaryAmount", "").text == "USD (amount not transcribed)"
    meta = {"contributions": [{"role": "annotator", "contributor": "orcid:0000-0000-0000-0000"},
                              {"role": "reviewer", "contributor": "orcid:0000-0000-0000-0000"}]}
    text = r.render_object(meta, "EcoRecordMetadata", "").text
    assert text.startswith("annotated by TODO: annotator; reviewed by TODO: annotator")


@pytest.mark.parametrize("bad", ["{a", "[{a}", "{a}]", "{a b}"])
def test_malformed_templates_are_refused(bad):
    with pytest.raises((rs.RosettaError, ValueError)):
        rs.parse(bad)


# --- the claim ------------------------------------------------------------------------

def test_verb_forms(r):
    f = r.forms("prevents", "{subject} prevents {object}")
    assert f["negative"] == "{subject} does not prevent {object}"
    assert f["past"] == "{subject} prevented {object}"
    assert f["past_negative"] == "{subject} did not prevent {object}"
    f = r.forms("intolerant_of", "{subject} is intolerant of {object}")
    assert (f["negative"], f["past"]) == ("{subject} is not intolerant of {object}",
                                          "{subject} was intolerant of {object}")


def test_a_particular_case_is_in_the_past(r):
    s = render(r, "warp:statement/kramer1995-c1")["sentence"]
    assert "in a particular case Tidal restoration of marsh prevented Larval density" in s
    assert "compared with a pre-treatment baseline" in s


def test_a_typical_case_is_in_the_present(r):
    s = render(r, "stmt:usda-bogr-ph")["sentence"]
    assert "typically Bouteloua gracilis tolerates pH of soil" in s
    assert "from 6.0 to 8.5" in s


def test_an_anticipated_case_is_not_put_in_the_past(r):
    s = render(r, "stmt:ms-11-causal", scope="assertional")["sentence"]
    assert "prevents Abundance" in s


def test_negated_statements(r):
    assert "does not eat" in render(r, "warp:statement/notebook-i1")["sentence"]
    assert "did not prevent" in render(r, "stmt:inpa-wattle-seedlings-persist")["sentence"]


def test_criteria_direction(r):
    assert "did not qualify as degraded area" in render(r, "stmt:assessor-e-0412-fed")["sentence"]
    assert "qualified as degraded area" in render(r, "stmt:assessor-c-0412-fed")["sentence"]
    s = render(r, "stmt:assessor-c-0412-fed", direction="neutral")["sentence"]
    assert "it is left open whether Agreement site 0412 qualified" in s


def test_recommendation_uses_guidance_and_justification(r):
    s = render(r, "stmt:burn-avoid-agency")["sentence"]
    assert "one should avoid Prescribed burning of grassland" in s
    assert "justified by the claim that typically, prescribed burning" in s


def test_negation_falls_back_without_a_verb(r):
    s = render(r, "stmt:burn-do-plan", direction="disputes")["sentence"]
    assert "it is not the case that one should carry out" in s


# --- labels and the report ----------------------------------------------------------

def test_references_read_by_label(r):
    res = render(r, "stmt:practitioner-drill-vs-plugs")
    assert "costs relative to Planting native grassland plugs" in res["sentence"]
    res = render(r, "stmt:inpa-wattle-cost")
    assert "in Mediterranean coastal Israel" in res["sentence"]
    assert res["unlabelled"] == ["TODO:unit_hectare"]


def test_quoted_and_elsewhere_values_are_kept_out_of_the_sentence(r):
    res = render(r, "warp:statement/kramer1995-c1")
    assert res["aside"]["original_text"][0] == "quoted"
    assert "98.7" in str(res["aside"]["predicate_qualifiers.effect_strength.quantitative_numeric"][1])
    assert "(results)" in res["aside"]["source_spans"][1]


def test_cli_writes_the_report(tmp_path, capsys):
    out = tmp_path / "statements.md"
    rs.main([*map(str, FILES), "--check", "--out", str(out)])
    text = out.read_text(encoding="utf-8")
    assert "### `warp:statement/kramer1995-c1` (CausalStatement)" in text
    assert "Evidence item `warp:result/kramer1995-site-1991`" in text
    assert "Not rendered" not in text
    assert "every slot covered" in capsys.readouterr().out
