"""Generate WARP profiles: the schema restricted to some predicate groups.

    python scripts/subset_schema.py config/profiles.yaml --out-dir project/profiles

For each profile in the config this writes

  <out-dir>/warp_<name>.yaml           the LinkML schema, imports rewritten to
                                       the vendored upstreams in src/warp/schema
  <out-dir>/warp-relations_<name>.ttl  warp-relations.ttl without the predicates
                                       of the groups left out

A profile keeps the shared core, the groups it names and the optional
StatementSet lists it names (strategy_definitions, site_definitions,
criteria_sets). Everything else in warp.yaml is kept only if something kept
refers to it: the closure follows ranges (including inside any_of, rules and
slot conditions), is_a, mixins, class slots and slot_usage keys. Classes,
enums and top-level slots nothing kept refers to are dropped. Imported
schemas (SEPIO, CAMO) are imported whole.

Every IRI is unchanged (same default prefix, same class and slot URIs), so a
profile is a strict subset of WARP: data valid against a profile is valid
against warp.yaml, and its derived IDs and RDF are the same as a full build
would give. Groups are found from the registry annotations, as everywhere
else; this script names no group.

The outputs are GENERATED: edit warp.yaml or the config, never the outputs.
"""

import argparse
import os
import sys
from pathlib import Path

import yaml
from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "src" / "warp" / "schema" / "warp.yaml"
DEFAULT_RELATIONS = ROOT / "src" / "warp" / "owl" / "warp-relations.ttl"
DCT_DESCRIPTION = URIRef("http://purl.org/dc/terms/description")


class ProfileError(ValueError):
    pass


def _ann(cls, key):
    v = (cls.get("annotations") or {}).get(key)
    return v.get("value") if isinstance(v, dict) else v


def registry(schema):
    """{group: {class, statements_slot, propositions_slot}} from annotations."""
    out = {}
    for name, cls in (schema.get("classes") or {}).items():
        g = _ann(cls, "warp_group")
        if g:
            out[g] = {"class": name,
                      "statements_slot": _ann(cls, "warp_statements_slot"),
                      "propositions_slot": _ann(cls, "warp_propositions_slot")}
    return out


def _refs(obj, slot_names, out):
    """Collect element names an element definition refers to, recursively."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("range", "is_a") and isinstance(v, str):
                out.add(v)
            elif k == "mixins":
                out.update(v or [])
            elif k == "slots" and isinstance(v, list):
                out.update(("slot", s) for s in v)
            elif k in ("description", "comments", "annotations", "examples", "title"):
                continue
            if k in slot_names:
                out.add(("slot", k))
            _refs(v, slot_names, out)
    elif isinstance(obj, list):
        for v in obj:
            _refs(v, slot_names, out)


def closure(schema, roots):
    classes, enums = schema.get("classes") or {}, schema.get("enums") or {}
    slots = schema.get("slots") or {}
    seen, stack = set(), list(roots)
    while stack:
        r = stack.pop()
        if r in seen:
            continue
        seen.add(r)
        if isinstance(r, tuple):
            definition = slots.get(r[1])
        else:
            definition = classes.get(r)
        if definition is None:
            continue       # an enum, a type, or an imported element
        found = set()
        _refs(definition, slots, found)
        stack.extend(found - seen)
    keep_classes = {x for x in seen if isinstance(x, str) and x in classes}
    keep_enums = {x for x in seen if isinstance(x, str) and x in enums}
    keep_slots = {x[1] for x in seen if isinstance(x, tuple) and x[1] in slots}
    return keep_classes, keep_enums, keep_slots


def subset(schema, name, profile, optional_lists, schema_path, out_dir):
    """Return the profile schema (a dict) and the groups left out."""
    reg = registry(schema)
    groups = profile.get("groups") or []
    unknown = sorted(set(groups) - set(reg))
    if unknown:
        raise ProfileError(f"{name}: unknown group(s) {unknown}; registered: {sorted(reg)}")
    lists = profile.get("lists") or []
    bad = sorted(set(lists) - set(optional_lists))
    if bad:
        raise ProfileError(f"{name}: {bad} are not optional lists {sorted(optional_lists)}")
    dropped_groups = sorted(set(reg) - set(groups))
    drop = {reg[g][k] for g in dropped_groups for k in ("statements_slot", "propositions_slot")}
    drop |= set(optional_lists) - set(lists)

    out = {k: v for k, v in schema.items() if k not in ("classes", "enums", "slots")}
    ss = dict(schema["classes"]["StatementSet"])
    ss["attributes"] = {k: v for k, v in ss["attributes"].items() if k not in drop}
    roots = set()
    _refs(ss, schema.get("slots") or {}, roots)
    classes, enums, slots = closure(schema, roots)
    classes.add("StatementSet")

    # An optional list left out whose records a kept element needs.
    for lst in sorted(set(optional_lists) - set(lists)):
        rng = schema["classes"]["StatementSet"]["attributes"][lst].get("range")
        if rng in classes:
            raise ProfileError(f"{name}: kept elements use {rng}; add '{lst}' to the profile's lists")

    rel = os.path.relpath(schema_path.parent, out_dir).replace(os.sep, "/")
    out["id"] = f"{schema['id']}/profiles/{name}"
    out["name"] = f"warp_{name.replace('-', '_')}"
    out["title"] = f"{schema.get('title', 'WARP')}, {profile.get('title', name)} profile"
    out["description"] = (
        f"GENERATED by scripts/subset_schema.py from {schema_path.name} and "
        f"config/profiles.yaml; do not edit. WARP restricted to the predicate group(s) "
        f"{', '.join(groups)}"
        + (f" and the lists {', '.join(lists)}" if lists else "")
        + ". Every IRI is WARP's own, so data valid here is valid against the full profile.\n\n"
        + str(schema.get("description", "")))
    out["imports"] = [i if i.startswith("linkml:") else f"{rel}/{i}" for i in schema.get("imports", [])]
    order = list(schema["classes"])
    out["enums"] = {k: v for k, v in (schema.get("enums") or {}).items() if k in enums}
    out["slots"] = {k: v for k, v in (schema.get("slots") or {}).items() if k in slots}
    out["classes"] = {k: (ss if k == "StatementSet" else schema["classes"][k])
                      for k in order if k in classes}
    return out, dropped_groups


def subset_relations(relations_path, schema, dropped_groups):
    """warp-relations.ttl without object properties only the dropped groups use.

    A dropped group's predicates are the meanings of its predicate enum
    values. An object property is removed when everything it is connected to
    by rdfs:subPropertyOf (its parent, its sub-properties) is in a dropped
    group, and no kept group's predicate is among them."""
    reg = registry(schema)
    classes, enums = schema["classes"], schema.get("enums") or {}
    prefixes = {k: (v["prefix_reference"] if isinstance(v, dict) else v)
                for k, v in (schema.get("prefixes") or {}).items()}

    def meanings(group):
        rng = ((classes[reg[group]["class"]].get("slot_usage") or {}).get("predicate") or {}).get("range")
        out = set()
        for pv in ((enums.get(rng) or {}).get("permissible_values") or {}).values():
            m = (pv or {}).get("meaning")
            if m and ":" in m:
                p, local = m.split(":", 1)
                out.add(URIRef(prefixes.get(p, p + ":") + local))
        return out

    dropped = set().union(*(meanings(g) for g in dropped_groups)) if dropped_groups else set()
    kept = set().union(*(meanings(g) for g in reg if g not in dropped_groups))
    g = Graph()
    g.parse(relations_path, format="turtle")
    ops = set(g.subjects(RDF.type, OWL.ObjectProperty))
    # connected components over rdfs:subPropertyOf among declared properties
    parent = {p: p for p in ops}

    def find(p):
        while parent[p] != p:
            parent[p] = parent[parent[p]]
            p = parent[p]
        return p
    for s, o in g.subject_objects(RDFS.subPropertyOf):
        if s in parent and o in parent:
            parent[find(s)] = find(o)
    comps = {}
    for p in ops:
        comps.setdefault(find(p), set()).add(p)
    remove = set()
    for members in comps.values():
        if members & dropped and not members & kept:
            remove |= members
    for p in remove:
        for t in list(g.triples((p, None, None))):
            g.remove(t)
    return g, sorted(str(p) for p in remove)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("config", type=Path)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--list", action="store_true", help="print the profile names and exit")
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--relations", type=Path, default=DEFAULT_RELATIONS)
    parser.add_argument("--profile", action="append", help="only these profiles (default: all)")
    args = parser.parse_args(argv)
    config = yaml.safe_load(args.config.read_text(encoding="utf-8")) or {}
    schema = yaml.safe_load(args.schema.read_text(encoding="utf-8"))
    optional = config.get("optional_lists") or []
    profiles = config.get("profiles") or {}
    if args.list:
        print(" ".join(profiles))
        return
    if args.out_dir is None:
        parser.error("--out-dir is required")
    names = args.profile or list(profiles)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    try:
        for name in names:
            if name not in profiles:
                raise ProfileError(f"no profile '{name}' in {args.config}")
            out, dropped = subset(schema, name, profiles[name], optional,
                                  args.schema.resolve(), args.out_dir.resolve())
            target = args.out_dir / f"warp_{name}.yaml"
            target.write_text(
                f"# GENERATED by scripts/subset_schema.py ({name} profile of "
                f"{args.schema.name}, config/profiles.yaml). Do not edit.\n"
                + yaml.safe_dump(out, sort_keys=False, allow_unicode=True, width=100),
                encoding="utf-8", newline="\n")
            rel, removed = subset_relations(args.relations, schema, dropped)
            onto = next(rel.subjects(RDF.type, OWL.Ontology), None)
            if onto is not None:
                rel.set((onto, RDFS.comment, __import__("rdflib").Literal(
                    f"GENERATED by scripts/subset_schema.py: the {name} profile of WARP's relations, "
                    f"without the predicates of {', '.join(dropped) or 'no group'}.")))
            rtarget = args.out_dir / f"warp-relations_{name}.ttl"
            rtarget.write_text(rel.serialize(format="turtle"), encoding="utf-8", newline="\n")
            print(f"{name}: {len(out['classes'])} classes, {len(out['enums'])} enums, "
                  f"{len(out['slots'])} slots from {args.schema.name}; groups "
                  f"{', '.join(profiles[name].get('groups') or [])}; "
                  f"{len(removed)} predicate(s) left out of the relations -> {target}")
    except ProfileError as err:
        print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
