# How to add a predicate group

A **predicate group** is one kind of statement: causal statements, biotic interaction
statements, occurrence statements, and so on. Each group brings:

- a **predicate list**: the controlled verbs statements can use;
- **predicate qualifiers**: what *kind* of relation is asserted (for causal
  statements: the philosophical account and causal features);
- a **statement class** and a **proposition class**, constraining subject,
  predicate and object;
- two **StatementSet lists**: one for statements, one for propositions;
- an answer to the five questions in [rdf-owl.md](rdf-owl.md): what the group
  emits in RDF, and whether any of it becomes OWL. Most groups project nothing,
  but the answer is recorded rather than assumed.

Groups share everything else: the SEPIO frame, scope, hedging conventions,
CARE metadata, evidence lines, synthesis assessments and proposition
derivation.

The repository's groups are listed at the end of this guide, each with the
test an annotator uses to tell it from its neighbours. **causal** reuses
CAMO's predicates and features. **interaction** (biotic interactions) is a
small worked example of adding a group; every step below points at it in
`src/warp/schema/warp.yaml`.

All edits go in `warp.yaml`. Never edit `upstream/`.

---

## 1. Decide what the group is for

- **What do statements in this group say?** Write three or four real examples as
  plain sentences. If they share a shape ("A ⟨verb⟩ B"), they are one group.
- **What are the subjects and objects?** Each needs a node template (see
  [node-templates.md](node-templates.md)). Interaction statements relate
  *populations*, so they use `population_of_taxon`.
- **Which features of the relation matter?** These become the predicate
  qualifiers. Keep only what changes the meaning of the relation itself.
  Hedging, scope, context and evidence are *not* predicate qualifiers; the
  shared statement frame already has places for them.

## 2. Predicate list (an enum)

One permissible value per predicate. Give each a `meaning` (a Relation
Ontology or Biolink IRI, checked in OLS) and a `rosetta_template`
annotation, which `derive_propositions.py` uses to render proposition text.

```yaml
enums:
  InteractionPredicateEnum:
    description: Predicates for biotic interaction statements, from RO.
    permissible_values:
      eats:
        meaning: RO:0002470
        annotations:
          rosetta_template: "{subject} eats {object}"
      pollinates:
        meaning: RO:0002455
        annotations:
          rosetta_template: "{subject} pollinates {object}"
```

Without a `rosetta_template`, text falls back to "{subject} ⟨predicate⟩
{object}". Add further annotations (sign, FCM weight) if downstream
renderings need them, following CAMO's `CausalPredicateEnum`.

The enum is the annotator's list, not the ontology. A predicate WARP mints is
also declared once, as an `owl:ObjectProperty`, in `src/warp/owl/warp-relations.ttl`;
predicates reused from RO or CAMO are named here and never re-declared there.
If a qualifier in your group can reverse what a statement says — the way
`negated` does — the relation layer needs sub-properties for it, or a triple
read on its own says the opposite of the source. See
[rdf-owl.md §3](rdf-owl.md#3-predicates).

## 3. Predicate qualifiers (a class)

The predicate layer: what kind of relation is asserted.

```yaml
  InteractionQualifiers:
    description: The sign of the interaction's effect on each partner.
    attributes:
      effect_on_subject:
        range: InteractionEffectEnum
      effect_on_object:
        range: InteractionEffectEnum
```

**Avoid slot names SEPIO already uses** on Statement: `direction`,
`strength`, `score`, `subject`, `predicate`, `object`, `qualifier`. CAMO's
`direction` and `strength` were renamed `causal_direction` and
`effect_strength` for this reason.

## 4. Statement class

Subclass `EcoStatement`, constrain subject, predicate and object, and add the
**registry annotations**. The annotations are how the scripts find the group,
so no script needs editing.

```yaml
  InteractionStatement:
    is_a: EcoStatement
    class_uri: warp:InteractionStatement
    description: >-
      A statement that organisms of one population interact with organisms of
      another in a particular way.
    annotations:
      warp_group: interaction                        # short name; part of the identity key
      warp_statements_slot: interaction_statements   # StatementSet list for these statements
      warp_propositions_slot: interaction_propositions
      warp_proposition_class: InteractionProposition
    slot_usage:
      subject:
        range: CausalNode
        required: true
      predicate:
        range: InteractionPredicateEnum          # the group's predicate list
        required: true
      object:
        range: CausalNode
        required: true
    attributes:
      negated:
        range: boolean
        ifabsent: "false"
      predicate_qualifiers:
        range: InteractionQualifiers
        inlined: true
```

`CausalNode` is CAMO's node record. It is the annotation record for every
group's nodes; what kind of thing a node is comes from its node template.

Three more annotations are optional:

| Annotation | Value | Use |
|---|---|---|
| `warp_identity_extras` | space-separated slot paths, in order | Fields added to this group's proposition identity key (see "Identity" below). Dotted paths reach into inlined objects: `predicate_qualifiers.guidance`. |
| `warp_identity_rule` | a rule name | Recorded on the group's propositions instead of the shared `warp-prop-identity/4`, when the group's identity is its own rule (the criteria group uses `warp-criteria-identity/1`). |
| `warp_derived_by` | a script file name | The script that derives this group's propositions, when it is not `derive_propositions.py` (the implementation group's projects come from `derive_projects.py`). `derive_propositions.py` then leaves the group alone; the checks still cover it. |

For example, a group whose guidance must split propositions:

```yaml
    annotations:
      warp_group: recommendation
      warp_statements_slot: recommendation_statements
      warp_propositions_slot: recommendation_propositions
      warp_proposition_class: RecommendationProposition
      warp_identity_extras: predicate_qualifiers.guidance
```

The proposition class must be able to hold every extra at the same path
(here, `predicate_qualifiers` with a `guidance` field): derivation copies each
extra's value from the statements onto the proposition, and open questions
written by people give their extras at the same paths.

Group-level fields every statement shares (`modality`, `context`,
`ecosystem_context`, `place`, `temporal_extent`, `specified_in`) are already
on `EcoStatement`; do not redeclare them.

Add statement-level fields a group needs beyond the shared ones (CAMO's
`causal_language` and `comparator` are examples), but check first whether
`scope`, `original_text`, `care` or evidence lines already cover it.

## 5. Proposition class

Subclass `EcoProposition` with the same constraints:

```yaml
  InteractionProposition:
    is_a: EcoProposition
    class_uri: warp:InteractionProposition
    description: A proposition put forward by biotic interaction statements.
    slot_usage:
      subject:
        range: CausalNode
      predicate:
        range: InteractionPredicateEnum
      object:
        range: CausalNode
```

## 6. StatementSet lists

Add the two lists named in the registry annotations to `StatementSet`:

```yaml
      interaction_statements:
        range: InteractionStatement
        multivalued: true
        inlined_as_list: true
      interaction_propositions:
        range: InteractionProposition
        multivalued: true
        inlined_as_list: true
```

## 7. Build, try, record

```
make lint        # camelCase warnings come from upstream SEPIO; anything else is yours
make all         # derives propositions for every group, validates, generates
```

`derive_propositions.py` reports each group it found:

```
causal: 2 proposition(s) under warp-prop-identity/4
interaction: 1 proposition(s) under warp-prop-identity/4
```

If your group is missing, the registry annotations are incomplete or the
predicate's range is not an enum.

Then:

1. Add at least one example statement to `examples/` (the interaction example is
   `warp:statement/notebook-i1` in `bloodroot_statements.yaml`).
2. Check the rendered proposition text reads sensibly.
3. Bump the schema `version` and note the new group in the README.

## Identity: what makes two statements the same proposition

All groups share identity rule `warp-prop-identity/4`: two statements share a
proposition when **group, subject, predicate, object, negated and scope**
match, **plus the group's identity extras**, in the order the group declares
them. Predicate qualifiers not named as extras do not count, so disagreements
about, say, reversibility show up as variation across statements of one
proposition rather than as separate propositions.

| Group | Identity extras |
|---|---|
| causal | none |
| interaction | none |
| recommendation | `predicate_qualifiers.guidance` |
| tolerance | `place` |
| cost | `place`, `predicate_qualifiers.phase`, `predicate_qualifiers.reporting_level` |
| implementation | its own rule, `warp-impl-identity/1` (`derive_projects.py`) |
| criteria | `predicate_qualifiers.criteria_set`, `predicate_qualifiers.assessed_period` (rule name `warp-criteria-identity/1`) |

(Later groups add theirs; the register in [rdf-owl.md](rdf-owl.md) lists every
group.)

How the key is built (`scripts/derive_propositions.py`):

- The six shared fields are joined with `|`, exactly as under rule 3, so a
  group with **no extras keeps every proposition ID it had** (the ID is a hash
  of the key; the rule version is recorded on the proposition, never hashed).
- Each extra is appended as `path=<canonical JSON>`. Objects are written with
  sorted keys and lists sorted, unless the slot is `list_elements_ordered`, so
  the same content always gives the same key.
- A **missing extra** is the JSON `null`. The statement still groups with
  others whose value is missing too, and the derivation report counts it
  under "grouped with missing key fields". The null lives only inside the key
  string; it is never written to a slot or exported.
- A missing or `unclear` **scope** still blocks grouping: the statement is
  left ungrouped and reported.

Adding an extra to an existing group changes that group's keys and therefore
its proposition IDs. Do it in its own commit, say which IDs moved in
`CHANGELOG.md`, and update `tests/test_derived_ids.py`.

If a group's identity cannot be written as an identity key at all (the
implementation group links statements by shared external IDs or overlapping
periods), give it its own derivation script and name it in
`warp_derived_by`.

## References

`scripts/check_refs.py` (run by `make validate`) checks that every reference
resolves: any slot whose range is a class and that is not inlined, so a new
group's references are checked as soon as its slots exist. Pass a statement
set together with its derived file and with anything that cites it.

## Checklist

- [ ] Predicate enum with `meaning` and `rosetta_template` for every value
- [ ] Qualifier class, no slot names that collide with SEPIO
- [ ] Statement class: `is_a: EcoStatement`, four registry annotations (plus `warp_identity_extras` if the group's identity needs more than the shared fields), subject / predicate / object constrained
- [ ] Proposition class: `is_a: EcoProposition`, same constraints
- [ ] Two StatementSet lists, named as in the annotations
- [ ] Node templates exist for the subjects and objects
- [ ] The five questions in [rdf-owl.md §8](rdf-owl.md#8-adding-a-group) answered, and the group added to its register
- [ ] Example statement; `make all` passes; version bumped

---

## The groups

### causal and interaction

What changes what; which organisms act on which. See the README.

### recommendation (0.7.0)

Guidance: a source tells someone to **do, avoid or consider** an action because
of an outcome. `RecommendationStatement`, one predicate `suggested_to`.

- **Subject**: the action as the source names it (an action node, or a
  management strategy node). Never the recommender: who gave the advice is the
  claimant, the statement's author contribution.
- **Object**: the outcome node, a change or target state ("decrease in
  abundance of the Milk River Mountain Sucker").
- **Qualifiers**: `guidance` (do / avoid / consider; required; in the identity
  key), `deontic_force` (required / recommended / suggested / optional),
  `priority` and `timing_of_influence` (`ScaledValue`s on the source's scale),
  `contribution` (direct / precursor).
- **`justified_by`**: the propositions the guidance cites, usually causal.
  Empty when the source gives no reason.

**The annotator's test: is the source telling someone what to do, or
describing what happens?** "Do X to achieve Y" is guidance. "The outcome of X
is, or was, Y" is a causal statement. When a sentence does both, record both,
and have the guidance cite the causal proposition through `justified_by`.

**Predictions are causal statements, never derived from guidance.** "If
sportfish are stocked, Mountain Sucker abundance will decrease" describes what
happens: record it as a causal statement with `modality: anticipated`, its
hedging in `causal_language`, and its basis in an evidence line
(`expert_judgment` for expert opinion, `not_stated` when the source gives
none). The guidance cites it. Nothing derives predictions from guidance
automatically: that would put claims in the source's mouth. An impact the
source says cannot be assessed is an open-question proposition, not a
prediction.

"Do prescribed burning" and "avoid prescribed burning" for the same outcome are
two propositions, because guidance is in the identity key; they may cite the
same causal proposition. Two agencies giving the same guidance share one
proposition.

In RDF the exporter writes `warp:recommended_to_achieve`,
`warp:advised_against_for` or `warp:suggested_for_consideration`, never the
abstract `warp:suggested_to`, so the relation layer cannot turn "avoid" into
"do". Nothing in this group projects to OWL, at any scope.
`scripts/report_guidance.py` (`make reports`) lists unsupported guidance,
self-supporting guidance (cited propositions resting only on the same
claimant's assertion or expert judgment), and the assessed strength of what
each recommendation cites. Example: `examples/recommendation_statements.yaml`.

### tolerance (0.7.0)

The conditions under which an organism establishes, persists or performs: the
soil pH it tolerates, the moisture regime it prefers, the salinity that
excludes it. `ToleranceStatement`, four predicates: `tolerates`, `prefers` and
`intolerant_of` (minted in `warp:`) and `has_habitat` (RO:0002303, reused).

- **Subject**: an organism node (a taxon, population or life stage:
  `taxon`, `population_of_taxon` or `taxon_at_life_stage`).
- **Object**: a `quality_of_environmental_material` node (pH of soil,
  temperature of water), or for `has_habitat` an ENVO habitat or environment
  node (`environment_type`). The kind varies by predicate, so
  `scripts/check_tolerance.py` (in `make validate`) checks it.
- **Qualifiers**: `range` (`QuantityRange`), `optimum` (`Quantity`),
  `class_value` (`ScaledValue`: Ellenberg, EIVE, USDA ratings, wetland
  indicator status), `response` (occurrence, germination, establishment,
  growth, survival, reproduction), `response_curve` (habitat suitability
  breakpoints, x strictly increasing, suitability in [0, 1]).
- **`explained_by`**: propositions giving the mechanism, usually causal.
- **`place` is in the identity key**: indicator ratings are assigned by region,
  so a species rated FACW in one region and FAC in another is two
  propositions, not a contradiction. The range is **not** in the key: two
  sources giving pH 6.0 to 8.5 and 6.5 to 8.0 agree that pH limits the species
  and differ on where, so they derive one proposition with two ranges.

**The annotator's test: is the source saying under what conditions the
organism can live, or what changes what?** "Grows on soils of pH 5.5 to 8" is
tolerance. "Compaction reduces root penetration" is causal. A tolerance
explained by a mechanism links to the causal proposition through
`explained_by`.

**`tolerates` and `intolerant_of` are recorded as stated and never derived
from each other.** A source that gives a tolerated range has not said the
organism is intolerant of everything outside it.

A habitat suitability model's **combination rule** (geometric mean, minimum,
weighted sum) is not a statement: it belongs to the model, on the source
document or an `EcoStudyResult`. Only `has_habitat` can project to OWL, and
only through the gate; ranges, optima, class values and curves never do.
`scripts/report_tolerance.py` (`make reports`) lists each proposition's ranges
by claimant and response, flags non-overlapping ranges and unit mismatches,
and never aggregates or converts. Example: `examples/tolerance_statements.yaml`.

### cost (0.7.0)

What carrying out an action took (money, staff and volunteer time,
equipment, materials) with the context needed to read the number.
`CostStatement`, two predicates: `incurs_cost` and `costs_relative_to`. The
qualifiers follow the five cost reporting standards of Iacona et al. (2018):
objective and outcome; context and method; when, where and scale; cost
categories; currency and date.

- **Subject**: an action or strategy node, the same kind of node the
  recommendation group uses, so a recommendation and the cost of following it
  meet. Strategy costs use the canonical strategy node.
- **Object**: for `incurs_cost` a cost category (`total`, `labour`,
  `capital_equipment`, `consumables`, `overhead`); for `costs_relative_to`
  another action or strategy node. The slot is `any_of` the two, and
  `scripts/check_cost.py` enforces which goes with which. A source reporting
  one total gives one statement with object `total`; a breakdown gives one
  statement per category. `unknown` is only for `includes_categories`.
- **Qualifiers**: `amount` (`MonetaryAmount`: value, ISO 4217 currency, price
  year, adjustment), `effort` and `volunteer_effort` (`Quantity`s, e.g.
  person-days), `ratio` (`CostRatio`), `scale` (always the total with its
  scale), `count` (a number of things, not a unit), `intensity`, `phase`
  (required), `covers_roles` (which strategy components a phase-level cost
  covers), `includes_categories`, `cost_behaviour`, `reporting_level`,
  `cost_basis`. Statement level: `period`, `outcome_reported` (same-source
  causal statements about what was achieved), `starting_conditions`,
  `cost_bearer`. The aim stays in the evidence layer, as the source's
  `EcoStudyResult.stated_goal`, never on the cost statement.
- **Identity**: `place`, `phase` and `reporting_level` are in the key, so
  costs from different regions, initial and maintenance costs, and an
  action's own cost and a program share never merge. Amounts, scales and years
  are not: two costings of the same work derive one proposition with two
  amounts, and a synthesis reports their spread.

`check_cost.py` (in `make validate`): `incurs_cost` needs amount or effort,
plus scale and phase; a total needs `includes_categories`; `costs_relative_to`
needs a ratio and a node; an amount with a value needs its price year (an
amount with no value records a figure not yet transcribed); `transferred_from`
needs `transfer_rule`; `covers_roles` must be roles of the subject strategy's
components.

**The annotator's test: is the source saying what an action took, or what it
did?** "Treating 600 ha took two seasons and cost NIS 17,600" is cost.
"Treatment led to regeneration of native vegetation" is causal. The cost
statement points at the causal statements through `outcome_reported`.

**Transfer is explicit.** Re-using a cost in another place, year or currency
creates a new derived cost statement, claimed by EcoWeaver, with
`transferred_from`, `transfer_rule` and `transfer_steps`
(`scripts/transfer_costs.py`, rule files in `config/cost_transfer/`). Labour
is re-priced from effort at a regional rate rather than scaling a dollar
total; other categories are indexed or left unchanged, as the rule says.
Source statements are never modified, and a cost without a value, currency or
price year is refused and reported. The shipped rule's tables are obviously
fake placeholders.

In RDF the category moves into the predicate: `<action>
warp:incurs_total_cost <amount>` (one sub-property per category), with the
amount a named individual a transferred cost can cite through
`derived_from_amount`. Nothing in this group projects to OWL.
`scripts/report_cost_completeness.py` (`make reports`) scores each costing
against the five standards and flags unknown breakdowns, payment rates and
missing values. Examples: `examples/cost_statements.yaml` and the generated
`examples/cost_statements.transferred.yaml`.

### implementation (0.7.0)

That a strategy (or action) was carried out at a site. `ImplementationStatement`,
one predicate `carried_out_at`; subject a strategy or action node, object a
site (checked by `check_sites.py`), scope always `assertional`. Qualifiers:
`period` (required; an open end means ongoing), `status` (planned,
in_progress, completed, maintained, abandoned; required, as of
`reported_on`), `reported_on` (an ISO 8601 date string), `area_treated`,
`implemented_by`, `funded_by`, `external_ids` (`{scheme, value}`, not CURIEs).
The plan document is the statement's `specified_in`.

**The annotator's test: does the source say this was done, or that it should
be done?** "We recontoured and seeded 42 ha in 2024" is implementation.
"Recontouring is recommended for sites like this" is a recommendation.
**Planned work is an implementation statement only when it is committed to a
specific site**; otherwise it is guidance.

**Projects are derived** (`scripts/derive_projects.py`, rule
`warp-impl-identity/1`, named in the group's `warp_derived_by`). Two
statements describe the same project when they share an external ID (same
scheme and value), or have the same subject, the same site and overlapping
periods, compared on normalized bounds, never as strings. Statements are
clustered with union-find. Sites match only by ID; there is no spatial
matching yet. Each project is two records (decision D17):

- the **`ImplementationProposition`**, the grouping record: member statements,
  each claimant's latest status (latest `reported_on` within that claimant
  only) and area treated, kept and attributed (42 ha from the land trust and
  40 ha from the funder, both shown), the union of implementers, funders and
  external IDs, and the envelope of periods;
- the **project individual, `proj:<id>`**, the work itself: an occurrent,
  written to `project/projects.ttl` as an instance of its strategy class,
  located in (`RO:0001025`) its site, with its period's bounds. The record is
  about it (`IAO:0000136`).

**Project IDs.** The record and the individual share their local ID. With
external IDs it is the smallest of them, `proj:<scheme>-<value>`
(`proj:agreement-0412`): a statement joining the project keeps the ID unless
it brings an external ID that sorts first. Without external IDs it is a hash
of the site, subject and earliest start: stable unless a newcomer starts
earlier. No scheme is fully stable, so `derive_projects.py` compares with the
previous derived file and records a moved ID in `replaces`; the old IRI is
written as deprecated, replaced by the new one (both behaviours are tested). A
cluster holding two different external IDs from one scheme is reported as a
candidate bad merge. Criteria statements about a project name it by its
`proj:` ID.

### criteria (0.7.0)

That a site or project meets a named, versioned definition, for a period.
`CriteriaStatement`, predicate `qualifies_as`; subject a site or project
individual (both particulars, so plainly required); object a
`CriteriaConceptEnum` value (`degraded_area`, `effective_restoration`, SKOS
concepts in `project/criteria_concepts.ttl`). The **verdict is the statement's
`direction`** (supports, disputes, neutral) and is required: criteria
statements are the one annotated statement that fills it. Qualifiers:
`criteria_set` and `assessed_period` (both required, both in the key) and
`assessment_method`.

Definitions are **`CriteriaSet`s**, information records, not nodes: one body's
versioned definition, described only by fixed elements (reference basis,
baseline date, attributes assessed, threshold kind and text, whether decline
must be human-caused, assessment unit and basis) plus the verbatim text, so a
definition never becomes its own small graph. `check_sites.py` checks that the
set operationalizes the statement's concept, and warns when the subject's kind
does not match the set's assessment unit.

**The annotator's test: is someone applying a named, versioned definition to
a site or project?** "Degraded" with no definition named is context, not a
criteria statement.

Two assessors applying the same definition and disagreeing share one
proposition, one supporting and one disputing it; "qualifies under A" and "does
not qualify under B" are two propositions and do not contradict. In RDF the
verdict picks `warp:qualifies_as` or `warp:does_not_qualify_as`, and the
relation's object is the **criteria set**, not the concept. Nothing projects to
OWL: a verdict is never inferred, which is what lets a definition change
without any record being rewritten. A rule that proposes verdicts (SHACL,
SPARQL) records them as criteria statements by EcoWeaver with
`assessment_method: rule_applied`.

`scripts/report_target2.py` (`make reports`) counts, for a jurisdiction and
year, sites degraded under a definition D, projects active on them, and those
effective under a definition E, with area as lower and upper bounds, in three
buckets (supported, contested, unsupported), and a comparison table across
definitions. Example: `examples/implementation_statements.yaml`.
