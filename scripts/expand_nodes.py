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
import sys
from collections import defaultdict
from pathlib import Path

import yaml
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS, DCTERMS

from templates_lib import (
    TemplateError, check_template, expand_curie, fill_text, load_collection,
)

OBO = Namespace("http://purl.obolibrary.org/obo/")
DEFINITION = OBO.IAO_0000115
PATTERN_BASE = "https://w3id.org/ecoweaver/patterns/"


def check_definition(defn, template):
    tid = template["id"]
    node = defn["node"]
    declared = {v["name"]: v for v in template["vars"]}
    filled = defaultdict(list)
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
        if prefix not in allowed:
            problems.append(f"{node}: var '{name}' = {fs[0]['value']} must use one of {allowed}")
    return problems


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
    g.add((DEFINITION, RDF.type, OWL.AnnotationProperty))
    g.add((DCTERMS.conformsTo, RDF.type, OWL.AnnotationProperty))
    rows = defaultdict(dict)   # template -> {node: row}; deduplicates across files
    problems, count = [], 0

    for path in args.statement_sets:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        node_types = {n["id"]: n.get("entity_type") for n in data.get("nodes") or []}
        for defn in data.get("node_definitions") or []:
            template = templates.get(defn["template"])
            if template is None:
                problems.append(f"{defn['node']}: unknown template '{defn['template']}'")
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

            cls = URIRef(expand_curie(defn["node"], prefixes))
            g.add((cls, RDF.type, OWL.Class))
            g.add((cls, RDFS.label, Literal(label)))
            g.add((cls, DEFINITION, Literal(definition)))
            g.add((cls, DCTERMS.conformsTo, URIRef(f"{PATTERN_BASE}{template['id']}.yaml")))
            g.add((cls, OWL.equivalentClass,
                   build_expression(g, template["equivalent_to"], values, prefixes)))

            row = {"defined_class": defn["node"], "defined_class_label": label}
            for v in template["vars"]:
                row[v["name"]] = values[v["name"]]
                row[f"{v['name']}_label"] = names[v["name"]]
            rows[template["id"]][defn["node"]] = row
            count += 1
            print(f"{defn['node']}  ->  {label}")

    if args.owl:
        args.owl.parent.mkdir(parents=True, exist_ok=True)
        g.serialize(args.owl, format="turtle")
        print(f"wrote {args.owl} ({len(g)} triples)")
    if args.tsv_dir:
        args.tsv_dir.mkdir(parents=True, exist_ok=True)
        for tid, by_node in rows.items():
            template = templates[tid]
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
