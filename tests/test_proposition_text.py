"""Proposition and project text names nodes across files and reads enum
values as words; text is not identity, so no ID moves."""

import copy

import derive_projects as dpj
import derive_propositions as dp
from conftest import EXAMPLES, SCHEMA, load_yaml


def test_names_from_keeps_the_first_name():
    a = {"nodes": [{"id": "node:x", "name": "X from a"}, {"id": "node:y"}]}
    b = {"nodes": [{"id": "node:x", "name": "X from b"}, {"id": "node:y", "name": "Y"}]}
    assert dp.names_from(a, b) == {"node:x": "X from a", "node:y": "Y"}


def test_word():
    names = {"node:x": "Planting"}
    assert dp.word("node:x", names) == "Planting"
    assert dp.word("degraded_area", names) == "degraded area"
    assert dp.word("TODO:unit_hectare", names) == "TODO:unit_hectare"


def test_enum_objects_read_as_words():
    text = dp.render({"qualifies_as": "{subject} qualifies as {object}"}, {"site:1": "Site 1"},
                     "site:1", "qualifies_as", "effective_restoration", False, "assertional")
    assert text == "In a particular case, site 1 qualifies as effective restoration."


def cost_set():
    return load_yaml(EXAMPLES / "cost_statements.yaml")


def strategy_names():
    return dp.names_from(load_yaml(EXAMPLES / "strategy_statements.derived.yaml"))


def test_a_strategy_in_another_file_is_named():
    alone, named = cost_set(), cost_set()
    dp.derive_all(alone, SCHEMA)
    dp.derive_all(named, SCHEMA, strategy_names())
    text = {p["id"]: p["propositionText"] for p in named["cost_propositions"]}
    assert any("earthworks then seeding then mowing incurs total cost" in t for t in text.values())
    assert not any("node:strategy-" in t for t in text.values())
    # Text only: the same propositions, the same IDs.
    assert [p["id"] for p in alone["cost_propositions"]] == list(text)


def test_own_nodes_win_over_names():
    data = cost_set()
    names = {"node:manual_removal_of_acacia_saligna": "Something else"}
    dp.derive_all(data, SCHEMA, names)
    texts = " ".join(p["propositionText"] for p in data["cost_propositions"])
    assert "manual removal of Acacia saligna" in texts
    assert "Something else" not in texts


def test_project_names_use_names_from_other_files():
    data = load_yaml(EXAMPLES / "implementation_statements.yaml")
    import derive_strategies as ds
    import warp_schema as ws
    ds.derive(data, ws.load(SCHEMA))
    dpj.derive(data, None, names=strategy_names())
    projects = [n["name"] for n in data["nodes"] if n["id"].startswith("proj:")]
    assert projects and all("Earthworks then seeding then mowing at" in n for n in projects)


def test_cli_names(tmp_path):
    src = tmp_path / "cost.yaml"
    src.write_text((EXAMPLES / "cost_statements.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    out = tmp_path / "cost.derived.yaml"
    dp.main([str(src), str(out), "--names", str(EXAMPLES / "strategy_statements.derived.yaml")])
    assert "node:strategy-" not in "".join(
        p["propositionText"] for p in load_yaml(out)["cost_propositions"])
