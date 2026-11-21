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

`project/nodes.ttl` is one of several generated files, and the only one that
says what a node *means*. What the others may be read as, and why a statement
about a node almost never becomes an axiom in them, is in
[rdf-owl.md](rdf-owl.md). The rule that matters here: a `node:` IRI is an OWL
class everywhere it appears, and particulars — sites, projects — are
individuals under their own prefixes, never classes.

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

A shape whose part count varies (a management strategy, which is a bundle of
however many action nodes) cannot be a class-expression template, for want of
list variables. Such templates say `kind: composite` (section 8); their OWL is
generated directly from their definitions and is `rdfs:subClassOf`, not
`owl:equivalentClass`. The reason is in
[rdf-owl.md §8](rdf-owl.md#8-adding-a-group): the strategy identity key is
ordered while its part axioms are not, so equivalence would tell a reasoner
that two strategies the identity rule just held apart are the same class.

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

## 8. Templates that are not class expressions (0.7.0)

Every template above is a `class_expression` template, the default: a
fillable shape compiled to a DOSDP pattern and an OWL equivalent-class axiom.
A template can also say `kind: composite` or `kind: particular`. Neither has
vars or an `equivalent_to`, neither gets a DOSDP pattern (`make patterns`
reports them as skipped), and each is filled in its own `StatementSet` list
rather than in `node_definitions`, because a node definitions list has no type
designator to tell them apart.

| kind | Template | Filled in | OWL from |
|---|---|---|---|
| `class_expression` | everything in sections 1 to 7 | `node_definitions` | the template's `equivalent_to` |
| `composite` | `management_strategy` | `strategy_definitions` | `expand_nodes.py`, directly from the definitions |
| `particular` | `site` (Phase 7) | its own list | `expand_nodes.py`, as individuals |

### Management strategies

A **management strategy** is a set of management actions carried out
together, in a stated order: earthworks, then hand seeding two weeks later,
then mowing yearly for three years. Statements in any group can point at the
strategy as a whole (a cost for the bundle, a recommendation to do it, an
outcome of it), while its parts stay ordinary, reusable action nodes.
`management_strategy` is **the first template whose OWL is generated outside
the template machinery**: a class with a variable number of parts cannot be a
template with a fixed var list.

```yaml
strategy_definitions:
  - node: node:earthworks-seed-mow          # local ID; the canonical one is derived
    template: management_strategy
    specified_in: [doc:project-report-x]
    components:
      - {action: node:earthworks_recontouring, step: 1, role: site_preparation}
      - {action: node:hand_seeding_native_mix_a, step: 2, lag: P2W, role: establishment}
      - {action: node:mowing_weed_control, step: 3, repeat: {every: P1Y, times: 3}, role: follow_up}
```

Each component has an `action` (a node, or one level of nested strategy),
a `step` (from 1; parts that run together share it), and optionally a `lag`
and `repeat.every` (ISO 8601 durations such as `P2W`, `P1Y`), `repeat.times`,
`repeat.until` (text), a `role` (site preparation, establishment, follow-up,
maintenance, monitoring; each maps to a cost phase) and `optional: true` for
parts done only "if needed". At least two components. **There is no objective
field:** what counts as success is contested, so aims stay on statements and in
`stated_goal`.

**Identity: `warp-strategy-identity/1`** (`scripts/derive_strategies.py`, run
before proposition derivation). Nested strategies are flattened one level; the
key is the sorted list of `(step, action)` pairs of the required parts; the
canonical node is `node:strategy-<hash of the key>`. So two sources
describing the same work under different names meet at one node, a nested
and a flat description of the same steps meet, and order counts:
earthworks-then-seeding and seeding-then-earthworks are two strategies. Lags,
repeats, roles, labels and optional parts are not in the key. References to
the local ID (statement subjects, nested components) are rewritten to the
canonical one in the derived file.

**OWL** (`project/nodes.ttl`):

```turtle
node:strategy-f38f3a2661ee rdfs:subClassOf OBI:0000011 ,          # planned process
    [ owl:onProperty BFO:0000051 ; owl:someValuesFrom node:earthworks_recontouring ] ,
    [ owl:onProperty BFO:0000051 ; owl:someValuesFrom node:hand_seeding_native_mix_a ] ,
    [ owl:onProperty BFO:0000051 ; owl:someValuesFrom node:mowing_weed_control ] .
```

`BFO:0000051` (has part) is transitive and used only inside `someValuesFrom`,
so the output stays in OWL 2 EL and agrees with the one-level flattening.
Order, lags, repeats, roles and optional parts do not render; they stay in the
reification layer, where `export_rdf.py` gives each component its own IRI,
`comp:<local ID>/<n>`, so the order is addressable.

**Strategy class IRIs are stable only while their parts are.** The canonical
ID is a content hash, so changing a required part mints a new class.
`derive_strategies.py` compares with the previous derived file and records the
old ID in the definition's `replaces`; `expand_nodes.py` writes the old IRI as
`owl:deprecated true` with `IAO:0100001` (term replaced by) the new one,
because a published class IRI that silently moves is worse than one that is
formally retired.

Worked example: `examples/strategy_statements.yaml`.

### Refinements: depth and season (0.7.0)

`quality_of_environmental_material` (the object of tolerance statements:
pH of soil, temperature of water, wetness of soil) lists `refinements: [depth,
season]`. A refinement narrows a node but has no ontology class, so it is a
field of the node definition, not a template variable:

```yaml
node_definitions:
  - node: node:ph_of_soil_0_15cm
    template: quality_of_environmental_material
    fillers:
      - {var: quality, value: "TODO:ph", label: pH}
      - {var: material, value: "ENVO:00001998", label: soil}
    depth: {min: 0, max: 15, unit: "TODO:unit_centimetre"}
```

A node with a refinement is written as a **subclass** of the template's
expression, with the refinement in its label, definition and an
`rdfs:comment`, never as an equivalent class: otherwise "pH of soil, 0 to 15
cm" and "pH of soil" would have the same definition and a reasoner would make
them one class. Refined nodes are left out of the DOSDP fill tables, which can
only write the equivalent-class form. A refinement on a template that does not
list it is an error.

### Sites: the first particular (0.7.0)

Every node so far is a kind of thing: an action, a variable, a taxon, a
strategy. A **site** is one piece of ground (agreement site 0412), the place a
strategy is carried out or whose condition is assessed. It is the first node
that is a **particular**.

It is a node anyway, with the same `CausalNode` record as every other node,
because every group needs to point at sites the same way it points at nodes:
the implementation group's object, the criteria group's subject. What differs
is everything that would otherwise make one IRI mean two things (decisions D7,
D11):

- **Its own IRI space, `site:`, never `node:`.** `node:` IRIs are classes
  everywhere; `site:` IRIs are individuals everywhere, so `check_owl.py` can
  catch a mistake. `check_sites.py` refuses a site under `node:`.
- **OWL individuals, never classes.** `expand_nodes.py --sites` writes each
  site to `project/sites.ttl` as an `owl:NamedIndividual` with its label.
- **`ecosystem_type` is `rdf:type`**: the site is an instance of an ENVO
  environmental system. As an object property pointing at an ENVO class it
  would put a class where an individual belongs.
- **Jurisdiction**: an IRI (`warp:in_jurisdiction <ISO 3166-2 CA-SK>`) where
  the place has an ISO 3166-2 code or a CURIE; a literal
  (`warp:jurisdiction_name`) where it has none, as for many Indigenous
  territories. Two properties, because one OWL property cannot take both.
- **Geometry never goes into a generated file**, not even the reification
  layer. `geometry_precision` is required (exact, generalized, centroid,
  withheld); withheld means no geometry is recorded at all; GeoJSON must
  parse; exact geometry under restricted care is a warning.

```yaml
site_definitions:
  - node: "site:0412"
    template: site
    label: Agreement site 0412
    geometry_precision: generalized
    area: {value: 64, unit: "TODO:unit_hectare"}
    ecosystem_type: ["TODO:grassland"]
    jurisdiction: CA-SK
    tenure: private
    care: {access_level: restricted}
```

Projects (`proj:`) are particulars too, but they are not defined by
annotators: `derive_projects.py` mints them from implementation statements,
and `project_owl.py` writes them to `project/projects.ttl` (see
[predicate-groups.md](predicate-groups.md), the implementation group). Whether
particulars belong in the node layer at all is an open question for Lars
(`TODOS.md`).
