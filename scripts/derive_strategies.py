#!/usr/bin/env python3
"""Derive canonical management strategy nodes (WARP).

    python scripts/derive_strategies.py IN.yaml OUT.yaml [--previous OLD.derived.yaml]

Annotators describe strategies in `strategy_definitions`, each under a local
node ID. This script computes each definition's canonical node under rule
warp-strategy-identity/1, groups definitions that describe the same strategy,
and rewrites every reference to a local strategy node so it points at the
canonical one. It runs before derive_propositions.py, so statements about two
descriptions of the same work meet in one proposition (R9).

Rule warp-strategy-identity/1
-----------------------------
1. Flatten nested strategies one level. A component whose action is another
   strategy (defined in the same set) at outer step k, with inner steps
   1..m, becomes that strategy's components at steps k..k+m-1, and every
   later outer step shifts by m-1. Parallel parts (a shared step) keep
   sharing it. A nested strategy marked optional makes all its parts
   optional. Nesting deeper than one level, and cycles, are errors.
2. The key is the sorted list of (step, action node ID) pairs of the
   non-optional components after flattening. Lags, repeats, roles, labels and
   optional parts are not in the key: they are aggregated, not identity.
3. The canonical node is node:strategy-<first 12 hex of sha1(key)>.

So order is part of identity (earthworks-then-seeding and
seeding-then-earthworks are two strategies), and the canonical ID is a
content hash: change a required part and the ID changes. When a previous
derived file is given (by default the output file, if it exists), a
definition whose canonical node changed records the old one in `replaces`,
and expand_nodes.py writes the old IRI as deprecated and replaced by the new
one. Strategy class IRIs are stable only while their parts are.

The derived output also gets one CausalNode record per canonical strategy
(named after the first definition that has it), so references resolve.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import warp_schema as ws  # noqa: E402

RULE_VERSION = "warp-strategy-identity/1"
CANONICAL_PREFIX = "node:strategy-"


class StrategyError(ValueError):
    """A strategy definition that cannot be flattened or keyed."""


def definitions(data):
    return {d["node"]: d for d in data.get("strategy_definitions") or []}


def flatten(defn, defs, _seen=None):
    """Components of a strategy after flattening one level of nesting.

    Returns a list of dicts with step (renumbered), action, optional and the
    component's own fields."""
    seen = (_seen or set()) | {defn["node"]}
    comps = defn.get("components") or []
    steps = sorted({c["step"] for c in comps})
    width = {}
    for s in steps:
        w = 1
        for c in comps:
            if c["step"] != s or c["action"] not in defs:
                continue
            inner = defs[c["action"]]
            if c["action"] in seen:
                raise StrategyError(f"{defn['node']}: cycle through {c['action']}")
            for ic in inner.get("components") or []:
                if ic["action"] in defs:
                    if ic["action"] in seen or ic["action"] == c["action"]:
                        raise StrategyError(f"{defn['node']}: cycle through {ic['action']}")
                    raise StrategyError(
                        f"{defn['node']}: {c['action']} nests {ic['action']}; strategies nest one level only")
            w = max(w, max((ic["step"] for ic in inner.get("components") or []), default=1))
        width[s] = w
    start, pos = {}, 1
    for s in steps:
        start[s] = pos
        pos += width[s]
    out = []
    for c in comps:
        base = start[c["step"]]
        if c["action"] in defs:
            for ic in defs[c["action"]].get("components") or []:
                fc = dict(ic)
                fc["step"] = base + ic["step"] - 1
                fc["optional"] = bool(ic.get("optional") or c.get("optional"))
                fc["nested_in"] = c["action"]
                out.append(fc)
        else:
            fc = dict(c)
            fc["step"] = base
            fc["optional"] = bool(c.get("optional"))
            out.append(fc)
    return sorted(out, key=lambda c: (c["step"], c["action"]))


def identity_key(flat):
    pairs = sorted((c["step"], c["action"]) for c in flat if not c.get("optional"))
    if not pairs:
        raise StrategyError("no required components")
    return json.dumps(pairs, separators=(",", ":"))


def canonical_id(key):
    return CANONICAL_PREFIX + hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def rewrite_references(sv, data, mapping):
    """Point every reference to a local strategy node at its canonical node.

    The definitions' own `node` (their local ID) and the annotators' node
    records are left alone; component actions inside other strategies, and
    statement subjects and objects, are rewritten."""
    count = 0
    for item in list(ws.walk(sv, data, "StatementSet")):
        slot = item.slot
        if not isinstance(item.value, str) or item.value not in mapping:
            continue
        if slot.identifier or not (ws.is_reference(sv, slot) or slot.range == "CausalNode"):
            continue
        val = item.owner[slot.name]
        if isinstance(val, list):
            item.owner[slot.name] = [mapping.get(v, v) if isinstance(v, str) else v for v in val]
        else:
            item.owner[slot.name] = mapping[val]
        count += 1
    return count


def derive(data, sv=None, previous=None):
    """Derive canonical strategies in place. Returns a report dict."""
    sv = sv or ws.load()
    defs = definitions(data)
    if not defs:
        return {"strategies": {}, "rewritten": 0}
    prev_canon = {d["node"]: d.get("canonical_node") for d in (previous or {}).get("strategy_definitions") or []}
    prev_replaces = {d["node"]: d.get("replaces") or [] for d in (previous or {}).get("strategy_definitions") or []}
    names = {n["id"]: n.get("name", n["id"]) for n in data.get("nodes") or []}
    mapping, groups = {}, {}
    for local, d in defs.items():
        flat = flatten(d, defs)
        key = identity_key(flat)
        canon = canonical_id(key)
        d["identity_key"] = key
        d["identity_rule_version"] = RULE_VERSION
        d["canonical_node"] = canon
        old = list(prev_replaces.get(local, []))
        if prev_canon.get(local) and prev_canon[local] != canon and prev_canon[local] not in old:
            old.append(prev_canon[local])
        if old:
            d["replaces"] = old
        else:
            d.pop("replaces", None)
        mapping[local] = canon
        groups.setdefault(canon, []).append(local)

    nodes = data.setdefault("nodes", [])
    have = {n["id"] for n in nodes}
    for canon, locals_ in sorted(groups.items()):
        if canon in have:
            continue
        first = locals_[0]
        nodes.append({
            "id": canon,
            "name": names.get(first, first),
            "entity_type": "management_intervention",
            "entity_term": "management strategy (derived by " + RULE_VERSION + ")",
        })
    rewritten = rewrite_references(sv, data, mapping)
    return {"strategies": groups, "rewritten": rewritten}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--previous", type=Path,
                        help="an earlier derived file, to record superseded canonical IDs "
                             "(default: the output file, if it exists)")
    parser.add_argument("--schema", type=Path, default=ws.DEFAULT_SCHEMA)
    args = parser.parse_args(argv)

    data = yaml.safe_load(args.input.read_text(encoding="utf-8")) or {}
    prev_path = args.previous or (args.output if args.output.exists() else None)
    previous = yaml.safe_load(prev_path.read_text(encoding="utf-8")) if prev_path else None
    try:
        report = derive(data, ws.load(args.schema), previous)
    except StrategyError as err:
        sys.exit(f"ERROR {err}")
    args.output.write_text(
        "# GENERATED by scripts/derive_strategies.py (" + RULE_VERSION + ") and "
        "scripts/derive_propositions.py. Do not edit derived records by hand.\n"
        + yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )
    groups = report["strategies"]
    print(f"strategies: {len(groups)} canonical node(s) under {RULE_VERSION}, "
          f"{report['rewritten']} reference(s) rewritten")
    for canon, locals_ in sorted(groups.items()):
        print(f"  {canon}  <- {', '.join(locals_)}")


if __name__ == "__main__":
    main()
