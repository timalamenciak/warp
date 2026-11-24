#!/usr/bin/env python3
"""Check tolerance statements for what neither LinkML nor OWL can say (R17).

    python scripts/check_tolerance.py FILE.yaml [FILE.yaml ...]

Pass statement sets together with the sets holding their node definitions.
Errors (exit status 1):

  - The object's kind must match the predicate. For has_habitat (RO:0002303)
    the object is a habitat or environment node: its node definition uses a
    habitat template (HABITAT_TEMPLATES, whose fillers are ENVO terms). For
    tolerates, prefers and intolerant_of the object is a
    quality_of_environmental_material node. One LinkML slot cannot say this,
    and no OWL axiom can carry it either, because the reification layer
    never asserts the relation between classes as a logical axiom.
  - An object with no node definition cannot be checked, and is an error.
  - response_curve: x strictly increasing, suitability in [0, 1].
"""

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import derive_propositions as dp  # noqa: E402

HABITAT_PREDICATES = {"has_habitat"}
HABITAT_TEMPLATES = {"environment_type", "environment_type_in_setting"}
QUALITY_TEMPLATES = {"quality_of_environmental_material"}


def node_templates(sets):
    out = {}
    for data in sets:
        for d in data.get("node_definitions") or []:
            out[d["node"]] = d["template"]
    return out


def check(sets, schema=dp.DEFAULT_SCHEMA):
    groups = {g["group"]: g for g in dp.load_groups(schema, all_groups=True)}
    g = groups.get("tolerance")
    if g is None:
        return []
    templates = node_templates(sets)
    errors = []
    for data in sets:
        for s in data.get(g["statements_slot"]) or []:
            sid, obj, pred = s.get("id", "?"), s.get("object"), s.get("predicate")
            tid = templates.get(obj)
            if tid is None:
                errors.append(f"{sid}: object {obj} has no node definition, so its kind cannot be checked")
            elif pred in HABITAT_PREDICATES and tid not in HABITAT_TEMPLATES:
                errors.append(f"{sid}: {pred} needs a habitat or environment node "
                              f"({', '.join(sorted(HABITAT_TEMPLATES))}); {obj} uses {tid}")
            elif pred not in HABITAT_PREDICATES and tid not in QUALITY_TEMPLATES:
                errors.append(f"{sid}: {pred} needs a quality_of_environmental_material node; {obj} uses {tid}")
            curve = (s.get("predicate_qualifiers") or {}).get("response_curve") or []
            xs = [p.get("x") for p in curve]
            if any(b <= a for a, b in zip(xs, xs[1:])):
                errors.append(f"{sid}: response_curve x values must be strictly increasing: {xs}")
            for p in curve:
                if not 0 <= p.get("suitability", 0) <= 1:
                    errors.append(f"{sid}: response_curve suitability {p.get('suitability')} is outside [0, 1]")
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
    print(f"check_tolerance: {len(errors)} error(s) in {len(sets)} file(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
