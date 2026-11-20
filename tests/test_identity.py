"""Identity rule warp-prop-identity/4: per-group extras (Phase 2, D1, D4)."""

import copy

import pytest

import derive_propositions as dp

BASE = {"group": "demo", "extras": [], "ordered": {}, "rule": dp.RULE_VERSION,
        "templates": {}, "statements_slot": "demo_statements",
        "propositions_slot": "demo_propositions", "proposition_class": "DemoProposition"}


def group(extras=(), ordered=None, **kw):
    g = dict(BASE, extras=list(extras), ordered=ordered or {})
    g.update(kw)
    return g


def statement(sid="s1", **kw):
    s = {"id": sid, "subject": "node:a", "predicate": "suggested_to", "object": "node:b",
         "scope": "prototypical"}
    s.update(kw)
    return s


def test_no_extras_gives_the_rule_3_key():
    key, missing = dp.identity_key(group(), statement(), False, "prototypical")
    assert key == "demo|node:a|suggested_to|node:b|affirmed|prototypical"
    assert missing == []


def test_rule_version_is_not_hashed():
    """Same key string, same ID, whatever rule is recorded (D4, Q11)."""
    key = "causal|node:x|prevents|node:y|affirmed|assertional"
    assert dp.proposition_id(key) == dp.proposition_id(key)
    assert dp.RULE_VERSION not in key


def test_extras_are_appended_in_order():
    g = group(["predicate_qualifiers.guidance", "place"])
    s = statement(predicate_qualifiers={"guidance": "avoid"}, place=["ISO3166-2:US-FL"])
    key, missing = dp.identity_key(g, s, False, "prototypical")
    assert key.endswith('|predicate_qualifiers.guidance="avoid"|place=["ISO3166-2:US-FL"]')
    assert missing == []


def test_different_extras_split_propositions():
    g = group(["predicate_qualifiers.guidance"])
    do, _ = dp.identity_key(g, statement(predicate_qualifiers={"guidance": "do"}), False, "prototypical")
    avoid, _ = dp.identity_key(g, statement(predicate_qualifiers={"guidance": "avoid"}), False, "prototypical")
    assert dp.proposition_id(do) != dp.proposition_id(avoid)


def test_missing_extra_is_an_explicit_null_and_still_groups():
    g = group(["place"])
    k1, m1 = dp.identity_key(g, statement("s1"), False, "prototypical")
    k2, m2 = dp.identity_key(g, statement("s2", place=[]), False, "prototypical")
    assert k1 == k2 and k1.endswith("|place=null")
    assert m1 == ["place"] and m2 == ["place"]


def test_structured_extras_hash_the_same_in_any_key_order():
    g = group(["predicate_qualifiers.scale"])
    a = statement(predicate_qualifiers={"scale": {"value": 600, "unit": "TODO:unit_hectare"}})
    b = statement(predicate_qualifiers={"scale": {"unit": "TODO:unit_hectare", "value": 600}})
    assert dp.identity_key(g, a, False, "x")[0] == dp.identity_key(g, b, False, "x")[0]


def test_unordered_lists_are_sorted_ordered_lists_are_not():
    unordered = group(["place"])
    ordered = group(["place"], ordered={"place": True})
    s1 = statement(place=["wd:Q2", "wd:Q1"])
    s2 = statement(place=["wd:Q1", "wd:Q2"])
    assert dp.identity_key(unordered, s1, False, "x")[0] == dp.identity_key(unordered, s2, False, "x")[0]
    assert dp.identity_key(ordered, s1, False, "x")[0] != dp.identity_key(ordered, s2, False, "x")[0]


def test_derive_group_copies_extras_and_counts_missing():
    g = group(["predicate_qualifiers.guidance"], rule="warp-demo/1")
    data = {"demo_statements": [
        statement("s1", predicate_qualifiers={"guidance": "do"}),
        statement("s2", predicate_qualifiers={"guidance": "do"}),
        statement("s3", predicate_qualifiers={"guidance": "avoid"}),
        statement("s4"),                                   # guidance missing
        statement("s5", scope="unclear"),                  # not grouped
    ]}
    props, skipped, incomplete = dp.derive_group(data, g, {})
    assert len(props) == 3
    by_stmts = {tuple(p["derived_from_statements"]): p for p in props}
    assert by_stmts[("s1", "s2")]["predicate_qualifiers"] == {"guidance": "do"}
    assert "predicate_qualifiers" not in by_stmts[("s4",)]          # the null is never written
    assert all(p["identity_rule_version"] == "warp-demo/1" for p in props)
    assert skipped == ["s5"] and incomplete == ["s4"]
    assert data["demo_statements"][0]["proposition"] == data["demo_statements"][1]["proposition"]


def test_templates_can_use_extras():
    text = dp.render({"suggested_to": "{guidance}: {subject} for {object}"}, {"node:a": "A", "node:b": "B"},
                     "node:a", "suggested_to", "node:b", False, "prototypical",
                     {"predicate_qualifiers.guidance": "avoid"})
    assert text == "Typically, avoid: A for B."


def test_registry_reads_extras_from_annotations(tmp_path, schemaview):
    """A group gains extras by annotation alone; no code change."""
    import yaml
    from conftest import SCHEMA
    src = yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))
    anns = src["classes"]["InteractionStatement"]["annotations"]
    anns["warp_identity_extras"] = "predicate_qualifiers.effect_on_subject place"
    anns["warp_identity_rule"] = "warp-demo-identity/1"
    for f in SCHEMA.parent.glob("upstream/*.yaml"):
        (tmp_path / "upstream").mkdir(exist_ok=True)
        (tmp_path / "upstream" / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    p = tmp_path / "warp.yaml"
    p.write_text(yaml.safe_dump(src, sort_keys=False), encoding="utf-8")
    g = {x["group"]: x for x in dp.load_groups(p)}["interaction"]
    assert g["extras"] == ["predicate_qualifiers.effect_on_subject", "place"]
    assert g["rule"] == "warp-demo-identity/1"
    assert g["ordered"] == {"predicate_qualifiers.effect_on_subject": False, "place": False}


def test_existing_groups_declare_no_extras():
    """D1: causal and interaction keep their keys, so no existing ID moves."""
    from conftest import SCHEMA
    groups = {g["group"]: g for g in dp.load_groups(SCHEMA)}
    assert groups["causal"]["extras"] == [] and groups["interaction"]["extras"] == []


def test_rederiving_is_idempotent():
    from conftest import EXAMPLES, SCHEMA, load_yaml
    once = load_yaml(EXAMPLES / "bloodroot_statements.yaml")
    dp.derive_all(once, SCHEMA)
    twice = copy.deepcopy(once)
    dp.derive_all(twice, SCHEMA)
    assert once == twice
