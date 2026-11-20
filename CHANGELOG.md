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
