# How to add a node template

A **node template** is a fillable shape for the things statements are about, for
example *the ⟨quality⟩ of ⟨process⟩ of a population of ⟨taxon⟩*. Each time
someone fills a template (rate, population growth, *Alliaria petiolata*), the
result is one OWL class with a generated label, definition and logical
definition.

You write templates once, in LinkML-validated YAML. Everything else is
generated:

```
templates/node_templates.yaml        you edit this (validated by warp_templates.yaml)
        │
        ├── make patterns ──▶ patterns/<template>.yaml     DOSDP patterns (validated)
        │                     patterns/prefixes.yaml
        │
StatementSet node_definitions         annotators/curators fill templates here
        │
        └── make nodes ─────▶ project/nodes.ttl            OWL classes (OWL 2 EL)
                              patterns/data/<template>.tsv DOSDP fill tables (ODK input)
```

The OWL comes out the same by either route: `scripts/expand_nodes.py` writes
Turtle directly, or dosdp-tools reads the patterns and fill tables
(`make owl-dosdp`). The two routes were checked against each other with
`robot diff`: the logical axioms are identical.

---

## 1. Design the shape first

Answer these before writing YAML. Most template problems are design problems.

1. **What is the node a variable *of*?** Write it as a phrase with blanks:
   "the ___ of the ___ of a population of ___". Each blank is a variable.
2. **Leave out direction of change.** "Increased", "decreased", "removed" are
   not part of the node. The node is the variable; the statement's predicate (or
   CAMO's state/change qualifier, if you still use it) carries the change.
   That is what lets a statement of increase and a statement of decrease meet on the
   same node.
3. **Which ontology fills each blank?** Pick a root class (the variable's
   range) and the prefixes allowed. Typical choices:

   | Blank | Range root | Prefixes |
   |---|---|---|
   | taxon | NCBITaxon:131567 *cellular organisms* | NCBITaxon |
   | quality / characteristic | PATO:0000001 *quality* | PATO |
   | process | BFO:0000015 *process* | PCO, ECOCORE, GO, ENVO |
   | environmental material | ENVO material entity root | ENVO, CHEBI |
   | management action | an ELMO action root | ELMO |

4. **Is there already a template for this shape?** Reuse it if the logical
   shape is the same, even if the topic differs. Templates are about shape:
   `population_of_taxon` serves deer, garlic mustard and bees alike.
5. **Write the logical definition in words**, outermost class first:

   > a **rate** that is a *characteristic of* some (**population growth** that
   > *has participant* some (**population of organisms** that *has member* some
   > **Alliaria petiolata**))

   Bold words are either fixed classes or variables; italics are relations.

## 2. Add any new terms

Every fixed class and relation in a template needs a label in the `terms`
list, exactly as its source ontology labels it, because DOSDP writes logical
definitions with quoted labels. Look terms up in
[OLS](https://www.ebi.ac.uk/ols4/) and record the date you checked.

```yaml
terms:
  - {id: "RO:0000052", label: characteristic of, kind: object_property}
  - {id: "PCO:0000001", label: population of organisms, kind: class}
```

Labels change: RO:0000052 used to be *inheres in* and is now *characteristic
of*. If a label is out of date the generated DOSDP pattern will not match the
ontology; re-check labels when you update templates.

New prefixes go under `prefixes`. They are written to `patterns/prefixes.yaml`
for dosdp-tools and used for Turtle output.

## 3. Write the template

Add an entry under `templates:` in `templates/node_templates.yaml`. Annotated
example (the garlic mustard template):

```yaml
  - id: quality_of_process_of_population      # snake_case; becomes the pattern file name
    title: Quality of a process of a population of a taxon
    status: draft                              # draft | testing | released | deprecated
    description: >-                            # when to use it, and when not to
      A measurable characteristic (rate, magnitude, duration) of a process a
      population takes part in. ...
    camo_entity_type: taxon                    # what CAMO nodes using it must say
    vars:
      - name: quality                          # used as {quality} below
        range: "PATO:0000001"                  # root class; must be in 'terms'
        allowed_prefixes: [PATO]               # fillers must use one of these
        description: "Usually PATO:0000161 rate."
      - name: process
        range: "BFO:0000015"
        allowed_prefixes: [PCO, ECOCORE, GO, ENVO]
      - name: taxon
        range: "NCBITaxon:131567"
        allowed_prefixes: [NCBITaxon]
    name: "{quality} of {process} of {taxon} population"     # generated label
    definition: >-                                            # generated definition
      The {quality} of a {process} process whose participant is a population
      of {taxon}.
    equivalent_to:                             # the logical definition
      var: quality                             # genus: a variable ...
      restrictions:
        - property: "RO:0000052"               # characteristic of
          filler:
            var: process                       # ... or nested expressions
            restrictions:
              - property: "RO:0000057"         # has participant
                filler:
                  genus: "PCO:0000001"         # ... or a fixed class
                  restrictions:
                    - property: "RO:0002351"   # has member
                      filler: {var: taxon}
    examples:
      - "quality=PATO:0000161 process=PCO:0000011 taxon=NCBITaxon:126270"
```

The logical definition is a nested **class expression**:

- each level has **exactly one** of `genus` (a fixed class) or `var` (a
  variable), intersected with zero or more `restrictions`;
- each restriction is `property some filler`, and the filler is again a class
  expression.

That covers EL-style definitions (intersections and existential
restrictions), which is what OBO DOSDP patterns normally use and what keeps
the output in OWL 2 EL. Unions, negation, `subClassOf`-only patterns, data
properties and list variables are not supported by the generator; if you need
them, extend `scripts/templates_lib.py` and `scripts/gen_dosdp.py` together.

## 4. Generate and check

```
make patterns
```

This validates the templates file against `warp_templates.yaml`, writes
`patterns/<id>.yaml`, and runs the DOSDP validator on each. Common errors:

| Error | Fix |
|---|---|
| `X has no label; add it under 'terms'` | Add the CURIE to `terms` |
| `each class expression needs exactly one of genus or var` | A level has both, or neither |
| `logical definition uses undeclared vars` | Add the var to `vars`, or fix the typo |
| `vars never used in the logical definition` | Remove the var, or use it |
| `name uses undeclared vars` | `{placeholders}` must match var names |
| `X is declared as class, used as object_property` | Fix `kind` in `terms` |

Never edit files in `patterns/` by hand: they are regenerated.

## 5. Use the template

In a StatementSet, keep the CAMO node as the annotation record and add a
`node_definitions` entry saying which template it fills and with what:

```yaml
nodes:
  - id: node:rate_of_population_growth_of_alliaria_petiolata
    name: Population growth rate of Alliaria petiolata
    entity_type: taxon
    entity_term: Alliaria petiolata
    measured_attribute: PATO:0000161

node_definitions:
  - node: node:rate_of_population_growth_of_alliaria_petiolata
    template: quality_of_process_of_population
    fillers:
      - {var: quality, value: "PATO:0000161", label: rate}
      - {var: process, value: "PCO:0000011", label: population growth}
      - {var: taxon, value: "NCBITaxon:126270", label: Alliaria petiolata}
```

Then:

```
make nodes
```

`scripts/expand_nodes.py` checks each definition (every variable filled once,
fillers use allowed prefixes, the CAMO node's `entity_type` matches the
template's `camo_entity_type`), then writes `project/nodes.ttl` and one fill
table per template in `patterns/data/`. It exits with an error listing every
problem, so it can run in CI.

Filler `label`s are optional but make the generated label readable; without
them the CURIE is used.

**Taxa:** CAMO nodes use Wikidata QIDs in `entity_term`. OWL output needs
NCBITaxon (or another OBO taxonomy) as fillers. Keep both, and crosswalk them
in SSSOM rather than in annotations.

## 6. Use the patterns in an ODK repository (optional)

The patterns and fill tables follow the ODK conventions, so an ODK repository
(ELMO, or a future EcoWeaver nodes ontology) can build the classes itself:

1. Copy `patterns/<id>.yaml` to `src/patterns/dosdp-patterns/`. (Once the
   patterns are published at their `pattern_iri`, you can instead list the
   URLs in `src/patterns/dosdp-patterns/external.txt`.)
2. Copy `patterns/data/<id>.tsv` to `src/patterns/data/default/`.
3. With `use_dosdps: TRUE` in the ODK config, run the pattern pipeline
   (`sh run.sh make patterns`, or your onto-make equivalent). Check the ODK
   documentation for your version: the details have moved between releases.

To run dosdp-tools outside ODK, `make owl-dosdp DOSDP_TOOLS=/path/to/dosdp-tools`.

## 7. Rules of thumb

- **One template per logical shape**, not per topic.
- **Name variables for their role** (`taxon`, `process`, `quality`), not their
  current filler.
- **Keep `allowed_prefixes` tight.** It is the cheapest check against
  annotators putting a Wikidata QID where an NCBITaxon ID belongs.
- **Released templates are frozen.** Changing a released template's logical
  definition silently changes the meaning of every node made with it. Make a
  new template id instead, and set the old one to `deprecated`.
- **Document the ontological decisions in `description`**, especially the
  contested ones (for example, BFO's treatment of characteristics of
  processes as process profiles).
