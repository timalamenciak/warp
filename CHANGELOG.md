# Changelog

All notable changes to WARP. The 0.4 proposal round
(`warp-proposals-0.4.html`, built from `warp-0.4-dev-guide.md`) ships as two
releases, **0.6.0** and **0.7.0**: the repository was already at 0.5.0 when the
work started, so "0.4.0" would have been a downgrade (dev guide, Q15b). The
documents keep their "0.4" names as the name of the proposal round only.

Each entry names the dev-guide phase it came from.

## 0.6.0 (unreleased)

Shared foundations, the identity engine and the RDF/OWL contract, with the two
existing predicate groups.

**This release changes what WARP emits as RDF.** Until 0.5.0 nothing generated
RDF for statements, and the schema OWL typed predicate IRIs as classes and
enum values as classes while data wrote literals for them. From 0.6.0:

- Four IRI spaces, and nothing crosses between them (D11): `node:` IRIs are
  OWL classes; `site:` and `proj:` IRIs are OWL individuals (from 0.7.0);
  `stmt:`/`warp:statement/`, `prop:`/`warp:prop/`, `warp:el/`, `doc:` and the
  rest are RDF individuals of the reification layer; enum values are
  individuals of their enum class. `check_owl.py` fails the build if one IRI
  is two kinds of thing.
- Statements point at node classes through annotation properties
  (`warp:subject`, `warp:predicate`, `warp:object`, D12).
- Every SEPIO slot WARP uses has a WARP IRI (`warp:statementText`,
  `warp:hasEvidenceLines`, …) instead of `https://example.org/sepio-model/…`
  (Q13). A mapping to SEPIO's IRIs will follow when SEPIO grounds them.
- `warp:prop/<hash>` keeps a slash in its local part, so it is not a legal
  Turtle prefixed name: write it in full, or as `prop:<hash>` now that `prop:`
  is declared, in hand-written Turtle and SPARQL. The same holds for enum
  value IRIs (`…/SemanticUnitScopeEnum#assertional`), whose `#` needs
  escaping.

### Phase 0: orientation and test harness

- **Build fix.** The `patterns` recipe in the `Makefile` had literal `\n`
  sequences where line continuations belonged, so `make all` failed on a clean
  checkout with a shell syntax error. Fixed.
- **Both worked examples are built.** `make derive`, `validate`, `check` and
  `nodes` now run over `bloodroot` and `kramer1995` (the second was never in
  the build). The file lists are `STATEMENTS` and `ASSESSMENTS` at the top of
  the `Makefile`.
- **Tests.** New pytest suite under `tests/`, run by `make test` and by
  `make all`. First test: every file in `examples/` validates against the
  profile.
- **`CLAUDE.md`** at the repo root: conventions, the definition of done, and
  how the code works, for anyone (or any session) picking the work up.
- **`CHANGELOG.md`** (this file) replaces the README's "Changes" section.
- `.gitignore` for Python caches.
- No derived proposition ID changed.

### Phase 1: shared foundations

- **Value classes** in the profile: `Quantity {value, unit}`,
  `QuantityRange {min, max, unit}` (either end optional, not both; `min <= max`
  checked), `ScaledValue {value, scale, concept}`, `CurvePoint {x, suitability}`
  (suitability in [0, 1]), `Count {value, entity}` and `Period {start, end}`.
  `Period` is new rather than a reuse of `temporal_extent`, because CAMO's
  `TemporalExtent` has no start or end (R2).
- **Shared statement slots.** `context`, `ecosystem_context` and
  `temporal_extent` were inline attributes on `CausalStatement`; they are now
  top-level slots on `EcoStatement`, so every group has them. Validation of
  causal statements is unchanged. New shared slots: `modality`, `place` and
  `specified_in` (plan documents, by reference).
- **`modality`** (`ModalityEnum`: observed, inferred, anticipated): whether a
  statement reports, infers or forecasts. Distinct from hedging
  (`causal_language`).
- **`place`** (decision D18): the region a statement is about, as an IRI from
  ISO 3166-2, Wikidata, GeoNames, Getty TGN, an ENVO ecoregion or a local
  `place:` concept. `ecosystem_context` keeps CAMO's functional-group range;
  both slots now say which is which. How to find a place IRI:
  `docs/values.md`.
- **`WarpEvidenceTypeEnum`** (decisions D2, D3): every CAMO evidence type, with
  the same descriptions and mappings, plus `not_stated` (the source gives no
  basis). It is the range of `EcoEvidenceLine.evidence_type`. A test fails if
  CAMO gains a value the profile enum lacks.
- **`stated_goal`** on `EcoStudyResult`: the aim as the source states it.
- **Scales as SKOS** (decision D18). `vocab/scales.yaml` registers DFO recovery
  priority and timing of influence, ECCC recovery priority, EIVE 1.0 reaction
  (binned; the binning is WARP's and marked TODO), USDA texture class, USDA
  tolerance rating and wetland indicator status; `practitioner-free` is listed
  as *not* a scale. New `scripts/gen_vocab.py` and `make vocab` write
  `project/scales.ttl`: one `skos:ConceptScheme` per scale, one `skos:Concept`
  per value, each with `warp:ordinal`.
- **Prefixes** (decision D20): `stmt`, `prop`, `doc`, `org`, `person`, `site`,
  `proj`, `comp`, `crit`, `concept`, `scale`, `place`, `TODO`, plus `UO`, QUDT
  `unit`, `ISO3166-2`, `geonames`, `tgn` and the ontologies node fillers use.
  `prop:`, `stmt:` and `doc:` expand to the paths already used under `warp:`,
  so no existing IRI changes.
- **Placeholders moved to `TODO:`.** `ELMO:TODO_planting` →
  `TODO:planting` and `ELMO:TODO_tidal_restoration` →
  `TODO:tidal_restoration`, in templates, examples and
  `examples/kramer1995.ttl` (R21). `expand_nodes.py` accepts a `TODO:` filler
  for any template variable.
- **`scripts/check_values.py`**, run by `make check`: undeclared prefixes,
  bare tokens in CURIE slots, placeholders under real prefixes, non-numeric
  OBO IDs, per-slot allowed prefixes (`warp_allowed_prefixes` annotation:
  units, places, scales), `QuantityRange` order, `ScaledValue` scale and
  concept registration, and ISO 8601 periods. Schema-driven through the new
  `scripts/warp_schema.py`.
- **Dates** (decision D19): new `scripts/warp_time.py` turns ISO 8601 years,
  year-months and dates into half-open `xsd:dateTime` bounds and tests period
  overlap on them. No slot uses LinkML `date` or `datetime` except SEPIO's
  `dateRecordCreated`.
- **OWL entity types** (R13, R14). Every profile enum now says what its values
  are with `implements:` — `owl:ObjectProperty` for predicate enums,
  `owl:NamedIndividual` for the rest — and `gen-owl` runs with
  `--default-permissible-value-type owl:NamedIndividual` for the CAMO enums
  the profile cannot annotate. `RO:0002470` and the other interaction
  predicates are now object properties, not classes. CAMO's causal predicate
  values are individuals until Phase 2.5 retypes them.
  `subject`, `predicate` and `object` are marked `owl:AnnotationProperty` on
  statements and propositions (decision D12).
- `project/nodes.ttl` now has an `owl:Ontology` header
  (`https://w3id.org/ecoweaver/warp/nodes`).
- Generators run with UTF-8 output (`PYTHONIOENCODING`), so
  `project/warp.owl.ttl` is UTF-8 on Windows too.
- New guide **`docs/values.md`**: units, counts, scales, places (including how
  to find a Wikidata or gazetteer IRI for a place) and dates.
- Tests: evidence-type mirroring, date bounds and overlap, scale vocabulary,
  value checks, shared slots and value classes, no predicate IRI emitted as an
  `owl:Class`, and the examples' proposition IDs (unchanged).

### Phase 2: identity engine and reference checker

- **Identity rule `warp-prop-identity/4`.** Groups can extend the
  proposition identity key without group-specific code, through two new
  registry annotations: `warp_identity_extras` (ordered slot paths, dotted
  paths reach into inlined objects) and `warp_identity_rule` (a rule name
  that overrides the shared one). A third, `warp_derived_by`, hands a group to
  its own derivation script. Documented in `docs/predicate-groups.md`.
- Extras are canonical JSON in the key (sorted object keys; lists sorted
  unless `list_elements_ordered`); a missing extra is an explicit `null`, so
  the statement still groups, and the derivation report counts it as
  "grouped with missing key fields". The null is never written to a slot.
  Derivation copies each extra onto the proposition. Proposition text
  templates may use an extra by name (`{guidance}`).
- **Why rule 4 and not rule 3.** The dev guide calls this rule v3 because it
  was written against 0.3.0; the code was already at v3 in 0.5.0. The rule
  version is recorded on each proposition and is **not** hashed into its ID
  (decision D4, Q11), and causal and interaction declare no extras (decision
  D1), so **no proposition ID changed**. The derived files changed only in
  `identity_rule_version` (`warp-prop-identity/3` → `/4`).
- **`scripts/check_refs.py`**, run by `make validate`: every value of a slot
  whose range is a class and that is not inlined must resolve to a record in
  the files given. Schema-driven through `warp_schema.walk()`, so later
  groups are checked as soon as their slots exist.
- `check_statements.py` now covers every registered group, including any
  derived by another script.
- Tests: key building with and without extras, missing extras, structured
  extras in a different key order, list ordering, extras read from
  annotations, idempotent re-derivation, unchanged example IDs, and
  dangling references caught (subject, nested contributor, node definition,
  `specified_in`).

### Phase 2.5: the RDF and OWL contract

- **`docs/rdf-owl.md`** corrected against the code and marked as built: the
  IRI spaces, how a statement points at a node class, relation triples, enum
  values, dates, the projection gate and its report, the state of play, and
  what `clean_owl.py` actually does. One correction of substance: the draft
  said OWL 2 DL forbids an IRI being both a class and an object property; it
  allows that as punning. WARP's one-IRI-one-kind rule is a house rule,
  stricter than OWL, and the docs now say so.
- **`src/warp/owl/warp-relations.ttl`** (hand-maintained, D13): an ontology
  with its own IRI and version IRI declaring the reification layer's
  annotation properties (`warp:subject`, `warp:predicate`, `warp:object`,
  `warp:focus`), the axiom annotation `warp:derived_from`, and
  `warp:abstract_predicate` for abstract parents. Causal and interaction reuse
  CAMO and RO predicates, which are never re-declared.
- **WARP IRIs for SEPIO's slots** (Q13, supersedes R22): `slot_uri` set in
  `slot_usage` on the profile classes for every SEPIO slot WARP uses, and new
  thin subclasses `EcoDataItem`, `EcoDataSet` and `EcoCoding` for the SEPIO
  classes the examples used directly (their `type` values in the examples
  changed accordingly). `gen-owl` now runs with `--no-use-native-uris` and
  `--xsd-anyuri-as-iri`.
- **Schema fixes found by the new checks:** `reportedIn` is narrowed from a
  string to a reference to `EcoDocument` (so `check_refs.py` covers it);
  `EcoContribution.date` is an ISO 8601 string, not LinkML `date` (D19);
  `focus` is an annotation property (D12); `TemplateFiller.value` is
  `warp:filler_term` and `EcoAgent.subtype` is `warp:agent_subtype`, because
  `warp:value` and `warp:subtype` hold other kinds of value elsewhere;
  `SynthesisAssessment.direction` and `EcoStatement.strength` restate their
  enum ranges, which `gen-owl` did not inherit.
- **`scripts/clean_owl.py`** runs on `gen-owl`'s output in `make gen`. The
  guide expected one job; there are eight, each reported: retype CAMO's
  predicate enum values as object properties, drop sentinel values, remove
  restrictions on annotation properties, replace `xsd:date`, declare
  `slot_uri` IRIs `gen-owl` uses but never declares, resolve upstream
  object/datatype property conflicts, move covering axioms off named enum
  classes (R15), and turn relative IRIs from element metadata into literals.
- **`scripts/export_rdf.py`** (`make rdf`) writes `project/statements.ttl`:
  every statement, proposition, evidence line, study result, agent and
  document as named individuals, inlined records at `<owner>/<slot>` IRIs
  (no blank nodes), enum values as IRIs, sentinels not exported, ISO dates
  verbatim plus `xsd:dateTime` bounds, and one relation triple per
  non-negated statement. Groups register polarity handling in `RELATIONS`.
- **`scripts/project_owl.py`** (`make owl`) writes `project/axioms.ttl` and
  `project/reports/projection.md`. The gate: scope universal, not negated,
  every grouped statement observed, a supporting SynthesisAssessment.
  Causal and interaction project existential subsumption with a
  `warp:derived_from` axiom annotation. **On the examples nothing passes**
  (5 propositions: assertional or prototypical), which is the correct answer.
- **`scripts/check_owl.py`** in `make validate`: one kind per IRI across every
  generated file, no `xsd:date`/`gYear`/`duration`, no relative IRIs,
  placeholders or SEPIO placeholder IRIs in data, no exported sentinels,
  every predicate declared or upstream, no abstract predicate asserted,
  literal/IRI values matching the declared property kind, and every
  restricted property declared. Clean on all generated files.
- **`make owl-check`**: ROBOT merges and `validate-profile` (EL for nodes,
  axioms, sites and projects; DL for the schema and relations), with a
  catalog for local imports. **ROBOT is not installed on the machine this was
  built on, so neither profile has been checked by ROBOT yet**; the target
  warns and succeeds without it (Q9).
- Generated ontology IRIs live under `https://w3id.org/ecoweaver/warp/ontology/`
  (`…/nodes`, `…/axioms`, `…/statements`, `…/scales`, `…/relations`), so they
  cannot collide with slot IRIs such as `warp:nodes`.
- `examples/kramer1995.ttl` is marked historical: `project/statements.ttl` is
  the generated rendering.
- Schema version **0.6.0**; examples' `profile_version` 0.6.0.
- Tests: exporter (no blank nodes, annotation properties, enum IRIs,
  sentinels, relation triples and negation, date bounds, no SEPIO
  placeholder), the gate (accepts one fixture; rejects assertional,
  prototypical, negated, anticipated, missing modality, unassessed and
  disputed, and a proposition with one anticipated statement among two),
  every `check_owl` rule, `clean_owl` (covering axioms, sentinels and nothing
  else; predicate retyping; annotation restrictions; one-value enums), and
  the generated files lint clean.
- No proposition ID changed.

## 0.5.0

Provenance the SEPIO way, and checks for what the schema cannot say. New
`EcoAgent`, `EcoContribution` (with `role`) and `EcoRecordMetadata`;
`StatementSet.agents`. Who made a statement is now a contribution with role
author (replaces `agent_kind` on the statement, which moves to the agent);
`annotator` and `annotation_timestamp` move to `recordMetadata`; evidence lines
can record who judged them (`evidence_assessor`).
`CareMetadata.knowledge_holder` (text) → `knowledge_holders` (agent ids).
`evidence_type` and `role` documented as specializations of SEPIO's `subtype`
and `activityType`. New `scripts/check_statements.py` and `make check`.
Identity rule `warp-prop-identity/3`: the key says "affirmed" rather than
"asserted"; derived proposition ids change.

## 0.4.0

Back to SEPIO's own terms. "Claim" is now "statement" throughout: `Claim` →
`EcoStatement`, `CausalClaim` → `CausalStatement`, `InteractionClaim` →
`InteractionStatement`, `ClaimSet` → `StatementSet`; slots `causal_claims` /
`interaction_claims` / `derived_from_claims` → `*_statements`, `claimant_kind`
→ `agent_kind` (`AgentKindEnum`); registry annotation `warp_claims_slot` →
`warp_statements_slot`; example ids `warp:claim/…` → `warp:statement/…`.
Profile classes get their own `class_uri`s (`warp:EcoProposition`,
`warp:EcoEvidenceLine`, …) instead of names that look like SEPIO's; example
`type` values name the concrete class. Derivation now also fills
`targetProposition` on each statement's evidence lines. Identity rule and
proposition ids unchanged.

## 0.3.0

Renamed WARP (Weaving Assertions, Reasons and Provenance), from "EcoWeaver
Claims". Namespace `https://w3id.org/ecoweaver/warp/` and CURIE prefix `warp:`
(were `.../claims/` and `ew:`); schema files `warp.yaml` and
`warp_templates.yaml`; group registry annotations `warp_*`; identity rule
renamed `warp-prop-identity/2` (same rule as before). No structural changes.

## 0.2.0

Node templates (LinkML → DOSDP and OWL); predicate group registry and the
biotic interaction group; `EcoProposition` base class; `propositions` list
renamed `causal_propositions`; identity rule v2 adds the group to the key.

## 0.1.0

First draft of the SEPIO profile.
