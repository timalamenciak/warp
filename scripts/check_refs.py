#!/usr/bin/env python3
"""Check that every reference in WARP statement sets resolves.

    python scripts/check_refs.py FILE.yaml [FILE.yaml ...] [--schema PATH]

Schema-driven: a reference is a value of any slot whose range is a class and
that is not inlined (subject and object nodes, propositions, documents in
`specified_in`, agents in contributions and CARE metadata, criteria sets, and
whatever a later group adds). Every such value must equal the identifier of a
record in one of the files given, so pass a set together with its derived
file and with anything that cites it (an assessment and the derived set it
assesses).

An identifier is the value of an `identifier` slot whose range is not itself
a class (so a NodeDefinition, whose identifier `node` points at a CausalNode,
defines nothing and is checked as a reference instead).

Slots whose range is a plain string or CURIE (`reportedIn`,
`evidence_item_refs`) are not references by the schema's lights;
check_statements.py checks those by name.

Exit status 1 if any reference is unresolved; each is reported with the file,
the record path and the slot it comes from.
"""

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import warp_schema as ws  # noqa: E402


def defined_ids(sv, data):
    ids = set()
    for item in ws.walk(sv, data, "StatementSet"):
        slot = item.slot
        if slot.identifier and isinstance(item.value, str) and not ws.is_class(sv, slot.range):
            ids.add(item.value)
    return ids


def references(sv, data):
    """Yield (path, slot name, referenced id) for every reference in data."""
    for item in ws.walk(sv, data, "StatementSet"):
        if isinstance(item.value, str) and ws.is_reference(sv, item.slot):
            yield item.path, item.slot.name, item.value


def check(sv, sets):
    """sets: [(name, data)]. Returns a list of unresolved-reference messages."""
    known = set()
    for _, data in sets:
        known |= defined_ids(sv, data)
    problems = []
    for name, data in sets:
        for path, slot, ref in references(sv, data):
            if ref not in known:
                problems.append(f"{name}:{path}: {slot} '{ref}' does not resolve to any record")
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("files", type=Path, nargs="+")
    parser.add_argument("--schema", type=Path, default=ws.DEFAULT_SCHEMA)
    args = parser.parse_args(argv)
    sv = ws.load(args.schema)
    sets = [(f.name, yaml.safe_load(f.read_text(encoding="utf-8")) or {}) for f in args.files]
    problems = check(sv, sets)
    for p in problems:
        print("error:", p, file=sys.stderr)
    n = sum(1 for _, d in sets for _ in references(sv, d))
    print(f"{n} reference(s) checked, {len(problems)} unresolved, in {len(sets)} file(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
