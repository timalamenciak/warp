#!/usr/bin/env python3
"""Check identifiers, units, places, scales and dates in WARP statement sets.

    python scripts/check_values.py FILE.yaml [FILE.yaml ...] [--schema PATH] [--scales PATH]

Schema-driven: every slot whose range is a CURIE type, an identifier, or a
reference to another record is checked, so new groups and value classes are
covered without code changes. Errors (exit status 1):

  - A CURIE whose prefix is not declared in the profile (D20). A value with
    no prefix at all in a CURIE slot (`unit: ha`) is an error too: in RDF it
    would become a relative IRI, which is silent garbage (R20).
  - A placeholder under a real ontology's prefix (`ELMO:TODO_planting`): use
    the TODO: prefix (`TODO:planting`), so nothing invented can pass as a
    real term (R21).
  - A non-numeric local ID under an OBO prefix (`UO:hectare`): OBO IDs are
    numeric.
  - A prefix outside a slot's `warp_allowed_prefixes` annotation: units must
    be UO, QUDT, a scale or TODO; places must come from a registered place
    scheme (docs/values.md).
  - QuantityRange with min greater than max.
  - ScaledValue whose scale is not registered in vocab/scales.yaml, whose
    concept is not in that scale, which has a concept but no scale, or which
    uses the `practitioner-free` pseudo-scale (a practitioner's wording goes in
    `value` with no scale).
  - Period or date strings that are not ISO 8601 (year, year-month, date),
    or that end before they start (D19).
"""

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import warp_schema as ws  # noqa: E402
import warp_time  # noqa: E402
from gen_vocab import load_scales, scale_index  # noqa: E402

DEFAULT_SCALES = ws.ROOT / "vocab" / "scales.yaml"
PLACEHOLDER_MARKERS = ("TODO", "<", ">")


class ValueChecker:
    def __init__(self, sv, scales_path=DEFAULT_SCALES):
        self.sv = sv
        self.pm = ws.prefix_map(sv)
        self.scales, self.not_scales = scale_index(load_scales(scales_path))
        self.errors = []

    def error(self, where, msg):
        self.errors.append(f"{where}: {msg}")

    # -- CURIEs -------------------------------------------------------------

    def curie(self, where, value, allowed=None):
        if ws.is_absolute(value):
            return
        if ":" not in value:
            self.error(where, f"{value!r} is not a CURIE (no prefix); in RDF it would be a relative IRI")
            return
        prefix, local = ws.split(value)
        if prefix not in self.pm:
            self.error(where, f"undeclared prefix {prefix!r} in {value!r}")
            return
        if prefix != "TODO" and any(m in local for m in PLACEHOLDER_MARKERS):
            self.error(where, f"placeholder {value!r} sits under the real prefix {prefix!r}; "
                              f"use TODO:{local.replace('TODO_', '').replace('TODO', '').strip('_') or 'term'}")
        elif ws.is_obo(prefix, self.pm) and not local.isdigit():
            self.error(where, f"{value!r}: {prefix} is an OBO ontology and its IDs are numeric")
        if allowed and prefix not in allowed:
            self.error(where, f"{value!r} uses prefix {prefix!r}; allowed here: {', '.join(sorted(allowed))}")

    # -- value classes ------------------------------------------------------

    def quantity_range(self, where, obj):
        lo, hi = obj.get("min"), obj.get("max")
        if lo is None and hi is None:
            self.error(where, "QuantityRange needs min, max or both")
        if lo is not None and hi is not None and lo > hi:
            self.error(where, f"QuantityRange min {lo} is greater than max {hi}")

    def scaled_value(self, where, obj):
        scale, concept = obj.get("scale"), obj.get("concept")
        if concept and not scale:
            self.error(where, "ScaledValue has a concept but no scale")
        if not scale:
            return
        try:
            scale_iri = ws.expand(scale, self.pm)
        except ws.CurieError:
            return   # reported by the CURIE check
        if scale_iri in self.not_scales:
            self.error(where, f"{scale} is not a scale: record the source's wording in value, "
                              "with no scale and no concept")
            return
        if scale.startswith("TODO:"):
            return
        concepts = self.scales.get(scale_iri)
        if concepts is None:
            self.error(where, f"scale {scale} is not registered in vocab/scales.yaml")
            return
        if concept is None:
            self.error(where, f"scale {scale} is registered, so concept is required")
            return
        try:
            concept_iri = ws.expand(concept, self.pm)
        except ws.CurieError:
            return
        if concept_iri not in concepts:
            self.error(where, f"concept {concept} is not in scale {scale}")

    def period(self, where, obj):
        try:
            warp_time.period_bounds(obj.get("start"), obj.get("end"))
        except warp_time.TimeError as err:
            self.error(where, str(err))

    CLASS_CHECKS = {
        "QuantityRange": quantity_range,
        "ScaledValue": scaled_value,
        "Period": period,
    }

    # -- driver -------------------------------------------------------------

    def check_set(self, name, data):
        for item in ws.walk(self.sv, data, "StatementSet"):
            where = f"{name}:{item.path}"
            slot = item.slot
            if isinstance(item.value, str) and ws.is_curie_slot(self.sv, slot):
                allowed = ws.annotation(slot, "warp_allowed_prefixes")
                self.curie(where, item.value, set(allowed.split()) if allowed else None)
            if isinstance(item.value, dict):
                cls = ws.concrete_class(self.sv, item.value, slot.range)
                for ancestor in self.sv.class_ancestors(cls) if ws.is_class(self.sv, cls) else []:
                    check = self.CLASS_CHECKS.get(ancestor)
                    if check:
                        check(self, where, item.value)
                        break
            date_pattern = slot.pattern and "[0-9]{4}" in slot.pattern
            if date_pattern and isinstance(item.value, str):
                try:
                    warp_time.parse(item.value)
                except warp_time.TimeError as err:
                    self.error(where, str(err))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("files", type=Path, nargs="+")
    parser.add_argument("--schema", type=Path, default=ws.DEFAULT_SCHEMA)
    parser.add_argument("--scales", type=Path, default=DEFAULT_SCALES)
    args = parser.parse_args(argv)

    checker = ValueChecker(ws.load(args.schema), args.scales)
    for f in args.files:
        checker.check_set(f.name, yaml.safe_load(f.read_text(encoding="utf-8")) or {})
    for e in checker.errors:
        print("error:", e, file=sys.stderr)
    print(f"{len(checker.errors)} error(s) in {len(args.files)} file(s)")
    return 1 if checker.errors else 0


if __name__ == "__main__":
    sys.exit(main())
