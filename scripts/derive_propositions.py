#!/usr/bin/env python3
"""Derive propositions from annotated statements (WARP).

Annotators record statements; this script groups statements that put forward
the same possible fact into a shared proposition, writes the propositions into
the StatementSet, fills each statement's `proposition` slot, and sets the
`targetProposition` of the statement's own evidence lines to match.

It works for every predicate group registered in the schema. A group is any
EcoStatement subclass carrying these annotations (see docs/predicate-groups.md):

    warp_group               short name, part of the identity key
    warp_statements_slot     StatementSet list holding the group's statements
    warp_propositions_slot   StatementSet list holding the group's propositions
    warp_proposition_class   the group's proposition class

Proposition text is rendered from the `rosetta_template` annotation on each
value of the group's predicate enum.

Identity rule warp-prop-identity/3
--------------------------------
Two statements share a proposition when these match exactly:

    group, subject node, predicate, object node, negated, scope

Everything else (hedging, predicate qualifiers, comparator, context, evidence)
stays on the statement and is aggregated later, not used for identity. Statements
whose scope is missing or "unclear" are not grouped and are reported, because
scope is part of what a proposition says. (Version 1 had no group field.
Version 2 wrote "asserted" for a non-negated key, the same word as the
proposition status; version 3 writes "affirmed". Same fields, new ids.)

Changing this rule regroups statements. Bump RULE_VERSION whenever you do.

Open questions (propositions written by people with status open_question) are
kept with their ids and flagged raised_as_question. If a statement matches one,
it becomes asserted; if those statements later go away, it reverts to
open_question. Re-running on the script's own output gives the same result.

Usage:
    python scripts/derive_propositions.py IN.yaml OUT.yaml [--schema PATH]
"""

import argparse
import hashlib
import sys
from pathlib import Path

import yaml
from linkml_runtime.utils.schemaview import SchemaView

RULE_VERSION = "warp-prop-identity/3"
UNGROUPABLE_SCOPES = {None, "", "unclear"}

DEFAULT_SCHEMA = (
    Path(__file__).resolve().parent.parent
    / "src" / "warp" / "schema" / "warp.yaml"
)

SCOPE_PREFIX = {
    "assertional": "In a particular case, ",
    "contingent": "Sometimes, ",
    "prototypical": "Typically, ",
    "universal": "Always, ",
}


def annotation(element, key):
    ann = (element.annotations or {}).get(key)
    return ann.value if ann is not None else None


def load_groups(schema_path):
    """Find registered predicate groups and their rendering templates."""
    sv = SchemaView(str(schema_path))
    groups = []
    for cname in sv.all_classes():
        cls = sv.get_class(cname)
        group = annotation(cls, "warp_group")
        if not group:
            continue
        predicate_enum = sv.induced_slot("predicate", cname).range
        enum = sv.get_enum(predicate_enum)
        if enum is None:
            raise SystemExit(f"{cname}: predicate range {predicate_enum} is not an enum")
        templates = {}
        for value, pv in enum.permissible_values.items():
            template = annotation(pv, "rosetta_template")
            if template:
                templates[value] = template
        groups.append({
            "group": group,
            "statement_class": cname,
            "statements_slot": annotation(cls, "warp_statements_slot"),
            "propositions_slot": annotation(cls, "warp_propositions_slot"),
            "proposition_class": annotation(cls, "warp_proposition_class"),
            "templates": templates,
        })
    return sorted(groups, key=lambda g: g["group"])


def identity_key(group, subject, predicate, obj, negated, scope):
    return "|".join([group, subject, predicate, obj, "negated" if negated else "affirmed", scope])


def proposition_id(key):
    return "warp:prop/" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def render(templates, node_names, subject, predicate, obj, negated, scope):
    template = templates.get(predicate, "{subject} " + predicate.replace("_", " ") + " {object}")
    text = template.format(
        subject=node_names.get(subject, subject),
        object=node_names.get(obj, obj),
    )
    if negated:
        text = "it is not the case that " + text
    prefix = SCOPE_PREFIX.get(scope, "")
    text = prefix + text[0].lower() + text[1:] if prefix else text[0].upper() + text[1:]
    return text + "."


def set_evidence_targets(statement, proposition_id):
    """A statement's own evidence lines argue for the proposition it puts forward."""
    for line in statement.get("hasEvidenceLines") or []:
        if proposition_id is None:
            line.pop("targetProposition", None)
        else:
            line["targetProposition"] = proposition_id


def derive_group(statement_set, g, node_names):
    # Keep propositions people raised as questions (stable ids, never deleted).
    # Purely derived propositions are rebuilt from scratch, so the identity
    # rule is the only source of truth for them; their hash ids are stable
    # because the key is.
    by_key = {}
    for p in statement_set.get(g["propositions_slot"]) or []:
        if p.get("status") == "open_question":
            p["raised_as_question"] = True
        if not p.get("raised_as_question"):
            continue
        key = identity_key(g["group"], p["subject"], p["predicate"], p["object"],
                           p.get("negated", False), p["scope"])
        p["identity_key"] = key
        p["identity_rule_version"] = RULE_VERSION
        p["derived_from_statements"] = []
        p["status"] = "open_question"   # becomes asserted below if any statement matches
        by_key[key] = p

    skipped = []
    for statement in statement_set.get(g["statements_slot"]) or []:
        scope = statement.get("scope")
        if scope in UNGROUPABLE_SCOPES:
            statement.pop("proposition", None)
            set_evidence_targets(statement, None)
            skipped.append(statement["id"])
            continue
        negated = bool(statement.get("negated", False))
        key = identity_key(g["group"], statement["subject"], statement["predicate"], statement["object"],
                           negated, scope)
        rendered = render(g["templates"], node_names, statement["subject"], statement["predicate"],
                          statement["object"], negated, scope)
        prop = by_key.get(key)
        if prop is None:
            prop = {
                "id": proposition_id(key),
                "type": g["proposition_class"],
                "subject": statement["subject"],
                "predicate": statement["predicate"],
                "object": statement["object"],
                "negated": negated,
                "scope": scope,
                "propositionText": rendered,
                "derived_from_statements": [],
            }
            by_key[key] = prop
        if prop.get("raised_as_question") and "description" not in prop:
            # Keep the question as asked; replace the text with the rendered fact.
            prop["description"] = "Raised as an open question: " + prop.get("propositionText", "")
            prop["propositionText"] = rendered
        prop["status"] = "asserted"
        prop["identity_key"] = key
        prop["identity_rule_version"] = RULE_VERSION
        prop.setdefault("derived_from_statements", [])
        if statement["id"] not in prop["derived_from_statements"]:
            prop["derived_from_statements"].append(statement["id"])
        statement["proposition"] = prop["id"]
        set_evidence_targets(statement, prop["id"])

    props = sorted(by_key.values(), key=lambda p: p["id"])
    if props:
        statement_set[g["propositions_slot"]] = props
    else:
        statement_set.pop(g["propositions_slot"], None)
    return props, skipped


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA,
                        help="WARP schema (for the group registry)")
    args = parser.parse_args(argv)

    statement_set = yaml.safe_load(args.input.read_text(encoding="utf-8"))
    node_names = {n["id"]: n.get("name", n["id"]) for n in statement_set.get("nodes") or []}

    report, skipped = [], []
    for g in load_groups(args.schema):
        props, sk = derive_group(statement_set, g, node_names)
        report.append((g["group"], props))
        skipped += sk

    args.output.write_text(
        "# GENERATED by scripts/derive_propositions.py (" + RULE_VERSION + "). Do not edit propositions by hand.\n"
        + yaml.safe_dump(statement_set, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )

    for group, props in report:
        print(f"{group}: {len(props)} proposition(s) under {RULE_VERSION}")
        for p in props:
            print(f"  {p['id']}  [{p['status']}]  {p.get('propositionText', p['identity_key'])}"
                  f"  <- {', '.join(p.get('derived_from_statements') or []) or 'no statements yet'}")
    if skipped:
        print(f"Not grouped (scope missing or unclear): {', '.join(skipped)}", file=sys.stderr)


if __name__ == "__main__":
    main()
