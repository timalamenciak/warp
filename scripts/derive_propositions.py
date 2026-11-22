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

and optionally:

    warp_identity_extras     space-separated, ordered slot paths added to the
                             key, e.g. "predicate_qualifiers.guidance" or
                             "place". Dotted paths reach into inlined objects.
    warp_identity_rule       the rule name recorded on the group's propositions,
                             overriding the shared RULE_VERSION (e.g.
                             warp-criteria-identity/1)
    warp_derived_by          the script that derives this group's propositions,
                             if not this one (e.g. derive_projects.py); this
                             script then leaves the group alone

Proposition text is rendered from the `rosetta_template` annotation on each
value of the group's predicate enum. Templates may also use an identity extra
by the last segment of its path ({guidance}). Subjects and objects read by
their node's name, looked up in this set's `nodes` and then in the sets given
with --names (other derived files: a cost statement names a canonical
strategy whose node is in another file). A value that is not a CURIE (an
enum value such as degraded_area, a cost category) reads with spaces for
underscores. Text is not part of identity: changing it moves no ID.

Identity rule warp-prop-identity/4
----------------------------------
Two statements share a proposition when these match exactly:

    group, subject node, predicate, object node, negated, scope,
    then the group's identity extras, in declaration order

A group with no extras has just the six shared fields in its key.
Proposition IDs hash the key alone (the rule version is recorded, not
hashed), so a new rule version that leaves a group's key unchanged leaves its
IDs unchanged (decision D4).

Extras are written into the key as `path=<canonical JSON>`. Structured values
are canonicalized (objects with sorted keys; lists sorted unless the slot is
`list_elements_ordered`), so the same content always hashes the same. A
missing extra is the JSON null, so the statement still groups with others
whose value is also missing, and is counted in the report as "grouped with
missing key fields". The null lives only inside the key string: it is never
written to a slot and never exported (decision D14).

Everything else (hedging, predicate qualifiers not in the key, comparator,
context, evidence) stays on the statement and is aggregated later, not used
for identity. Statements whose scope is missing or "unclear" are not grouped
and are reported, because scope is part of what a proposition says.

A non-negated key says "affirmed", not "asserted", so it cannot be confused
with the proposition status `asserted`.

Changing this rule regroups statements. Bump RULE_VERSION whenever you do.

Open questions (propositions written by people with status open_question) are
kept with their ids and flagged raised_as_question. If a statement matches one,
it becomes asserted; if those statements later go away, it reverts to
open_question. Re-running on the script's own output gives the same result.

Usage:
    python scripts/derive_propositions.py IN.yaml OUT.yaml [--names SET.yaml ...] [--schema PATH]
"""

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

import yaml
from linkml_runtime.utils.schemaview import SchemaView

RULE_VERSION = "warp-prop-identity/4"
UNGROUPABLE_SCOPES = {None, "", "unclear"}
THIS_SCRIPT = "derive_propositions.py"

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
    anns = element.annotations
    if not anns:
        return None
    try:
        ann = anns[key]
    except (KeyError, TypeError, AttributeError):
        ann = getattr(anns, key, None)
    if ann is None:
        return None
    return ann.get("value") if isinstance(ann, dict) else getattr(ann, "value", ann)


def resolve_path(sv, cls, path):
    """The induced slot at the end of a dotted path, starting from a class."""
    slot = None
    for seg in path.split("."):
        slot = sv.induced_slot(seg, cls)
        cls = slot.range
    return slot


def load_groups(schema_path, all_groups=False):
    """Find registered predicate groups and their rendering templates.

    By default, groups derived by another script (warp_derived_by) are left
    out; pass all_groups=True to list every registered group."""
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
        extras = (annotation(cls, "warp_identity_extras") or "").split()
        ordered = {}
        for path in extras:
            try:
                slot = resolve_path(sv, cname, path)
            except Exception as err:   # noqa: BLE001 - report which path is wrong
                raise SystemExit(f"{cname}: identity extra {path!r} is not a slot path ({err})")
            ordered[path] = bool(slot.list_elements_ordered)
        derived_by = annotation(cls, "warp_derived_by") or THIS_SCRIPT
        if derived_by != THIS_SCRIPT and not all_groups:
            continue
        groups.append({
            "group": group,
            "statement_class": cname,
            "statements_slot": annotation(cls, "warp_statements_slot"),
            "propositions_slot": annotation(cls, "warp_propositions_slot"),
            "proposition_class": annotation(cls, "warp_proposition_class"),
            "templates": templates,
            "extras": extras,
            "ordered": ordered,
            "rule": annotation(cls, "warp_identity_rule") or RULE_VERSION,
            "derived_by": derived_by,
        })
    return sorted(groups, key=lambda g: g["group"])


# --- identity keys --------------------------------------------------------------

def get_path(record, path):
    """Value at a dotted path through nested dicts, or None."""
    node = record
    for seg in path.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(seg)
    return node


def set_path(record, path, value):
    node = record
    segs = path.split(".")
    for seg in segs[:-1]:
        node = node.setdefault(seg, {})
    node[segs[-1]] = copy.deepcopy(value)


def _normalize(value, ordered):
    if isinstance(value, dict):
        return {k: _normalize(v, False) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        items = [_normalize(v, False) for v in value]
        if ordered:
            return items
        return sorted(items, key=lambda v: json.dumps(v, sort_keys=True, ensure_ascii=False))
    return value


def canonical(value, ordered=False):
    """Deterministic JSON for a key field: sorted object keys, and sorted
    lists unless their order carries meaning. Empty values count as missing."""
    if value in (None, "", [], {}):
        return "null"
    return json.dumps(_normalize(value, ordered), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def identity_key(g, record, negated, scope):
    """(key string, [extras that were missing]) for a statement or proposition."""
    parts = [g["group"], record["subject"], record["predicate"], record["object"],
             "negated" if negated else "affirmed", scope]
    missing = []
    for path in g.get("extras", []):
        value = get_path(record, path)
        text = canonical(value, g.get("ordered", {}).get(path, False))
        if text == "null":
            missing.append(path)
        parts.append(f"{path}={text}")
    return "|".join(parts), missing


def proposition_id(key):
    return "warp:prop/" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


# --- rendering ----------------------------------------------------------------

def names_from(*statement_sets):
    """{node id: name} from the `nodes` of each set; the first set to name an
    id wins."""
    names = {}
    for s in statement_sets:
        for n in (s or {}).get("nodes") or []:
            if isinstance(n, dict) and n.get("id") and n.get("name"):
                names.setdefault(n["id"], n["name"])
    return names


def word(value, names):
    """How a subject or object reads in text: its node's name; a value that is
    not a CURIE (an enum value, a cost category) with spaces for underscores;
    otherwise as written."""
    if value in names:
        return names[value]
    if isinstance(value, str) and ":" not in value:
        return value.replace("_", " ")
    return value


class _Blank(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def render(templates, node_names, subject, predicate, obj, negated, scope, extras=None):
    template = templates.get(predicate, "{subject} " + predicate.replace("_", " ") + " {object}")
    fields = _Blank(subject=word(subject, node_names), object=word(obj, node_names))
    for path, value in (extras or {}).items():
        if isinstance(value, str):
            fields[path.split(".")[-1]] = value.replace("_", " ")
    text = template.format_map(fields)
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


# --- derivation -----------------------------------------------------------------

def derive_group(statement_set, g, node_names):
    """Derive one group's propositions in place. Returns (propositions,
    ungrouped statement ids, statement ids grouped with missing key fields)."""
    rule = g.get("rule", RULE_VERSION)
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
        key, _ = identity_key(g, p, p.get("negated", False), p["scope"])
        p["identity_key"] = key
        p["identity_rule_version"] = rule
        p["derived_from_statements"] = []
        p["status"] = "open_question"   # becomes asserted below if any statement matches
        by_key[key] = p

    skipped, incomplete = [], []
    for statement in statement_set.get(g["statements_slot"]) or []:
        scope = statement.get("scope")
        if scope in UNGROUPABLE_SCOPES:
            statement.pop("proposition", None)
            set_evidence_targets(statement, None)
            skipped.append(statement["id"])
            continue
        negated = bool(statement.get("negated", False))
        key, missing = identity_key(g, statement, negated, scope)
        if missing:
            incomplete.append(statement["id"])
        extras = {path: get_path(statement, path) for path in g.get("extras", [])}
        rendered = render(g["templates"], node_names, statement["subject"], statement["predicate"],
                          statement["object"], negated, scope, extras)
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
            }
            for path, value in extras.items():
                if value not in (None, "", [], {}):
                    set_path(prop, path, value)
            prop["propositionText"] = rendered
            prop["derived_from_statements"] = []
            by_key[key] = prop
        if prop.get("raised_as_question") and "description" not in prop:
            # Keep the question as asked; replace the text with the rendered fact.
            prop["description"] = "Raised as an open question: " + prop.get("propositionText", "")
            prop["propositionText"] = rendered
        prop["status"] = "asserted"
        prop["identity_key"] = key
        prop["identity_rule_version"] = rule
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
    return props, skipped, incomplete


def derive_all(statement_set, schema_path=DEFAULT_SCHEMA, names=None):
    """Derive every group's propositions in place; return a report per group.
    `names` ({node id: name}) names nodes defined in other sets; the set's
    own nodes win."""
    node_names = {**(names or {}), **names_from(statement_set)}
    report = []
    for g in load_groups(schema_path):
        props, skipped, incomplete = derive_group(statement_set, g, node_names)
        report.append({"group": g["group"], "rule": g["rule"], "propositions": props,
                       "skipped": skipped, "incomplete": incomplete})
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA,
                        help="WARP schema (for the group registry)")
    parser.add_argument("--names", type=Path, nargs="*", default=[],
                        help="other statement sets whose nodes name subjects and objects "
                             "defined outside this one (pass every derived file)")
    args = parser.parse_args(argv)

    statement_set = yaml.safe_load(args.input.read_text(encoding="utf-8"))
    others = [yaml.safe_load(p.read_text(encoding="utf-8")) or {} for p in args.names if p.exists()]
    report = derive_all(statement_set, args.schema, names_from(*others))

    args.output.write_text(
        "# GENERATED by scripts/derive_strategies.py, derive_propositions.py and derive_projects.py ("
        + RULE_VERSION + "). Do not edit derived records by hand.\n"
        + yaml.safe_dump(statement_set, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )

    skipped = []
    for r in report:
        print(f"{r['group']}: {len(r['propositions'])} proposition(s) under {r['rule']}")
        for p in r["propositions"]:
            print(f"  {p['id']}  [{p['status']}]  {p.get('propositionText', p['identity_key'])}"
                  f"  <- {', '.join(p.get('derived_from_statements') or []) or 'no statements yet'}")
        if r["incomplete"]:
            print(f"  grouped with missing key fields: {len(r['incomplete'])} "
                  f"({', '.join(r['incomplete'])})")
        skipped += r["skipped"]
    if skipped:
        print(f"Not grouped (scope missing or unclear): {', '.join(skipped)}", file=sys.stderr)


if __name__ == "__main__":
    main()
