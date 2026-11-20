# CLAUDE.md

Working notes for anyone (person or Claude Code session) changing WARP. Read
this before touching the schema, a script or an example. The build plan for
the current round of work is `warp-0.4-dev-guide.md`; the reference for every
slot and enum is `warp-0.4-reference.html`; the graph contract is
`docs/rdf-owl.md`.

## Running the build

- `make all` runs templates → patterns → nodes → derive → validate → check →
  gen → test. It takes a few minutes, mostly `gen-owl` and `gen-json-schema`.
- `make test` runs the pytest suite in `tests/` (about ten seconds plus one
  schema load).
- Windows: GNU make is not in Git Bash. Rtools ships one: put
  `/c/rtools45/usr/bin` on `PATH` (`export PATH="$PATH:/c/rtools45/usr/bin"`).
- `robot` is not on `PATH` on the development machine. `make owl-check` warns
  and exits 0 without it (Q9); releases are checked with ROBOT.
- `pip install -r requirements.txt` installs everything, including `dosdp`,
  which `make patterns` needs.

## Conventions

- **Never edit `src/warp/schema/upstream/`.** Make every change in the profile
  (`src/warp/schema/warp.yaml`) by `is_a` and `slot_usage`.
- **Never hand-edit generated files**: `patterns/`, `project/`,
  `examples/*.derived.yaml`, and any other output a script writes. Regenerate
  them with `make`.
- **Every derivation rule has a version constant**, and every derived record
  stores the rule version that made it. Changing a rule means bumping its
  version.
- **Derived records** (propositions, canonical strategies, projects,
  transferred costs) are never written by annotators or in input examples.
- **New predicate groups** follow `docs/predicate-groups.md` and are discovered
  from schema annotations. Derivation code is group-agnostic unless a rule
  cannot be expressed as an identity key.
- **Examples are illustrative.** Mark placeholders with TODO. Never invent DOIs,
  ontology IDs or figures that could pass as real.
- **Use only ontology CURIEs you have verified.** Otherwise use a placeholder
  under the `TODO:` prefix (`TODO:planting`, never `ELMO:TODO_planting`) and add
  it to `TODOS.md`. Nothing under a real ontology's prefix is invented. Offline,
  the ECOCORE imports in `C:\ODK\harvest\ecocore\imports\*.owl` are a local
  source for BFO, RO, IAO, ENVO, PATO, PCO, PO, UBERON, CHEBI and GO IDs.
- **Every prefix an example uses is declared in the profile.** A CURIE that
  cannot be expanded is an error, not a warning.
- **The graph rules in `docs/rdf-owl.md` hold for every group**: one IRI is one
  kind of thing; predicates are declared once as object properties; polarity is
  in the predicate, never only in a qualifier; nothing becomes an OWL axiom
  unless it passes the projection gate.
- **Names.** The code says `Statement`, `StatementSet`, `EcoStatement`; the
  proposals say `Claim`, `ClaimSet`, `RecommendationClaim`. Use the code's
  names everywhere (Q1). Where a proposal sketch says `claimant`, the code's
  equivalent is a contribution with role `author`.
- **Versions.** The 0.4 proposal round ships as 0.6.0 (after Phase 2.5) and
  0.7.0 (after Phase 7), never as 0.4.0 (Q15b).
- **Ask before adding a dependency** to `requirements.txt`.

## Definition of done (every phase)

- `make all` passes, including tests, reference checks and `make owl-check`
  (from Phase 2.5 on).
- Existing examples still validate. If any derived ID changed, say which and
  why.
- Every IRI the phase introduces has exactly one kind (class, individual,
  object property, annotation property, datatype), and `scripts/check_owl.py`
  is clean (from Phase 2.5 on).
- An entry in `CHANGELOG.md` under the unreleased version, naming the phase.
- Docs updated where the phase changed behaviour (`README.md`, `docs/*.md`).
- Open questions not resolved are added to `TODOS.md`, citing the proposal and
  its question number.
- Tests for every new rule, check and script.
- One commit: `warp 0.4: <phase name>`.

## How the code works

### Predicate group registry

A group is any `EcoStatement` subclass in `warp.yaml` carrying these class
annotations, read by `load_groups()` in `scripts/derive_propositions.py`:

| Annotation | Meaning |
|---|---|
| `warp_group` | short name; first field of the identity key |
| `warp_statements_slot` | `StatementSet` list holding the group's statements |
| `warp_propositions_slot` | `StatementSet` list holding its propositions |
| `warp_proposition_class` | the group's proposition class |
| `warp_identity_extras` | optional: ordered slot paths added to the identity key |
| `warp_identity_rule` | optional: rule name recorded instead of the shared one |
| `warp_derived_by` | optional: the script that derives the group, if not `derive_propositions.py` |

The predicate enum is found as the induced range of `predicate` on the
statement class; `rosetta_template` annotations on its values render
proposition text.

### Proposition identity and IDs

Rule `warp-prop-identity/4` (constant `RULE_VERSION`; rule 3 until 0.6.0).
The key is `"|".join([group, subject, predicate, object,
"negated"|"affirmed", scope])`, followed by `path=<canonical JSON>` for each
of the group's `warp_identity_extras` (missing extras are `null`). Causal and
interaction declare no extras, so their keys are what they were under rule 3.
The proposition ID is `"warp:prop/" + sha1(key)[:12]`. **The rule version is
not part of the hash** (it is recorded on the proposition as
`identity_rule_version`), so a rule change that leaves a group's key string
unchanged leaves its IDs unchanged (D4, Q11). Statements whose scope is
missing or `unclear` are not grouped and are reported. Propositions written by
people with `status: open_question` keep their IDs.

### Slots on CausalStatement

- Inherited from SEPIO `Statement` (attributes, not top-level slots):
  `subject`, `predicate`, `object`, `proposition`, `statementText`,
  `direction`, `strength`, `hasEvidenceLines`, `contributions`,
  `recordMetadata`, `reportedIn`, `dateAuthored`.
- Top-level slot from the profile: `scope`.
- Inline attributes on `EcoStatement`: `original_text`, `source_spans`, `care`.
- Inline attributes on `CausalStatement` (0.5.0): `negated`, `causal_language`,
  `predicate_qualifiers`, `comparator`, `context`, `ecosystem_context`,
  `temporal_extent`, `camo_edge_id`. Phase 1 promotes `context`,
  `ecosystem_context` and `temporal_extent` to shared slots.

### Claimant

There is no `claimant` slot. The claimant is the `contributor` of the
statement's `EcoContribution` with `role: author`. The EcoWeaver synthesis
pipeline, as claimant of `SynthesisAssessment`s, is the agent
`warp:agent/ecoweaver-synthesis` (`agent_kind: synthesis_pipeline`).

### Types of `temporal_extent` and `ecosystem_context`

- `temporal_extent`: CAMO `TemporalExtent` (`duration_months`,
  `duration_text`, `lag_months`, `observation_grain`, `observation_seasons`).
  It has **no start or end**, so periods use the profile's own `Period` class.
- `ecosystem_context`: CAMO `EcosystemFunctionalGroupEnum`, the IUCN Global
  Ecosystem Typology functional groups (110 values). A kind of ecosystem, not
  a place: places go in `place`.

### Shared helpers (0.6.0)

- `scripts/warp_schema.py`: cached SchemaView, the prefix map of the profile
  and its imports, CURIE expansion, and `walk()`, which yields every slot
  value of a StatementSet with its class and induced slot. Use it for any
  new schema-driven check rather than hard-coding slot names.
- `scripts/warp_time.py`: ISO 8601 strings to half-open `xsd:dateTime`
  bounds, and period overlap. Never compare date strings.
- `scripts/check_values.py`: CURIEs, units, places, scales and dates. Slots
  restrict their prefixes with a `warp_allowed_prefixes` annotation.
- `scripts/gen_vocab.py`: `vocab/scales.yaml` to SKOS.

### Templates to OWL and DOSDP

- `scripts/templates_lib.py` loads `templates/node_templates.yaml` and checks
  each template (every var used, every fixed term labelled).
- `scripts/gen_dosdp.py` writes one DOSDP pattern per template to `patterns/`
  (Manchester text built from term labels) plus `patterns/prefixes.yaml`.
- `scripts/expand_nodes.py` reads the `node_definitions` of each StatementSet,
  checks fillers against the template (allowed prefixes, entity type), and
  writes each node as an `owl:Class` with label, `IAO:0000115` definition and
  an `owl:equivalentClass` intersection to `project/nodes.ttl`, plus DOSDP fill
  tables in `patterns/data/`.

### RDF and OWL (0.6.0)

- `project/warp.owl.ttl`: `gen-owl $(OWLGEN_FLAGS)` then `scripts/clean_owl.py`
  (eight reported jobs; see `docs/rdf-owl.md` §9.1). Enum values are
  individuals, predicate enum values object properties, SEPIO slots WARP uses
  have `warp:` IRIs via `slot_uri` in `slot_usage` (Q13).
- `src/warp/owl/warp-relations.ttl`: hand-maintained; every predicate WARP
  mints, abstract parents marked `warp:abstract_predicate true`, and the
  annotation properties `warp:subject`/`predicate`/`object`/`focus`.
- `project/statements.ttl`: `scripts/export_rdf.py`, schema-driven. Group
  polarity hooks go in its `RELATIONS` dict.
- `project/axioms.ttl` + `project/reports/projection.md`:
  `scripts/project_owl.py`. Group projections go in its `PROJECTIONS` dict;
  no entry means the group projects nothing.
- `scripts/check_owl.py` (in `make validate`) must stay clean. Sentinel
  values are listed once, in `SENTINELS` in `clean_owl.py`.
- New slot names: if a slot name already exists elsewhere with a different
  kind of value (literal vs IRI), give the new one its own `slot_uri`, or
  `check_owl.py` will report the IRI as two kinds.

### Where each kind of OWL entity came from (0.5.0, before the contract)

- `project/nodes.ttl` (`expand_nodes.py`): node classes, the object properties
  used in their definitions, `IAO:0000115` and `dcterms:conformsTo` as
  annotation properties. No `owl:Ontology` header in 0.5.0.
- `project/warp.owl.ttl` (`gen-owl`): every class, slot and enum of the
  profile and both upstreams. Enum values, including predicate IRIs such as
  `RO:0002470`, come out as `owl:Class` with `rdfs:subClassOf` the enum, and
  each enum class carries `owl:unionOf` directly. Enum-ranged slots are
  `owl:ObjectProperty` with the enum class as range, while data writes
  literals for them.
- Nothing generates RDF for statements or propositions in 0.5.0:
  `examples/kramer1995.ttl` is hand-written and is the specification for
  `export_rdf.py`. It uses node class IRIs as objects of `sepio:subject`,
  which would pun them as individuals if `sepio:subject` were an object
  property.

## Where the 0.4 proposals' sketches differ from the code

Listed in Phase 0 and resolved in the phases that touch them:

- `Claim`, `ClaimSet`, `causal_claims`, `RecommendationClaim` → `Statement`,
  `StatementSet`, `causal_statements`, `RecommendationStatement` (Q1).
- `claimant: org:dfo` → a contribution with `role: author` and a `contributor`
  agent ID.
- Sketch IDs use prefixes the profile did not declare (`stmt:`, `prop:`,
  `org:`, `site:`, `proj:`, `comp:`, `crit:`, `scale:`, `dfoprio:`) (D20).
- `predicate: warp:suggested_to` and `predicate: camo:decreases`: predicates
  are enum value names (`suggested_to`, `prevents`), not CURIEs, and CAMO has
  no `decreases`.
- `causal_language: hedged` is not a CAMO `ClaimStrengthEnum` value
  (`no_relationship`, `associational`, `uncertain_causal`, `direct_causal`).
- `evidence_type: expert_opinion` → CAMO's `expert_judgment` (D2).
- `QuantityValue` → `Quantity` (R1); `Period` vs `temporal_extent`: CAMO's
  `TemporalExtent` has no start or end, so `Period` is new (R2).
- Registry keys such as `warp_group` placeholders → the four real `warp_*`
  annotations (R11).
- `ImplementationProposition # = project` and `subject_proposition` → a
  project individual under `proj:` (D17, R18).
- `predicate_qualifiers` declared under `attributes` in the implementation
  sketch, as an inline attribute per group in the code (R6).
- `ecosystem_context: florida-usa` and similar: regions are not
  `EcosystemFunctionalGroupEnum` values → `place` (D18, R19).
- Units such as `UO:hectare`, `ha`, `protected_area` → verified CURIEs or
  `TODO:` placeholders, and counts as `Count` (R20).
- The identity rule is already `warp-prop-identity/3` in 0.5.0 (the guide was
  written against 0.3.0, where it was v2), so the per-group extras rule is
  `warp-prop-identity/4`, not v3.
