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
