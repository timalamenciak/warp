# WARP in RDF and OWL

WARP's output is RDF, and OWL wherever the content allows it. This file is the
contract: which files are produced, what each one may be read as, and the rules
every predicate group follows so that the seventh group is no harder to add
than the third.

It exists because the content does not all belong in the same place. A node
template produces a class definition a reasoner can use. A statement that
*typically* soil pH between 5.5 and 8 suits blue grama, said by one database,
with a range nobody else agrees with, is not a class axiom in any logic — and
asserting it as one would state something stronger than the source did. So
WARP has two layers, and the rules below are mostly about keeping them apart.

> **Status.** Every predicate group follows this contract; each has its row
> in the register in section 8. The "state of play" table in section 9 says
> what exists. The design decisions behind it (D11 to D20) are in
> `docs/proposals/warp-0.4-dev-guide.md`.
>
> **Terminology.** The design proposals write `Claim` and `ClaimSet` where the
> code writes `Statement` and `StatementSet`. This file follows the code.

```
templates/node_templates.yaml ──▶ project/nodes.ttl         classes       OWL 2 EL
vocab/scales.yaml ────────────▶ project/scales.ttl          SKOS schemes
vocab/local/*.yaml ───────────┬▶ project/local_terms.ttl     SKOS concepts
                              └▶ project/local_classes.ttl   classes       OWL 2 EL
StatementSet *.yaml ──────────┬▶ project/statements.ttl     reification   RDF
     + *.derived.yaml         ├▶ project/sites.ttl          individuals   OWL 2 EL
                              ├▶ project/projects.ttl       individuals   OWL 2 EL
                              └▶ project/axioms.ttl         class axioms  OWL 2 EL
src/warp/schema/warp.yaml ────▶ project/warp.owl.ttl        schema        OWL 2 DL
src/warp/owl/warp-relations.ttl                             predicates    OWL 2 DL
                                                            (hand-written)
```

---

## 1. Two layers

**The reification layer** is the whole graph: every statement, proposition,
evidence line, qualifier bundle, amount, quantity and strategy component, as
RDF individuals. Scope, hedging, modality, negation, ranges, costs, order,
provenance and CARE all live here. **Nothing in it is asserted as true of the
world.** `warp:statement/x` saying that tidal restoration prevents larval
density is a record that someone said so, and the graph says exactly that.

**The logical layer** is node classes, site and project individuals, and the
few class axioms projected from propositions that pass the gate in section 6.
It is what WARP is prepared to let a reasoner use, and it is deliberately
small. On the examples in the repository today it is empty of projected
axioms, which is the correct answer for a set of assertional and prototypical
statements, not a bug to be worked around.

The layers are kept apart by three rules, one per section below: one IRI is one
kind of thing (§2), predicates are declared once as object properties (§3), and
nothing becomes an axiom without passing the gate (§6).

## 2. One IRI, one kind of thing

### 2.1 The four spaces

| Space | Kind | Holds | Written by |
|---|---|---|---|
| `node:` | OWL **class** | Actions, outcomes, environmental variables, taxa and populations, strategies ([node-templates.md](node-templates.md)) | `expand_nodes.py` (strategy IRIs come from `derive_strategies.py`) |
| `site:` | OWL **individual** | One piece of ground | `expand_nodes.py` → `sites.ttl` |
| `proj:` | OWL **individual** | The work that was done: a process instance | `derive_projects.py` → `projects.ttl` |
| `stmt:` (`warp:statement/`), `prop:` (`warp:prop/`), `warp:el/`, `doc:`, `crit:`, `comp:` …, and `<owner>/<slot>` for inlined records | RDF individual | The reification layer | `export_rdf.py` |

A `node:` IRI is a class everywhere it appears. A `site:` or `proj:` IRI is an
individual everywhere it appears. No IRI is ever both, and `check_owl.py`
fails the build if one is.

The prefixes are doing real work. Sites and projects are particulars, so they
have to be individuals; strategies and actions are kinds, so they have to be
classes; and both ends turn up in the same LinkML slot (`object: {range:
CausalNode}`) because the annotation record is the same shape for all of them.
Without separate IRI spaces there is nothing to check, and one IRI quietly
means a class in `nodes.ttl` and an individual in the statement layer depending
on which file you read.

### 2.2 How a statement points at a node class

A statement's `subject`, `predicate` and `object` are declared as **annotation
properties** in `warp-relations.ttl` (`implements: [owl:AnnotationProperty]`
in the profile says the same), and `export_rdf.py` emits them as annotation
assertions. From `project/statements.ttl`:

```turtle
stmt:kramer1995-c1 a warp:CausalStatement ;
    warp:subject   node:tidal_restoration_of_marsh ;      # an annotation assertion
    warp:predicate camo:prevents ;
    warp:object    node:volumetric_density_of_ochlerotatus_dorsalis_population_at_larval_stage ;
    warp:scope     <https://w3id.org/ecoweaver/warp/SemanticUnitScopeEnum#assertional> ;
    warp:causal_language <https://w3id.org/ecoweaver/warp/ClaimStrengthEnum#direct_causal> ;
    warp:predicate_qualifiers <https://w3id.org/ecoweaver/warp/statement/kramer1995-c1/predicate_qualifiers> .
```

The same goes for `focus`, the node a study result's data are about. Every
other slot is the object or datatype property the schema OWL declares, and
its values are IRIs or literals to match (`check_owl.py` enforces it).

**WARP's own IRIs for SEPIO's slots (Q13).** SEPIO's LinkML schema has no
`slot_uri`s and a placeholder default prefix, so its slots resolve under
`https://example.org/sepio-model/` and nothing using them could be published.
The profile sets `slot_uri: warp:<name>` in `slot_usage` for every SEPIO slot
WARP uses (`warp:subject`, `warp:statementText`, `warp:hasEvidenceLines`,
`warp:targetProposition`, …), with thin subclasses (`EcoDataItem`,
`EcoDataSet`, `EcoCoding`) for SEPIO classes the data uses directly, and
`gen-owl` runs with `--no-use-native-uris` so it honours them. `export_rdf.py`
reads every IRI from the schema. When SEPIO grounds its terms, one file of
`owl:equivalentProperty` axioms (`warp:subject owl:equivalentProperty
sepio:subject`, …) maps them, with no data change and no re-derivation.

**Relation triples.** Besides the record, each annotated statement that is not
negated contributes one triple between its subject and object, using the
predicate (or, for groups with polarity in a qualifier, a sub-property; §3.3):

```turtle
node:tidal_restoration_of_marsh camo:prevents
    node:volumetric_density_of_ochlerotatus_dorsalis_population_at_larval_stage .
```

so the relation layer reads correctly with no qualifiers. Its subject is a
node class: read as OWL, that would pun the class as an individual. That is
why `statements.ttl` is RDF for SPARQL and is never merged into the logical
layer, and why `check_owl.py` takes kinds from usage only in the OWL files.
Typing still counts there: a node IRI with an `rdf:type` in the reification
layer is an error.

An annotation assertion sits outside the logical part of the ontology, so a
class IRI may appear in it without anything being inferred and without the IRI
acquiring a second life as an individual. This is the standard OBO move, and it
is what the layer needs: the statement is *about* the class, it does not relate
instances of it.

OWL 2 DL does permit punning a class IRI as an individual. It is legal and
useless: the punned individual is a different entity from the class as far as
the semantics is concerned, so `sepio:subject` declared as an object property
would buy an assertion that says nothing about any marsh, while making every
merged file carry two unrelated meanings for one IRI. Annotation assertions say
the same thing and say it honestly. They are invisible to a reasoner, which is
the point, and fully visible to SPARQL, which is how the layer is queried.

## 3. Predicates

### 3.1 Declared once, by hand

Every predicate WARP mints is declared in `src/warp/owl/warp-relations.ttl`,
once, as an `owl:ObjectProperty`, with a label, an `IAO:0000115` definition
taken from its proposal, and `rdfs:isDefinedBy`. (Because its enum says
`implements: [owl:ObjectProperty]`, the schema OWL also types it an object
property, with the same kind; its definition and sub-property structure live
only in the relations file.) The file is hand-maintained
and never generated. A new group adds its own predicates and touches nothing
else.

Predicates from other ontologies — RO's `RO:0002303 has habitat`, CAMO's
`camo:prevents` — are **reused exactly as published and never re-declared**.

The reason is specific. By default, generating OWL from the LinkML schema
types every permissible value of a predicate enum as a class, so
`project/warp.owl.ttl` would contain:

```turtle
RO:0002470 a owl:Class ;                     # "eats": an object property in RO
    rdfs:subClassOf warp:InteractionPredicateEnum .
```

OWL 2 DL would tolerate that as punning (an IRI may be a class and an object
property at once), but the two readings are unrelated entities, so the class
says nothing about eating, and WARP's own rule is stricter: one IRI, one kind
(§2). The fix is a schema setting, not a script: `implements:
[owl:ObjectProperty]` on a predicate enum makes `gen-owl` emit
`RO:0002470 a owl:ObjectProperty` with no subclass axiom and no covering
axiom. CAMO's `CausalPredicateEnum` comes from the vendored upstream, which
the profile cannot annotate, so `clean_owl.py` does the same retyping for it
(and turns `correlated_with`'s subclass link into `rdfs:subPropertyOf`).

### 3.2 Domains and ranges: usually none

A domain or range axiom is written only when the predicate's end is a single
kind of thing. Where it varies — `has_habitat` takes an ENVO habitat while the
other three tolerance predicates take a `quality_of_environmental_material`
node; `incurs_cost` takes a category where `costs_relative_to` takes a node —
the relations file carries a comment and the group's check script enforces it
in Python. A range axiom that is wrong for one predicate in a group is worse
than no range axiom, because a reasoner will act on it.

### 3.3 Polarity belongs in the predicate

If a qualifier can reverse what a statement says, the relation layer has to
carry that in the predicate, or a triple read without its qualifiers says the
opposite of what the source said. So each such group gets an abstract parent
that is never asserted, and sub-properties the exporter chooses between:

| Group | Abstract parent | Sub-properties | Chosen by |
|---|---|---|---|
| recommendation | `warp:suggested_to` | `recommended_to_achieve`, `advised_against_for`, `suggested_for_consideration` | `guidance` |
| criteria | `warp:assessed_against` | `qualifies_as`, `does_not_qualify_as` | `direction` |
| cost | `warp:incurs_cost` | `incurs_total_cost`, `incurs_labour_cost`, `incurs_capital_equipment_cost`, `incurs_consumables_cost`, `incurs_overhead_cost` | the object category |

The qualifier stays: it is what annotators fill in and what enters the identity
key. Only the export changes.

Two cases do not become sub-properties:

- **Negation.** A statement with `negated: true` exports its reified record and
  **no relation triple at all**. There is no `did_not_prevent` predicate,
  because a null result is not a relation that holds.
- **A neutral criteria verdict.** Same treatment: the record, no triple.

Cost is the same move for a different reason. "This action `incurs_cost`
*total*" is not a relation between an action and a category: a cost is three
things at once — an action, a category and an amount — and the only part of it
that is a relation is action-to-amount. Putting the category in the predicate
leaves the amount as the object, where it belongs, and means no `costcat:` IRIs
have to be minted for things nothing can say the kind of.

## 4. Enum values

Every permissible value exports as an IRI, not a literal:

```turtle
warp:scope         <https://w3id.org/ecoweaver/warp/SemanticUnitScopeEnum#assertional> .
warp:evidence_type <https://w3id.org/ecoweaver/warp/EvidenceTypeEnum#quasi_experiment> .
```

and each value IRI is declared once as an `owl:NamedIndividual` typed by its
enum class: `implements: [owl:NamedIndividual]` on every profile enum, and
`gen-owl --default-permissible-value-type owl:NamedIndividual` for the CAMO
enums. Enum value IRIs (`…/SemanticUnitScopeEnum#assertional`) are not legal
Turtle prefixed names (`#` needs escaping in a local part), so write them out
in full in hand-written Turtle and SPARQL. Proposition IRIs are fine as
`prop:9f0b068ca33b`, since `prop:` is a declared prefix; written as
`warp:prop/9f0b068ca33b` they are not, because of the `/`.

`gen-owl` writes the covering axiom (`owl:oneOf`) directly onto the named enum
class, which does not reverse-map to OWL 2 DL, so `clean_owl.py` moves it to
`<enum> owl:equivalentClass [ a owl:Class ; owl:oneOf (…) ]`. That is the one
real LinkML defect here; the dev guide's appendix has the upstream patch.

Literals would not work. The schema declares `warp:scope` an
`owl:ObjectProperty` with `rdfs:range warp:SemanticUnitScopeEnum`, so
`warp:scope "assertional"` would put a literal in an object property's object
position, which has no OWL 2 DL reading at all. Exporting IRIs keeps both ends
consistent, and makes the value joinable with its definition and its
mappings.

**Sentinels are not values.** `not_stated`, `unknown`, `unclear`,
`not_reported` and `not_addressed` record the *absence* of something. They get
no `meaning:` in the schema, and `export_rdf.py` emits nothing for them: an IRI
asserting "there is evidence, of type not-stated" would be false, and OWL has
no null. The same goes for the explicit null that `derive_propositions.py` puts
in an identity key for a missing extra — it lives inside the key string and
reaches no slot and no file.

The list of sentinel values is in one place, `SENTINELS` in `clean_owl.py`,
which also removes them from `warp.owl.ttl`; `export_rdf.py` and
`check_owl.py` read it from there. Add to it when a group adds one.

## 5. Values, units, scales and dates

**Units** are verified CURIEs from UO, or QUDT where UO has no term. Never a
bare token: `unit: ha` and `unit: UO:hectare` are not CURIEs that resolve (UO
IDs are numeric), and in Turtle they become relative IRIs against the base —
silent garbage that looks fine until two files disagree. One quantity gets one
IRI: site area and cost scale cannot use two different hectares, or nothing
aggregates. A count of things (46 protected areas) is a count with an entity
CURIE, not a unit.

**Scales** are SKOS. `vocab/scales.yaml` lists each source scale and its values
in order; `gen_vocab.py` writes `project/scales.ttl` with one
`skos:ConceptScheme` per scale and an explicit ordinal per concept, so "medium"
can be compared with "high" without a script hard-coding DFO's ordering. A
`ScaledValue` carries the source's wording verbatim in `value`, the scheme IRI
in `scale` and the concept IRI in `concept`. A practitioner's "wet" carries no
scale and no concept, because it is not on a scale; the tolerance report says
so rather than inventing one.

**Dates and durations.** The OWL 2 datatype map contains `xsd:dateTime` and
`xsd:dateTimeStamp` and **not** `xsd:date`, `xsd:gYear` or `xsd:duration`. So:
temporal values are ISO 8601 strings in the data, at whatever granularity the
source gave (`2024-05`, `2023`, `2026-03-31`), and every exporter writes the
verbatim string plus normalized `xsd:dateTime` lower and upper bounds beside
it, on `<slot>_lower_bound` and `<slot>_upper_bound` (half-open: the upper
bound is the first instant after the value; `scripts/warp_time.py`). The bounds
are also what period-overlap tests use — `derive_projects.py`
compares bounds, never strings, because no string ordering handles `2024-05`
against `2023`.

**Structured values get IRIs, not blank nodes.** Qualifier bundles, monetary
amounts, quantities, ranges and strategy components are named individuals.
Blank nodes are not addressable across files and duplicate on merge, and
several things here must be citable: a transferred cost names the amount it was
computed from, a strategy's components carry its order, and anything in an
identity key has to be reachable.

## 6. The projection gate

A proposition becomes an OWL class axiom only when **all four** conditions
hold. `project_owl.py` prints every rejection with its reason.

| Condition | Why |
|---|---|
| `scope` is `universal` | OWL 2 has no defaults and no non-monotonic reasoning. `prototypical` means "typically, allowing exceptions", which a `subClassOf` axiom cannot express: projecting it would state something stronger than the source. `assertional` is about one plot and is not a class axiom at all. |
| `negated` is false | A null result is not a relation. |
| every grouped statement has `modality: observed` | An anticipated or inferred claim is a forecast or a derivation, not a report of how the world is. |
| a `SynthesisAssessment` supports the proposition | One statement is a source's view. An axiom is WARP's. The assessment is where that judgement is made, by people or by the synthesis pipeline, and it is revisable. |

Scope is the condition that bites, and it should. Most ecological
generalizations are prototypical, which is why WARP records scope at all. **On
the examples in this repository the gate passes nothing**, and
`project/axioms.ttl` is an ontology header with no axioms under it. That is the
right answer. If a change makes something pass, check which condition stopped
being true before believing it.

What is projected, per group, is in the register in section 8. The shape for
causal and interaction is existential subsumption, annotated with its source:

```turtle
node:soil_compaction rdfs:subClassOf _:r .
_:r a owl:Restriction ;
    owl:onProperty camo:prevents ;
    owl:someValuesFrom node:seedling_survival .
[] a owl:Axiom ;                       # the axiom annotation
    owl:annotatedSource node:soil_compaction ;
    owl:annotatedProperty rdfs:subClassOf ;
    owl:annotatedTarget _:r ;
    warp:derived_from prop:9f0b068ca33b .
```

`project_owl.py` writes the report to `project/reports/projection.md`: how
many propositions were considered, how many passed, and every condition each
rejected one failed. Groups register their projection in `PROJECTIONS`; a
group with no entry projects nothing.

Never `owl:equivalentClass`, and never a plain triple between two class IRIs.

### What never reaches OWL, at any scope

- **Guidance.** "You should do X" has no OWL rendering. A graph that cannot
  tell advice from description is worse than one that holds only description.
- **Ranges, optima, curves, amounts, efforts.** Measurements across populations
  and episodes, not class axioms.
- **Criteria verdicts.** A criteria set is a stated, versioned test and
  deliberately not an OWL definition — which is exactly what lets a definition
  change without a record being rewritten.
- **Step order, lags, repeats.** They stay addressable in the reification
  layer.
- **Costs.** There is no universal-scope cost, and if there were it still
  would not be a class axiom.

## 7. What each file means

| File | A reader may infer | A reader may **not** infer |
|---|---|---|
| `nodes.ttl` | What a node means: its genus and the relations in its definition. Classification under other node classes. | Anything about particular sites, populations or episodes. |
| `axioms.ttl` | That WARP holds this of every instance, on the evidence as currently assessed. Each axiom names the proposition it came from. | That it is settled. An assessment can change and the axiom goes with it. |
| `sites.ttl`, `projects.ttl` | That this piece of ground exists, is of these ecosystem types, is in this jurisdiction; that this project occurred, instantiating this strategy, at this site, over this period. | Anything about geometry — it is never exported. Anything about whether the project worked; that is a criteria claim. |
| `statements.ttl` | That someone said this, with this scope and hedging, on this evidence, under this CARE metadata. Relation triples read correctly on their own, including polarity. | **That anything in it is true.** Propositions are groupings, not findings; the relation triples are what a claimant asserted. |
| `warp.owl.ttl` | The shape of the records: classes, slots, ranges, enum values and their definitions. | Anything about the world. `owl:minCardinality` here is LinkML's `required`, not a constraint a reasoner should act on. |
| `warp-relations.ttl` | What each WARP predicate means, and how they nest. | Domains and ranges that are not written down; most are deliberately absent. |

The merged logical layer (`nodes.ttl` + `axioms.ttl` + `sites.ttl` +
`projects.ttl`) is OWL 2 EL and is what a reasoner should be given.
`warp.owl.ttl` and `warp-relations.ttl` are OWL 2 DL and describe the schema;
merging them into the logical layer for reasoning is a mistake. `statements.ttl`
is RDF and is for SPARQL.

## 8. Adding a group

Five questions, alongside the schema work in
[predicate-groups.md](predicate-groups.md). Answer them in the group's proposal
section and record the answers in the register below.

1. **Which predicates does it mint?** Declared once in `warp-relations.ttl`, as
   object properties, with the proposal's definitions. Reused predicates are
   named, not re-declared.
2. **What kind of thing is each end?** A class, an individual, or a value. If
   it varies by predicate, say which script checks it.
3. **Which qualifier carries polarity?** If one does, it becomes sub-properties
   (§3.3). If none does, say so explicitly.
4. **What does it export?** Which individuals, with which IRIs, and which values
   need IRIs of their own because something else will cite them.
5. **What does it project?** The default — and the answer for most groups — is
   nothing.

### The register

Management strategies are nodes, not a group, but they follow the same
rules: the canonical strategy node is an OWL class (`rdfs:subClassOf` planned
process and `has part some` per required part, never `owl:equivalentClass`),
and its components are reification-layer individuals under `comp:`, linked by
the annotation properties `warp:action` and `warp:component_of`.

| Group | Predicates | Subject → object kinds | Polarity | Projects |
|---|---|---|---|---|
| causal | CAMO (`camo:causes`, `camo:prevents`, …) | class → class | `negated`: no triple | Existential subsumption, through the gate |
| interaction | RO (`RO:0002470`, …), reused | class → class | `negated`: no triple | Existential subsumption, through the gate |
| recommendation | `suggested_to` (abstract) + `recommended_to_achieve`, `advised_against_for`, `suggested_for_consideration` | class → class | `guidance`; each `GuidanceEnum` value names its sub-property (`warp_subproperty`), and each sub-property its value (`warp:selected_by`) | **Nothing**, at any scope: deontic. The causal proposition a recommendation cites may project on its own if it passes the gate |
| tolerance | `tolerates`, `prefers`, `intolerant_of`; `RO:0002303` reused | class → class; object kind varies by predicate (`check_tolerance.py`) | none | `has_habitat` only, through the gate. Ranges, optima, class values and curves never: measurements across populations, not class axioms |
| cost | `incurs_cost` (abstract) + `incurs_total_cost`, `incurs_labour_cost`, `incurs_capital_equipment_cost`, `incurs_consumables_cost`, `incurs_overhead_cost`; `costs_relative_to` | class → amount individual (`<statement>/predicate_qualifiers/amount`, or the first effort quantity for an effort-only costing), or class → class; checked by `check_cost.py` | the object category; each `CostCategoryEnum` value names its sub-property | **Nothing** |
| implementation | `carried_out_at` | class → individual (site) | none | Nothing through the gate; the project individuals (`projects.ttl`) are its logical-layer output, and they come from the derivation rule. The grouping record is `IAO:0000136` (is about) its project |
| criteria | `assessed_against` (abstract) + `qualifies_as`, `does_not_qualify_as` | individual (site or project) → criteria set | `direction`; neutral exports no triple, and a proposition's record names `assessed_against` | **Nothing** |

Two entries in that table need their reason stated where someone will hit it:

**The criteria object is the criteria set, not the concept.** The exported
triple is `site:0412 warp:qualifies_as crit:degraded-area/fed-draft-1`, and the
concept is recoverable through the set's `operationalizes`. Keeping the set in
the object position is what stops the graph holding `site:0412 qualifies_as
degraded_area` and `site:0412 does_not_qualify_as degraded_area` as a flat
contradiction, when the two verdicts are about two different definitions. This
is the only place where the exported object is not the annotated object.

**Strategy part axioms are `rdfs:subClassOf`, not `owl:equivalentClass`.** The
strategy identity key is the sorted list of `(step, action)` pairs, so order is
part of identity and earthworks-then-seeding is a different node from
seeding-then-earthworks. Their part axioms are identical, because order does
not render in EL. Asserted as equivalence, those axioms tell a reasoner the two
nodes are the same class — contradicting the rule that just held them apart.
Asserted as subsumption they say only what is true. Nothing is lost:
containment was the only thing equivalence was wanted for, and the query class
`has_part some hand_seeding` has every strategy containing hand seeding among
its subclasses. The part relation is declared transitive and used only inside
`some`, never in a cardinality restriction, which keeps the output in EL and
makes the derivation's one-level flattening agree with the OWL.

## 9. Checks, and the state of play

`make validate` runs `check_owl.py` over every generated file, merged:

- no IRI is used as more than one kind of entity
- no `xsd:date`, `xsd:gYear` or `xsd:duration` literal
- every CURIE expands under a declared prefix, and nothing invented sits under
  a real ontology's prefix (placeholders use `TODO:`)
- no sentinel value was exported
- every predicate in a relation triple is declared in `warp-relations.ttl` or
  comes from an upstream ontology

`make owl-check` runs ROBOT, and is skipped with a warning if `robot` is not on
PATH:

```
robot merge nodes.ttl axioms.ttl sites.ttl projects.ttl | validate-profile --profile EL
robot merge warp.owl.ttl warp-relations.ttl             | validate-profile --profile DL
```

| Piece | State |
|---|---|
| `nodes.ttl`, node classes in EL, with an ontology header | Built (`expand_nodes.py`) |
| `warp.owl.ttl` | Built: `gen-owl`, then `clean_owl.py` (§9.1) |
| `warp-relations.ttl` | Hand-maintained: the annotation properties, and every predicate WARP mints for the recommendation, tolerance, cost, implementation and criteria groups. Causal and interaction reuse CAMO and RO |
| `statements.ttl` | Built (`export_rdf.py`) |
| `axioms.ttl` | Built (`project_owl.py`); empty of axioms on the examples, by design |
| `scales.ttl` | Built (`gen_vocab.py`) |
| `check_owl.py` | In `make validate`; clean |
| `make owl-check` | Written; skipped with a warning where `robot` is not on PATH. **Neither profile has been confirmed by ROBOT yet.** |
| `sites.ttl` | Built (`expand_nodes.py --sites`) |
| `projects.ttl` | Built (`project_owl.py --projects`, from `derive_projects.py`) |
| `local_terms.ttl`, `local_classes.ttl` | Built (`gen_vocab.py --local`); no class schemes yet, so no `local_classes.ttl` |
| WARP IRIs for SEPIO's slots | **Done (Q13):** `slot_uri` in the profile; a SEPIO mapping file waits on SEPIO grounding its terms. SEPIO's own classes and slots still appear under `https://example.org/sepio-model/` in `warp.owl.ttl`, which carries the vendored schema as it is; `check_owl.py` refuses them in every data file. |

### 9.1 What `clean_owl.py` does

There are eight jobs, each a function that reports
every change, and each a candidate upstream issue (`TODOS.md`, "Upstream"):

| Job | Why |
|---|---|
| `predicate_enums` | CAMO's predicate enum cannot carry `implements:`; retype its values as object properties |
| `sentinels` | absence values have no IRI (§4) |
| `annotation_restrictions` | `gen-owl` writes class restrictions on subject, predicate and object, which are annotation properties; not OWL 2 DL |
| `datatypes` | LinkML `date` becomes `xsd:date`, outside the OWL 2 datatype map; becomes `xsd:string` (only SEPIO's own `date` slot still has it) |
| `declarations` | `gen-owl` uses `slot_uri` IRIs from `slot_usage` without declaring them; OWL 2 DL needs declarations |
| `kind_conflicts` | same-named upstream attributes with different ranges (CAMO `id`, SEPIO `subtype`) come out as both object and datatype property |
| `covering_axioms` | `owl:oneOf` on a named class (R15) |
| `relative_iris` | element metadata such as `status: Draft` comes out as a relative IRI |

## Checklist for a group's RDF and OWL

- [ ] Predicates declared in `warp-relations.ttl`, once, as object properties, with definitions
- [ ] Upstream predicates reused, not re-declared
- [ ] Polarity answered: sub-properties, or an explicit "none"
- [ ] Object kind per predicate stated, and checked in a script where it varies
- [ ] Projection answered, with its reason, in the register above
- [ ] Any value another record will cite has an IRI, not a blank node
- [ ] Scales registered in `vocab/scales.yaml`; units verified or `TODO:`
- [ ] Every term chosen by `docs/terminology.md`: an ontology term, else a register entry with its upstream status
- [ ] Sentinel values listed in `clean_owl.py` and not exported
- [ ] `check_owl.py` clean; `make owl-check` passes both profiles
- [ ] The projection report says what passed and why the rest did not
