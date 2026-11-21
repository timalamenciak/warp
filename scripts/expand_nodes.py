#!/usr/bin/env python3
"""Expand node definitions into OWL classes and DOSDP fill tables.

    python scripts/expand_nodes.py templates/node_templates.yaml \
        examples/bloodroot_statements.yaml [more StatementSet files...] \
        --owl project/nodes.ttl --tsv-dir patterns/data

For every entry in a StatementSet's `node_definitions`, this:
  1. checks the filling against its template (every var filled exactly once,
     filler CURIEs use an allowed prefix);
  2. writes the node as an OWL class with a generated label, definition and
     owl:equivalentClass axiom (Turtle, --owl);
  3. appends a row to patterns/data/<template>.tsv, the input format
     dosdp-tools and the ODK pattern pipeline expect (--tsv-dir).

Two routes to OWL, same result: use the Turtle directly, or run dosdp-tools on
the generated patterns and TSVs inside an ODK repository.

Exits non-zero if any definition is invalid.
"""

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS, DCTERMS

from templates_lib import (
    CLASS_EXPRESSION, TemplateError, check_template, expand_curie, fill_text, load_collection,
    template_kind,
)

OBO = Namespace("http://purl.obolibrary.org/obo/")
DEFINITION = OBO.IAO_0000115
TERM_REPLACED_BY = OBO.IAO_0100001
PATTERN_BASE = "https://w3id.org/ecoweaver/patterns/"
PLACEHOLDER_PREFIX = "TODO"
NODES_ONTOLOGY = URIRef("https://w3id.org/ecoweaver/warp/ontology/nodes")


def check_definition(defn, template):
    tid = template["id"]
    node = defn["node"]
    declared = {v["name"]: v for v in template["vars"]}
    filled = defaultdict(list)
    if not defn.get("fillers"):
        return [f"{node}: template {tid} needs fillers"]
    for f in defn["fillers"]:
        filled[f["var"]].append(f)
    problems = []
    for name in declared:
        if name not in filled:
            problems.append(f"{node}: {tid} var '{name}' is not filled")
    for name, fs in filled.items():
        if name not in declared:
            problems.append(f"{node}: {tid} has no var '{name}'")
            continue
        if len(fs) > 1:
            problems.append(f"{node}: var '{name}' filled {len(fs)} times")
        prefix = fs[0]["value"].split(":", 1)[0]
        allowed = declared[name]["allowed_prefixes"]
        # TODO: is the placeholder prefix (decision D20). It fills any variable
        # while the real term is unverified, and never passes as a real term.
        if prefix not in allowed and prefix != PLACEHOLDER_PREFIX:
            problems.append(f"{node}: var '{name}' = {fs[0]['value']} must use one of {allowed}")
    return problems


SITES_ONTOLOGY = URIRef("https://w3id.org/ecoweaver/warp/ontology/sites")
ISO_3166_2 = re.compile(r"^[A-Z]{2}-[A-Z0-9]{1,3}$")
WARP_NS = Namespace("https://w3id.org/ecoweaver/warp/")


def expand_sites(sg, data, pm, problems):
    """Write each site as an OWL named individual (decisions D7, D11): never a
    class, under site:, typed by its ecosystem types (rdf:type: a site is an
    instance of an ENVO environmental system), with its label and
    jurisdiction. Geometry never goes into a generated output. Yields
    (site id, label)."""
    import warp_schema as ws
    for d in data.get("site_definitions") or []:
        sid = d["node"]
        if not sid.startswith("site:"):
            problems.append(f"{sid}: a site's ID must be under site:, not node: (decision D11)")
            continue
        try:
            iri = URIRef(ws.expand(sid, pm))
        except ws.CurieError as err:
            problems.append(f"{sid}: {err}")
            continue
        sg.add((iri, RDF.type, OWL.NamedIndividual))
        if d.get("label"):
            sg.add((iri, RDFS.label, Literal(d["label"])))
        for t in d.get("ecosystem_type") or []:
            cls = URIRef(ws.expand(t, pm))
            sg.add((cls, RDF.type, OWL.Class))
            sg.add((iri, RDF.type, cls))
        j = d.get("jurisdiction")
        if j:
            if ISO_3166_2.match(j):
                target = URIRef(ws.expand(f"ISO3166-2:{j}", pm))
            elif re.match(r"^[A-Za-z][\w.-]*:\S+$", j) and j.split(":", 1)[0] in pm:
                target = URIRef(ws.expand(j, pm))
            else:
                target = None
            if target is not None:
                sg.add((WARP_NS.in_jurisdiction, RDF.type, OWL.ObjectProperty))
                sg.add((target, RDF.type, OWL.NamedIndividual))
                sg.add((iri, WARP_NS.in_jurisdiction, target))
            else:
                sg.add((WARP_NS.jurisdiction_name, RDF.type, OWL.AnnotationProperty))
                sg.add((iri, WARP_NS.jurisdiction_name, Literal(j)))
        yield sid, d.get("label", sid)


def refinements(defn, template):
    """Text for a node definition's refinements (depth, season), or ''."""
    parts = []
    depth = defn.get("depth")
    if depth:
        lo, hi, unit = depth.get("min"), depth.get("max"), depth.get("unit", "")
        span = f"{lo:g} to {hi:g}" if lo is not None and hi is not None else (
            f"from {lo:g}" if lo is not None else f"to {hi:g}")
        parts.append(f"depth {span} {unit}".strip())
    if defn.get("season"):
        parts.append(f"season {defn['season']}")
    return "; ".join(parts)


def expand_strategies(g, data, templates, prefixes, names, seen, problems):
    """Write each canonical management strategy as an OWL class (Phase 4).

    `<strategy> rdfs:subClassOf <parent_class>` and one
    `rdfs:subClassOf [ owl:onProperty <part_property> ; owl:someValuesFrom <part> ]`
    per required part after flattening (decisions D5, D6). Subclass, never
    equivalent class: order is in the identity key but does not render, so
    equivalence would merge strategies the rule holds apart. The part
    relation is transitive and used only inside someValuesFrom, so the output
    stays in OWL 2 EL. Optional parts, order, lags, repeats and roles stay in
    the reification layer. Superseded canonical IRIs (a part changed) are
    written as deprecated and replaced by the current one (IAO:0100001).
    Yields (canonical node, label) per strategy written."""
    defs = data.get("strategy_definitions") or []
    if not defs:
        return
    import derive_strategies as ds
    template = templates.get("management_strategy")
    if template is None:
        problems.append("strategy_definitions present but templates define no management_strategy")
        return
    parent = URIRef(expand_curie(template["parent_class"], prefixes))
    part = URIRef(expand_curie(template["part_property"], prefixes))
    # Derived files point nested components at canonical IDs, so look
    # definitions up by either ID.
    by_node = {d["node"]: d for d in defs}
    by_node.update({d["canonical_node"]: d for d in defs if d.get("canonical_node")})
    for d in defs:
        canon = d.get("canonical_node")
        if not canon:
            problems.append(f"{d['node']}: no canonical_node; run scripts/derive_strategies.py first")
            continue
        cls = URIRef(expand_curie(canon, prefixes))
        for old in d.get("replaces") or []:
            old_iri = URIRef(expand_curie(old, prefixes))
            g.add((old_iri, RDF.type, OWL.Class))
            g.add((old_iri, OWL.deprecated, Literal(True)))
            g.add((old_iri, TERM_REPLACED_BY, cls))
            g.add((TERM_REPLACED_BY, RDF.type, OWL.AnnotationProperty))
        if canon in seen:
            continue
        seen.add(canon)
        try:
            flat = ds.flatten(d, by_node)
        except ds.StrategyError as err:
            problems.append(str(err))
            continue
        required = sorted({c["action"] for c in flat if not c.get("optional")})
        steps = sorted((c["step"], names.get(c["action"], c["action"])) for c in flat if not c.get("optional"))
        label = names.get(canon, canon)
        g.add((cls, RDF.type, OWL.Class))
        g.add((cls, RDFS.label, Literal(label)))
        g.add((cls, DEFINITION, Literal(
            "A planned process whose required parts are, in order: "
            + "; ".join(f"step {s}: {n}" for s, n in steps) + ".")))
        g.add((parent, RDF.type, OWL.Class))
        g.add((part, RDF.type, OWL.ObjectProperty))
        g.add((part, RDF.type, OWL.TransitiveProperty))
        g.add((cls, RDFS.subClassOf, parent))
        for action in required:
            a = URIRef(expand_curie(action, prefixes))
            g.add((a, RDF.type, OWL.Class))
            r = BNode()
            g.add((r, RDF.type, OWL.Restriction))
            g.add((r, OWL.onProperty, part))
            g.add((r, OWL.someValuesFrom, a))
            g.add((cls, RDFS.subClassOf, r))
        yield canon, label


def build_expression(g, expr, values, prefixes):
    """Turn a template class expression into OWL triples; return its node.
    Every named class and property used is declared, so the output is a
    complete OWL 2 EL ontology on its own."""
    head = values[expr["var"]] if "var" in expr else expr["genus"]
    head = URIRef(expand_curie(head, prefixes))
    g.add((head, RDF.type, OWL.Class))
    restrictions = expr.get("restrictions") or []
    if not restrictions:
        return head
    members = [head]
    for r in restrictions:
        rnode = BNode()
        prop = URIRef(expand_curie(r["property"], prefixes))
        g.add((prop, RDF.type, OWL.ObjectProperty))
        g.add((rnode, RDF.type, OWL.Restriction))
        g.add((rnode, OWL.onProperty, prop))
        g.add((rnode, OWL.someValuesFrom, build_expression(g, r["filler"], values, prefixes)))
        members.append(rnode)
    inter = BNode()
    g.add((inter, RDF.type, OWL.Class))
    lst = BNode()
    Collection(g, lst, members)
    g.add((inter, OWL.intersectionOf, lst))
    return inter


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("templates", type=Path)
    parser.add_argument("statement_sets", type=Path, nargs="+")
    parser.add_argument("--owl", type=Path, help="Turtle output file")
    parser.add_argument("--tsv-dir", type=Path, help="Directory for DOSDP fill tables")
    parser.add_argument("--sites", type=Path, help="Turtle output for site individuals (project/sites.ttl)")
    args = parser.parse_args(argv)

    coll = load_collection(args.templates)
    prefixes, labels, kinds, templates = (
        coll["prefixes"], coll["labels"], coll["kinds"], coll["templates"])
    for t in templates.values():
        check_template(t, labels, kinds)

    g = Graph()
    for prefix, iri in prefixes.items():
        g.bind(prefix, iri)
    g.bind("obo", OBO)
    # An ontology header: ROBOT needs one, and the logical-layer files
    # (axioms.ttl, sites.ttl, projects.ttl) import this IRI.
    g.add((NODES_ONTOLOGY, RDF.type, OWL.Ontology))
    g.add((NODES_ONTOLOGY, RDFS.label, Literal("WARP node classes")))
    g.add((DEFINITION, RDF.type, OWL.AnnotationProperty))
    g.add((DCTERMS.conformsTo, RDF.type, OWL.AnnotationProperty))
    rows = defaultdict(dict)   # template -> {node: row}; deduplicates across files
    problems, count = [], 0
    seen_strategies = set()
    import warp_schema as ws
    pm = ws.prefix_map(ws.load())
    sg = Graph()
    for prefix in ("site", "ENVO", "TODO", "ISO3166-2", "warp"):
        sg.bind(prefix, pm[prefix])
    sg.add((SITES_ONTOLOGY, RDF.type, OWL.Ontology))
    sg.add((SITES_ONTOLOGY, RDFS.label, Literal("WARP sites (individuals)")))
    sg.add((SITES_ONTOLOGY, RDFS.comment, Literal(
        "Sites are particulars: OWL named individuals, never classes. Geometry is never exported.")))

    for path in args.statement_sets:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        node_types = {n["id"]: n.get("entity_type") for n in data.get("nodes") or []}
        for defn in data.get("node_definitions") or []:
            template = templates.get(defn["template"])
            if template is None:
                problems.append(f"{defn['node']}: unknown template '{defn['template']}'")
                continue
            if template_kind(template) != CLASS_EXPRESSION:
                problems.append(f"{defn['node']}: template {defn['template']} is {template_kind(template)}; "
                                "define it in its own list (strategy_definitions)")
                continue
            issues = check_definition(defn, template)
            etype = node_types.get(defn["node"])
            if etype and etype != template["camo_entity_type"]:
                issues.append(f"{defn['node']}: CAMO entity_type is {etype}, "
                              f"template {template['id']} expects {template['camo_entity_type']}")
            if issues:
                problems += issues
                continue

            values = {f["var"]: f["value"] for f in defn["fillers"]}
            names = {f["var"]: f.get("label") or f["value"] for f in defn["fillers"]}
            label = fill_text(template["name"], names)
            definition = " ".join(fill_text(template["definition"], names).split())
            refined = refinements(defn, template)
            unknown = [r for r in ("depth", "season") if defn.get(r) and r not in (template.get("refinements") or [])]
            if unknown:
                problems.append(f"{defn['node']}: template {template['id']} has no refinement {unknown}")
                continue
            if refined:
                label = f"{label}, {refined}"
                definition = f"{definition[:-1] if definition.endswith('.') else definition}, {refined}."

            cls = URIRef(expand_curie(defn["node"], prefixes))
            g.add((cls, RDF.type, OWL.Class))
            g.add((cls, RDFS.label, Literal(label)))
            g.add((cls, DEFINITION, Literal(definition)))
            g.add((cls, DCTERMS.conformsTo, URIRef(f"{PATTERN_BASE}{template['id']}.yaml")))
            expression = build_expression(g, template["equivalent_to"], values, prefixes)
            if refined:
                # A refinement narrows the node but has no logical rendering:
                # subclass, so it is never the same class as the unrefined node.
                g.add((cls, RDFS.subClassOf, expression))
                g.add((cls, RDFS.comment, Literal(f"Refined by {refined}; not rendered in the logical definition.")))
            else:
                g.add((cls, OWL.equivalentClass, expression))

            row = {"defined_class": defn["node"], "defined_class_label": label}
            for v in template["vars"]:
                row[v["name"]] = values[v["name"]]
                row[f"{v['name']}_label"] = names[v["name"]]
            if not refined:   # the DOSDP route can only write the equivalent-class form
                rows[template["id"]][defn["node"]] = row
            count += 1
            print(f"{defn['node']}  ->  {label}")

        names = {n["id"]: n.get("name", n["id"]) for n in data.get("nodes") or []}
        for canon, label in expand_strategies(g, data, templates, prefixes, names, seen_strategies, problems):
            count += 1
            print(f"{canon}  ->  {label} (strategy)")
        for sid, label in expand_sites(sg, data, pm, problems):
            count += 1
            print(f"{sid}  ->  {label} (site individual)")

    if args.owl:
        args.owl.parent.mkdir(parents=True, exist_ok=True)
        g.serialize(args.owl, format="turtle")
        print(f"wrote {args.owl} ({len(g)} triples)")
    if args.sites:
        args.sites.parent.mkdir(parents=True, exist_ok=True)
        sg.serialize(args.sites, format="turtle")
        print(f"wrote {args.sites} ({len(sg)} triples)")
    if args.tsv_dir:
        args.tsv_dir.mkdir(parents=True, exist_ok=True)
        for tid, by_node in rows.items():
            template = templates[tid]
            if template_kind(template) != CLASS_EXPRESSION:
                continue
            cols = ["defined_class", "defined_class_label"]
            for v in template["vars"]:
                cols += [v["name"], f"{v['name']}_label"]
            out = args.tsv_dir / f"{tid}.tsv"
            with out.open("w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=cols, delimiter="\t")
                w.writeheader()
                for node in sorted(by_node):
                    w.writerow(by_node[node])
            print(f"wrote {out}")

    print(f"{count} node definition(s) expanded")
    if problems:
        for p in problems:
            print(f"ERROR {p}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except TemplateError as err:
        sys.exit(f"ERROR {err}")
