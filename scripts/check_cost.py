#!/usr/bin/env python3
"""Check cost statements for rules LinkML cannot express (R3, R4, R16, R17).

    python scripts/check_cost.py FILE.yaml [FILE.yaml ...]

Pass statement sets together with the sets that hold the nodes, agents and
statements they cite. Errors (exit status 1):

  - incurs_cost: the object is a cost category (not `unknown`, which is only
    for includes_categories); amount or effort is given; scale and phase are
    given.
  - incurs_cost with object `total`: includes_categories is given (`unknown`
    is allowed and common).
  - costs_relative_to: ratio is given and the object is a node, not a
    category; scale is not required.
  - an amount with a value needs currency (schema) and price_year. An amount
    with no value records that the source gives a figure not yet transcribed:
    allowed here, flagged by report_cost_completeness.py, refused by
    transfer_costs.py.
  - transferred_from requires transfer_rule.
  - covers_roles needs a strategy subject, and each role must be a role of one
    of that strategy's components.
"""

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import derive_propositions as dp  # noqa: E402
import warp_schema as ws  # noqa: E402

UNKNOWN = "unknown"


def index(sets):
    nodes, roles = set(), {}
    for data in sets:
        nodes |= {n["id"] for n in data.get("nodes") or []}
        for d in data.get("strategy_definitions") or []:
            rs = {c.get("role") for c in d.get("components") or [] if c.get("role")}
            for key in (d["node"], d.get("canonical_node")):
                if key:
                    roles.setdefault(key, set()).update(rs)
    return nodes, roles


def check(sets, schema=dp.DEFAULT_SCHEMA):
    sv = ws.load(schema)
    categories = set(sv.get_enum("CostCategoryEnum").permissible_values)
    groups = {g["group"]: g for g in dp.load_groups(schema, all_groups=True)}
    g = groups.get("cost")
    if g is None:
        return []
    nodes, roles = index(sets)
    errors = []
    for data in sets:
        for s in data.get(g["statements_slot"]) or []:
            sid, pred, obj = s.get("id", "?"), s.get("predicate"), s.get("object")
            q = s.get("predicate_qualifiers") or {}
            if pred == "incurs_cost":
                if obj not in categories:
                    errors.append(f"{sid}: incurs_cost needs a cost category as object, not {obj!r}")
                elif obj == UNKNOWN:
                    errors.append(f"{sid}: `unknown` is not an object; use total with includes_categories [unknown]")
                if not (q.get("amount") or q.get("effort")):
                    errors.append(f"{sid}: incurs_cost needs amount or effort")
                if not q.get("scale") and not q.get("count"):
                    errors.append(f"{sid}: incurs_cost needs scale (or a count of things treated)")
                if not q.get("phase"):
                    errors.append(f"{sid}: incurs_cost needs phase")
                if obj == "total" and not q.get("includes_categories"):
                    errors.append(f"{sid}: a total needs includes_categories ([unknown] is allowed)")
            elif pred == "costs_relative_to":
                if not q.get("ratio"):
                    errors.append(f"{sid}: costs_relative_to needs a ratio")
                if obj in categories:
                    errors.append(f"{sid}: costs_relative_to needs an action or strategy node as object, not the category {obj!r}")
                elif obj not in nodes:
                    errors.append(f"{sid}: costs_relative_to object {obj} is not a node in the files given")
            amount = q.get("amount") or {}
            if amount.get("value") is not None and amount.get("price_year") is None:
                errors.append(f"{sid}: an amount with a value needs price_year")
            if amount and not amount.get("currency"):
                errors.append(f"{sid}: an amount needs a currency")
            if s.get("transferred_from") and not s.get("transfer_rule"):
                errors.append(f"{sid}: transferred_from requires transfer_rule")
            if q.get("covers_roles"):
                subject_roles = roles.get(s.get("subject"))
                if subject_roles is None:
                    errors.append(f"{sid}: covers_roles needs a strategy subject; {s.get('subject')} is not one")
                else:
                    missing = sorted(set(q["covers_roles"]) - subject_roles)
                    if missing:
                        errors.append(f"{sid}: covers_roles {missing} are not roles of {s.get('subject')}'s components")
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("files", type=Path, nargs="+")
    parser.add_argument("--schema", type=Path, default=dp.DEFAULT_SCHEMA)
    args = parser.parse_args(argv)
    sets = [yaml.safe_load(f.read_text(encoding="utf-8")) or {} for f in args.files]
    errors = check(sets, args.schema)
    for e in errors:
        print("error:", e, file=sys.stderr)
    print(f"check_cost: {len(errors)} error(s) in {len(sets)} file(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
