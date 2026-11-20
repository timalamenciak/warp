# WARP 0.4: implementation guide for the proposal set

This guide consolidates five draft proposals into one build plan for WARP,
and gives a Claude Code prompt for each step. It is written against WARP 0.3.0.

| Proposal | File | Adds |
|---|---|---|
| Recommendation group | `docs/proposal-recommendation-group.html` | `suggested_to` guidance statements |
| Management strategy node | `docs/proposal-management-strategy.html` | Ordered bundles of actions as one node |
| Tolerance group | `docs/proposal-tolerance-group.html` | Ranges and optima of taxa on environmental variables |
| Cost group | `docs/proposal-cost-group.html` | What actions took to carry out, following Iacona et al. (2018) |
| Implementation, sites and definitions | `docs/proposal-implementation-group.html` | Sites, `carried_out_at`, derived projects, criteria sets, `qualifies_as` |

It also covers the "related changes" the proposals list (`modality`,
`not_stated`, shared value types, `stated_goal`). Optional Phase 9 covers the
additions from `docs/feedback-models-compatibility.md`, plus `ThreatAssessment`.

**This revision adds the graph.** The proposals say what each group records but
not what any of it becomes in RDF, and WARP's goal is RDF-OWL wherever the
content allows it. So this guide now carries ten decisions about the graph
(section 3.1, D11 to D20), ten resolutions for places where the sketches would
have produced something that is not OWL 2 (section 4, R13 to R22), and one new
phase, 2.5, that puts the contract in code before the groups are built on it.
Four of the problems it fixes are in 0.3 already, and seven groups would have
multiplied them.

---

## 0. Questions for you to resolve

Everything else in this guide has a default and proceeds without you. These
fifteen do not, either because the default could be wrong for this project,
because they change records that already exist, or because the answer is not
mine to give. Write your answer in the last column; where you accept the
default, "yes" is enough.

The **Needed by** column is when an unanswered question starts to cost
something. Q1, Q2 and Q13 are the ones I would settle first: the first two
change files from Phase 1 onwards, and the third decides whether any of this
can be published at all.

| # | Question | Default if you say nothing | Needed by | Your answer |
|---|---|---|---|---|
| Q1 | **`Claim` or `Statement`?** The proposals' sketches say `Claim`, `ClaimSet`, `RecommendationClaim`; the code says `Statement`, `StatementSet`, `EcoStatement`. No decision in this guide covers it, and Prompt 3 would fail as written. | Keep the code's `Statement` and translate the proposals' `Claim` wherever a prompt quotes a sketch. Renaming is a separate, breaking change, not something to slip into a feature release. | Phase 1 | `Statement` is correct and should be used everywhere. |
| Q2 | **Add `place` at all?** (D18) This is my addition, not the proposals'. It fixes regions being written into a slot that ranges over functional groups, but it adds a claim-level slot and changes what tolerance and cost propositions group on. | Add it, and use it in place of `ecosystem_context` in the tolerance and cost identity keys. | Phase 1 | Yes, place is good since that can be more informative than a geospatial coordinate (as in that the claim could apply to an entire municipality instead of some unclear range around its geographic centre). Make sure to add guidance on finding URIs for placenames - Wikidata and gazetteer. |
| Q3 | **Identity: per group, or everywhere?** (D1) Putting context-of-place in every group's key changes causal and interaction proposition IDs. | Per group, as the proposals say. Causal and interaction keep their current keys, so no existing ID moves. | Phase 2 | Correct. |
| Q4 | **Is the projection gate right?** (D15) Universal scope, not negated, observed modality, and a supporting assessment. On today's examples it passes nothing, which is the honest answer but may not be the one you want from a 0.4 release. | Keep it strict. Loosening it later is cheap; retracting axioms other people have already reasoned over is not. | Phase 2.5 | Correct. |
| Q5 | **Mint polarity sub-predicates?** (D16) Nine more IRIs to define, document and maintain, so that a triple read without its qualifiers cannot say the opposite of its source. | Mint them. The alternative is a relation layer that silently inverts "avoid" into "do". | Phase 2.5 | Correct. |
| Q6 | **Project as an individual?** (D17) You had settled D8 as `CriteriaClaim` with `subject_proposition`. I changed it, because that makes an effectiveness verdict an assertion about a record rather than about the work. | Mint `proj:` individuals, and drop `subject_proposition` and the `exactly_one_of` rule with it. | Phase 7.2 | I don't understand this and need more detail. |
| Q7 | **Work around LinkML, or push upstream first?** (D13) `clean_owl.py` post-processes `gen-owl` output for ever, and `warp-relations.ttl` is hand-maintained alongside the schema. | Work around it now, file the upstream issues, and drop the workaround if LinkML lands a fix. Waiting blocks everything. | Phase 2.5 | Yes, but also outline the upstream linkML fix since I could potentially implement that. **→ The appendix at the end of this guide. Two of the three problems were not LinkML bugs: they are `implements:` settings WARP never used, now folded into Phase 1. The third has a ten-line patch, tested.** |
| Q8 | **UO or QUDT for units?** (D18) You may already have a house answer from ELMO or CAMO that I should follow instead. | UO first, QUDT only where UO has no term, and a `TODO:` placeholder rather than a guessed CURIE. | Phase 1 | Suggestion seems correct. |
| Q9 | **ROBOT as a build dependency?** It is the only thing that can check an OWL profile, and the repo asks before adding dependencies. | Optional: `make owl-check` warns and continues when `robot` is absent, and releases are checked with it. | Phase 2.5 | Correct approach. |
| Q10 | **Where does `not_stated` live?** (D3) | A profile enum mirroring CAMO's plus `not_stated`, with a TODO to propose it upstream. | Phase 1 | Yes, todo for upstream. This should be in some evidence ontology. |
| Q11 | **Proposition IDs under rule v3** (D4). If the current code hashes the rule version, bumping to v3 changes every existing ID. | Do not hash it. If the code already does, Claude Code stops and asks rather than rewriting IDs silently. | Phase 2 | Correct. |
| Q12 | **Units, scales and placeholders in examples.** Phases 3 to 7 need real CURIEs for hectares, person-days, ELMO actions and ENVO types. I cannot verify any of them offline. | Leave `TODO:` placeholders and hand you the list at Phase 8. Nothing invented goes under a real ontology's prefix. | Phase 8 | Correct. |
| Q13 | **SEPIO's `example.org` namespace.** `subject`, `predicate`, `object` and the evidence slots have no real IRIs, so the reification layer cannot be published however much else gets built. Not fixable inside this repo. | Confine it to one constant and keep building; settle it with the semantics working group before 0.5. | Before publishing | **Mint WARP IRIs now; map to SEPIO later.** Set slot_uri in the profile for the SEPIO slots WARP uses and generate with --no-use-native-uris; publish an equivalentProperty mapping file when SEPIO grounds its terms. See 0.1. |
| Q14 | **What goes to Lars, and when?** Particulars in the node layer (D7), whether part-to-part `precedes` relations are wanted on strategies (D6), and tolerance as a BFO disposition. Each is narrower than it was; none is closed. | Build on the defaults and take all three to him once Phase 7 exists, so there is something concrete to react to. | Phases 4, 7 | **One conversation, after Phase 7, with the generated files in hand.** Particulars first, disposition second, precedes third. Send docs/rdf-owl.md and the TTL, not the proposals. See 0.1. |
| Q15 | **Target 2 counting rules** (D9), **release shape** (D10), and whether **Phase 9** runs at all. Policy and scope, not modelling. | D9 as written, reported so the effect of the choice is visible; one 0.4.0 release with one commit per prompt; Phase 9 only when you ask for it. | Phases 7.3, 8 | **D9: keep the defaults but report three buckets, not two. D10: the version is wrong and the release should be split. Phase 9: not in this release.** See 0.1. |

### 0.1 Q13 to Q15, answered

You asked me to settle these three. Here they are, with the reasoning, so you
can overrule any of them knowing what it rests on.

#### Q13. SEPIO's namespace: mint WARP IRIs now, map later

`subject`, `predicate`, `object`, `hasEvidenceLines` and `targetProposition`
resolve under `https://example.org/sepio-model/`, so nothing WARP publishes can
be dereferenced. Three options: wait for SEPIO, mint under a SEPIO-looking
namespace, or mint under WARP's own.

**Mint under WARP's own.** Waiting is not a decision, it is a deferral to
someone else's roadmap: SEPIO today has no `class_uri`, no `slot_uri` and a
placeholder default prefix, and the README already names grounding it as the
single most valuable upstream PR — which is to say it has not happened.
Minting under something like `ecoweaver/sepio/` is worse than either, because
it implies a governance over SEPIO's terms that EcoWeaver does not have.

The mechanism is in the profile, not in a script, and it needs no change to
`upstream/`. LinkML's OWL generator uses native model URIs by default, which is
why SEPIO slots currently come out under `example.org`; with
`--no-use-native-uris` it honours `slot_uri`, and `slot_usage` can override it
per class. I checked this on linkml 1.11.1: a slot declared
`slot_uri: up:inherited_slot` on the base class and overridden in a subclass's
`slot_usage` emits both IRIs correctly, each on the right class.

So: set `slot_uri` in `EcoStatement`'s and `EcoProposition`'s `slot_usage` for
the SEPIO slots WARP actually uses, generate with `--no-use-native-uris`, and
have `export_rdf.py` read the same IRIs from the schema rather than from a
constant of its own. **This supersedes R22 and the one-constant instruction in
Prompt 2.5.**

What it costs later is one Turtle file: `warp:subject owl:equivalentProperty
sepio:subject` and a dozen like it, added when SEPIO grounds. No data changes,
no re-derivation, no ID churn. And still file the upstream PR — WARP having
its own IRIs makes that PR easier to argue, not harder, because the mapping
file demonstrates what the grounding is for.

#### Q14. Lars: one conversation, after Phase 7, with the files in hand

Not three questions on three occasions. All three are versions of "is this
layering ontologically respectable?", and asking them separately invites three
debates instead of one review. After Phase 7 there is something to react to:
`nodes.ttl`, `sites.ttl`, `projects.ttl`, `axioms.ttl` and the contract that
produced them.

Order them by what rework costs:

1. **Particulars in the node layer (D7).** The only one that could cause
   rework. If sites should not be nodes, `NodeDefinition`, the implementation
   group's object range and the Target 2 query all change. Ask first.
2. **Tolerance as a BFO disposition.** Decides whether tolerance ever projects
   beyond `has_habitat`. A template's worth of rework, not the architecture's.
3. **Part-to-part `precedes` on strategies (D6).** Pure addition. It can land
   in a later release without touching anything that exists.

Send him `docs/rdf-owl.md` and the generated Turtle. Not the proposals page,
which argues a case, and not this guide, which is a build plan. An ontologist
reacts to axioms.

One thing **not** to ask: whether `prototypical` should project to OWL. That
is settled by OWL 2 having no defaults and no non-monotonic reasoning, not by
taste, and putting it on a list of open questions invites an answer we would
have to refuse.

#### Q15a. Target 2 counting: three buckets, not two

Keep D9's defaults, keep every one of them behind a flag, and keep the
comparison table that shows what each definition set would mean. But change
one thing: **"supported" as "at least one supporting claim and no disputing
claim" is too brittle for a national indicator.** One disputing claim from any
claimant removes a site from the total, which makes the number sensitive to a
single assessor and is an obvious thing to game.

Report three buckets — supported, contested, unsupported — and let the
reporting policy choose which count. Contested propositions are already listed
separately in D9; this promotes them from a footnote to a column. It costs
nothing, it is more honest about what the records say, and making exactly this
kind of choice visible is why WARP holds disagreement instead of resolving it.

#### Q15b. Release shape: fix the version first, then split

**The version numbering is already wrong, and this guide would make it worse.**
`src/warp/schema/warp.yaml` says `version: 0.5.0`, `profile_version` defaults
to `0.5.0`, and the README says "Status: draft 0.5.0". The README's changelog
shows 0.4.0 and 0.5.0 both shipped. This whole body of work is called 0.4, and
Prompt 8 says "bump the schema version to 0.4.0" — which would be a downgrade
over what is in the repo today.

So: this work ships as **0.6.0 and 0.7.0**, and the documents keep their "0.4"
names only as the name of the proposal round. Rename at Phase 8 and say so in
the changelog.

Split it in two, rather than one release:

- **0.6.0 after Phase 2.5.** Shared foundations, the identity engine, and the
  graph contract, with the two existing groups. This changes what every
  generated file emits, so it deserves its own release note and its own chance
  to be found wrong before five groups sit on top of it. It is also what makes
  Q14's conversation possible earlier than Phase 7.
- **0.7.0 after Phase 7.** The five new groups and three templates.

One release of seven groups, three templates, a graph contract, five scripts
and a schema-wide `implements:` pass is hard to review and impossible to
bisect.

#### Q15c. Phase 9: not in this release

- **9.1 (lag, state variables, effect size, self-regulation)** touches the
  causal predicate qualifiers, which are the one part of the schema that
  already works and whose proposition IDs are stable. It is also the one with
  real downstream value, for the feedback models. It deserves its own proposal
  and its own release, not a tail on this one.
- **9.2 ThreatAssessment** and **9.3 rate-of-interaction** are small and purely
  additive. Any time after Phase 8, when someone wants them.
- **9.4 the tolerance importer** is gated on source licences, which is a people
  problem and will not get faster by being scheduled.

---

**What is not on this list, and why.** D2 (use CAMO's `expert_judgment`), D5
(no DOSDP pattern for strategies), D11, D12, D14, D19 and D20 are forced:
either by OWL 2 itself — an IRI cannot be two kinds of thing, `xsd:date` is
not in the datatype map — or by conventions this repo already follows. I would
not spend your time on them. They are still written up in sections 3 and 3.1
with their reasons, so you can overrule any of them; you just do not have to
decide them for the work to start.

---

## 1. How to use this guide

1. **Answer section 0, then skim section 3.** Section 0 is the short list that
   needs you; section 3 is every decision, with the default each prompt uses.
   If you choose differently, edit the prompt where it cites the decision (D1,
   D2 and so on). Section 3.1 holds the decisions about the graph, D11 to D20:
   they are new in this revision, Phase 2.5 implements them and every group
   phase depends on them, so changing one means changing 2.5 and each phase
   that cites it.
2. **Run the phases in order** (section 5). Use one Claude Code session per
   prompt, and run `/clear` between them. For Phases 2, 2.5, 4, 6 and 7, start
   in plan mode so you can review the plan before any files change.
3. **Prompt 0.1 writes a `CLAUDE.md`** with the repo's rules and a Definition
   of done. Every later prompt relies on it, so the prompts stay short.
4. **Review each phase before committing** (checklist in section 7). Work on one
   branch, `warp-0.4`, with one commit per prompt.
5. The prompts expect the proposals at `docs/proposal-*.html`, where they sit in
   the project. If your checkout lacks them, copy them there first.

---

## 2. What gets built

### 2.1 Predicate groups after 0.4

| Group | Predicates | Subject → object | Identity key beyond the v2 fields* | Rule |
|---|---|---|---|---|
| causal | CAMO predicates | node → node | none (see D1) | `warp-prop-identity/3` |
| interaction | RO predicates | node → node | none (see D1) | `warp-prop-identity/3` |
| **recommendation** | `warp:suggested_to` | action or strategy → outcome node | `guidance` | `warp-prop-identity/3` |
| **tolerance** | `warp:tolerates`, `warp:prefers`, `warp:intolerant_of`, RO `has habitat` | organism node → environmental variable or habitat node | `place` | `warp-prop-identity/3` |
| **cost** | `warp:incurs_cost`, `warp:costs_relative_to` | action or strategy → cost category, or → action | `place`, `phase`, `reporting_level` | `warp-prop-identity/3` |
| **implementation** | `warp:carried_out_at` | strategy or action → site | Derived projects: shared external ID, or same strategy, same site and overlapping period | `warp-impl-identity/1` |
| **criteria** | `warp:qualifies_as` | site, or derived project → concept | `criteria_set`, `assessed_period` | `warp-criteria-identity/1` |

\* v2 fields: group, subject, predicate, object, negated, scope.

The identity extras say `place`, not `ecosystem_context`, because every example
in the proposals puts a region there and `ecosystem_context` ranges over CAMO's
functional groups. See decision D18.

Each group also declares what it emits in RDF, and whether it projects to OWL
at all (section 2.6, decisions D11 to D20).

### 2.2 New node templates

| Template | Kind | Proposal |
|---|---|---|
| `management_strategy` | Type: ordered components, derived identity (`warp-strategy-identity/1`) | Management strategy |
| `quality_of_environmental_material` | Type: quality + material or medium, optional depth and season | Tolerance |
| `site` | **Particular**: geometry, precision, area, ecosystem type, jurisdiction, tenure, care. Emitted as an OWL **individual** under `site:`, never a class (D11) | Implementation |

### 2.3 Records that are not nodes

- **`CriteriaSet`**: one body's versioned definition, described by a fixed set of definitional elements plus verbatim text.
- **Criteria concepts**: `degraded_area`, `effective_restoration`, generated as SKOS concepts, with the enum's `meaning:` pointing at those same IRIs so only one IRI per concept exists (D14).
- **Projects**: the derived grouping record stays a proposition, but the project itself is an OWL **individual** under `proj:`, a process instance of its strategy class (D17).

### 2.4 Base profile additions (shared by several proposals)

- Value classes: `Quantity`, `QuantityRange`, `ScaledValue`, `CurvePoint`, and `Period` (or the existing `temporal_extent` type).
- Claim-level slots shared across groups: `context`, `ecosystem_context`, `place`, `temporal_extent`, `specified_in`.
- `modality` on `Claim`: `observed`, `inferred`, `anticipated`.
- `not_stated` as an evidence type.
- `stated_goal` on `EcoStudyResult`. Aims belong to the evidence layer, never to nodes or claims.
- `place` (D18): the region a claim is about, as an IRI from a registered place scheme. This is what the proposals' examples mean when they write a region into `ecosystem_context`.
- `ScaledValue` gains `concept`: the IRI of the value in its scale's SKOS scheme, beside the verbatim string.
- `vocab/scales.yaml`: every source scale (`dfo-recovery-priority`, `eive-1.0-reaction`, `usda-texture-class` and the rest) as a `skos:ConceptScheme` with ordered concepts, so a scaled value resolves to something.

### 2.5 Scripts and reports

| Script | Kind | Purpose |
|---|---|---|
| `derive_strategies.py` | Derivation | Canonical strategy nodes from component keys |
| `derive_propositions.py` (extended) | Derivation | Per-group identity extras, rule v3 |
| `derive_projects.py` | Derivation | Projects from implementation claims |
| `check_refs.py` | Validation | Every non-inlined reference resolves |
| `check_cost.py` | Validation | Per-predicate cost rules that LinkML cannot express |
| `report_guidance.py` | Report | Unsupported and self-supporting guidance |
| `report_tolerance.py` | Report | Ranges per proposition, non-overlapping ranges |
| `report_cost_completeness.py` | Report | Completeness against Iacona's five standards |
| `transfer_costs.py` | Derivation | Explicit, versioned transfer of costs to a new place or year |
| `report_target2.py` | Report | Target 2 area under chosen definitions |
| `gen_vocab.py` | Generation | `vocab/scales.yaml` and the criteria concepts → SKOS (`project/scales.ttl`, `project/criteria_concepts.ttl`) |
| `clean_owl.py` | Generation | Post-processes `gen-owl` output into an OWL 2 DL ontology (Phase 2.5) |
| `export_rdf.py` | Generation | The reification layer: claims, propositions, evidence, sites, projects → `project/statements.ttl` |
| `project_owl.py` | Generation | The logical layer: propositions that pass the gate → OWL class axioms in `project/axioms.ttl` |
| `check_owl.py` | Validation | OWL lint: entity kinds, datatypes, undeclared prefixes, sentinel values |

The `make` order becomes: templates → vocab → strategies → nodes →
propositions → projects → validate → refs → rdf → owl → reports.

### 2.6 RDF and OWL outputs

Seven groups and three templates only pay off if what comes out is a graph a
reasoner will accept. After 0.4 there are two layers and five files, and
nothing mixes them (decisions D11 to D20, contract in `docs/rdf-owl.md`).

| File | Layer | Holds | Profile |
|---|---|---|---|
| `project/nodes.ttl` | logical | Node classes from templates | OWL 2 EL |
| `project/axioms.ttl` | logical | Class axioms projected from propositions that pass the gate (D15) | OWL 2 EL |
| `project/sites.ttl`, `project/projects.ttl` | logical | Site and project **individuals** (D11, D17) | OWL 2 EL |
| `project/statements.ttl` | reification | Every claim, proposition, evidence line, qualifier, amount, agent and document | RDF, with OWL annotation properties only |
| `project/warp.owl.ttl` | schema | The profile itself, after `clean_owl.py` | OWL 2 DL |
| `src/warp/owl/warp-relations.ttl` | schema | Every minted `warp:` predicate, declared once as an object property | OWL 2 DL |

The two layers answer different questions. The reification layer is the whole
graph, and it is where scope, hedging, modality, negation, ranges, amounts,
order and provenance live: nothing there is asserted as true of the world. The
logical layer holds only what WARP is prepared to let a reasoner use, which is
much less. A claim reaches it only through the gate in D15.

---

## 3. Decisions to make before Phase 1

The prompts use the defaults below. Change a prompt only where its decision
cites one you changed. Section 0 says which of these actually need your answer;
the rest are here so you can see what was decided and why, not so you have to
decide them again.

| # | Decision | Default in prompts | Affects |
|---|---|---|---|
| D1 | Is context-of-place part of identity for **every** group, or only where a proposal adds it (tolerance, cost)? An earlier modelling decision put it in the key generally; the proposals add it per group. | Per group, as the proposals say, and as `place` rather than `ecosystem_context` (D18). If you want it everywhere, add it to causal and interaction in Phase 2. Their proposition IDs then change. | 2, 5, 6 |
| D2 | Proposals write `expert_opinion`; CAMO's evidence enum has `expert_judgment`. | Use CAMO's `expert_judgment` and translate the proposal examples. | 1, 3, 5 |
| D3 | Where does `not_stated` live? | A profile enum that contains every CAMO value plus `not_stated`, plus a TODO to upstream it to CAMO. | 1 |
| D4 | Do proposition IDs change under rule v3? | No, for groups with no extras: the rule version is recorded on each proposition but is not hashed. If the current code hashes it, Claude Code stops and asks. | 2 |
| D5 | DOSDP for strategies, whose part count varies (strategy Q5). | Skip DOSDP; generate the OWL directly from the definitions. | 4 |
| D6 | Step order in OWL (strategy Q6, for Lars). | RDF only. OWL gets `has_part` only, as `rdfs:subClassOf`, never `owl:equivalentClass` (see D16 and Prompt 4). | 4 |
| D7 | Sites as particulars (implementation Q1, for Lars). | Sites are nodes. They are emitted as OWL individuals under their own prefix (D11), and geometry never appears in generated outputs. | 7.1 |
| D8 | Effectiveness verdicts about projects (implementation Q3). | **Superseded by D17.** The verdict's subject is the project individual, not a proposition, so `subject_proposition` is not needed. | 7.3 |
| D9 | Target 2 counting rules (implementation Q5). | Planned work excluded unless a flag is set. Area is reported as lower and upper bounds. **Amended by Q15a:** report three buckets, supported / contested / unsupported, rather than a binary where one disputing claim removes a site. | 7.3 |
| D10 | Release shape. | **Amended by Q15b:** two releases, 0.6.0 after Phase 2.5 and 0.7.0 after Phase 7, one commit per prompt. Not 0.4.0: the repo is already at 0.5.0, so that would be a downgrade. | All |



### 3.1 Decisions about the graph

D11 to D20 settle how WARP becomes RDF and OWL. They are new in this revision
of the guide: the first draft added five groups without saying what any of them
emits, and the four defects 0.3 already has (predicate IRIs typed as classes,
enum slots declared as object properties but carrying literals, node IRIs used
as both class and individual, and polarity kept in a sibling slot) would have
been multiplied by seven. Phase 2.5 implements them; the group phases follow
them.

| # | Decision | Default in prompts | Affects |
|---|---|---|---|
| D11 | What each IRI space denotes. | Four spaces, and nothing crosses: `node:` are OWL **classes** (actions, outcomes, variables, taxa, strategies); `site:` and `proj:` are OWL **individuals** (particulars); `warp:prop/`, `warp:statement/`, `warp:el/` and the rest are RDF individuals in the reification layer and never classes. A `node:` IRI is never used as an individual, and no IRI is ever both. | 2.5, 4, 7 |
| D12 | How a claim points at a node class without punning it. | In the reification layer `subject`, `predicate` and `object` are declared **annotation properties**, so a claim may reference a class IRI legally. The logical layer never uses them. | 2.5 |
| D13 | Where predicate IRIs are declared. | Once, in `src/warp/owl/warp-relations.ttl`, as `owl:ObjectProperty`. RO and CAMO IRIs are reused, never re-declared. `clean_owl.py` strips the `owl:Class` typing `gen-owl` gives them. | 2.5, 3–7 |
| D14 | How enum values appear in RDF. | As IRIs: each permissible value is an `owl:NamedIndividual` typed by the enum class, with no covering axiom. Values that denote absence (`not_stated`, `unknown`, `unclear`, `not_reported`, `not_addressed`) get no `meaning:` and are never exported. | 2.5, 1 |
| D15 | When a claim becomes an OWL axiom. | Only when scope is `universal`, `negated` is false, every grouped claim's modality is `observed`, and a `SynthesisAssessment` supports the proposition. Everything else stays in the reification layer. `prototypical` is defeasible and has no OWL 2 rendering, so it never projects. | 2.5, 3–7 |
| D16 | Where polarity lives. | In the predicate, so a triple reads correctly without its qualifiers: recommendation gets `recommended_to_achieve`, `advised_against_for` and `suggested_for_consideration` under an abstract `suggested_to`; criteria gets `qualifies_as` and `does_not_qualify_as` under an abstract `assessed_against`; cost gets one sub-property per category. Negated claims are never projected or exported as triples. | 2.5, 3, 6, 7.3 |
| D17 | What a project is. | A process individual. `derive_projects.py` mints `proj:<id>`, typed by its canonical strategy class and located at its site; the `ImplementationProposition` stays the derived grouping record and is about that individual (`IAO:0000136`). Criteria claims about a project take `subject: proj:<id>`, so `subject_proposition` is dropped. | 7.2, 7.3 |
| D18 | Units, scales and places. | Units are verified UO CURIEs, QUDT where UO has no term, never bare tokens like `ha` or `protected_area`. Every source scale is a SKOS scheme generated from `vocab/scales.yaml`. A new claim slot `place` carries geography, and replaces `ecosystem_context` in the tolerance and cost identity keys; `ecosystem_context` keeps its CAMO functional-group range. | 1, 5, 6 |
| D19 | Temporal values. | ISO 8601 strings in the data, as the proposals have them. Exporters emit the verbatim string plus normalized `xsd:dateTime` bounds for comparison. No `xsd:date`, `xsd:gYear` or `xsd:duration` literal appears in any generated file: they are not in the OWL 2 datatype map. | 1, 2.5, 7 |
| D20 | Prefixes and placeholders. | Every prefix an example uses is declared in the profile. Placeholder terms move to a `TODO:` prefix of their own, so `TODO:planting` can never be mistaken for an ELMO term. `external_ids` become `{scheme, value}` records rather than invented CURIEs. | 1, 2.5, 7.2 |

---

## 4. Where the proposals disagree, and how the prompts resolve it

These fixes are written into the prompts already.

- **R1. `QuantityValue` vs `Quantity`.** The implementation sketch uses `QuantityValue`; the others use `Quantity`. The prompts use `Quantity` everywhere.
- **R2. `Period` vs `temporal_extent`.** The prompts reuse whatever type `temporal_extent` already has, rather than adding a second period class.
- **R3. Cost rule across objects.** The cost sketch puts a rule on `CostClaim` that tests slots inside `predicate_qualifiers`, which LinkML rules cannot reach. Instead, the prompts put `any_of` (amount, effort or ratio) on `CostQualifiers` and enforce per-predicate rules in `check_cost.py`.
- **R4. Required `scale`.** The cost sketch makes `scale` required, but the relative-cost example has none. The prompts require it only for `incurs_cost`.
- **R5. `adjustment` base year.** The cost table mentions a base year for adjustments; the sketch omits it. The prompts add `adjustment_base_year`.
- **R6. Where `predicate_qualifiers` is declared.** The implementation sketch declares it under `attributes`, while the others use slots and `slot_usage`. The prompts follow the existing pattern in the repo.
- **R7. Criteria subjects.** A criteria claim about a project has no subject node. The prompts make `subject` optional for that class and require exactly one of `subject` or `subject_proposition`. **Superseded by R18:** the project individual is a subject node, so `subject` is simply required.
- **R8. Missing identity fields.** The prompts encode a missing extra (such as `ecosystem_context`) as an explicit null, which still groups with other nulls, and report it. Missing or unclear `scope` keeps the current behaviour: the claim is not grouped.
- **R9. Referring to strategies.** Annotators give strategies local IDs. Strategy derivation computes canonical IDs and rewrites references in the derived output, and it runs before proposition derivation, so claims about two equivalent strategies meet in one proposition.
- **R10. Role and phase.** Strategy `role` and cost `phase` line up but use different values. The prompts record the mapping as enum annotations: `site_preparation` and `establishment` → `initial`, and the rest one to one.
- **R11. Group names and counts.** The proposals say "fourth" and "fifth" group, and use placeholder registry keys (`warp_group`). The prompts use the repo's real `warp_*` annotations, and the docs list seven groups.
- **R12. Subject and object ranges.** All sketches use `CausalNode` (the CAMO annotation record) for subjects and objects. The prompts keep this at the LinkML level, and settle in D11 and D12 what the IRI denotes once it reaches RDF.

The next ten are not disagreements between the proposals. They are places where
all five sketches would produce a graph that is not OWL 2, usually by inheriting
something 0.3 already does. The prompts fix them in Phase 2.5 and after.

- **R13. Predicate IRIs typed as classes.** `gen-owl` emits every predicate enum value as an `owl:Class` subclassing the enum class, so `project/warp.owl.ttl` already contains `RO:0002470 a owl:Class`, contradicting RO, where it is an object property. `examples/kramer1995.ttl` then uses `camo:prevents` as an individual. Eight new predicates would follow, plus `RO:0002303`, which the tolerance group also wants to use as a real relation. **Fixed in the schema, not in a script:** `implements: [owl:ObjectProperty]` on each predicate enum makes `gen-owl` emit the object-property declaration and no covering axiom. Predicates are still declared in `warp-relations.ttl` (D13), which is where their definitions and sub-property structure live. See the appendix.
- **R14. Enum slots declared as object properties but carrying literals.** The schema OWL says `warp:scope a owl:ObjectProperty ; rdfs:range warp:SemanticUnitScopeEnum`; the data writes `warp:scope "assertional"`. A literal in the object position of an object property does not map to OWL 2 DL. 0.4 adds roughly 28 enums. The prompts export permissible-value IRIs (D14), and `implements: [owl:NamedIndividual]` on each value enum makes `gen-owl` declare those IRIs as individuals of the enum class. Also a schema setting, not a script. See the appendix.
- **R15. `owl:unionOf` on named classes.** `gen-owl` writes the covering axiom directly onto the enum class IRI, which does not reverse-map to OWL 2 DL and is outside EL anyway. This is the one genuine LinkML defect of the three, and so the only thing left for `clean_owl.py` to do. The appendix has the ten-line upstream patch and the evidence that it works.
- **R16. Cost object range.** The sketch has `object: {range: uriorcurie}`, which is a cost category in one claim and an action node in the next, and mints `costcat:` IRIs that nothing declares or types. The prompts put `any_of` on the slot range (`CostCategoryEnum` or `CausalNode`), mint no `costcat:` IRIs at all, and move the category into the predicate in RDF (D16).
- **R17. Object kind varies by predicate.** `has_habitat` takes an ENVO habitat while the other three tolerance predicates take a quality-of-environmental-material node; `incurs_cost` and `costs_relative_to` differ the same way. LinkML cannot say this on one slot, so the group's check script enforces it and the exporter emits `RO:0002303` only for `has_habitat`.
- **R18. Claims about propositions.** The implementation sketch sets `ImplementationProposition # = project`, which identifies an information record with a process, and D8 then made a criteria verdict an assertion about that record. D17 mints the project individual instead, so `subject_proposition` and the `exactly_one_of` rule in R7 both go away.
- **R19. `ecosystem_context` holding places.** Every 0.4 example puts a region there (`mediterranean-coastal-israel`, `florida-usa`, `northern-great-plains`, `europe`) while the slot ranges over CAMO's `EcosystemFunctionalGroupEnum`. Two axes in one slot, and it is in three identity keys. The prompts add `place` (D18).
- **R20. Scales and units as bare tokens.** `{value: medium, scale: dfo-recovery-priority}` and `{value: 600, unit: UO:hectare}` are not CURIEs (UO IDs are numeric), and `unit: protected_area` is a count, not a unit. In RDF they resolve as relative IRIs against the base: silent garbage. Site area uses `ha` where cost scale uses `UO:hectare`, so one quantity gets two IRIs and aggregation breaks. The prompts register both vocabularies (D18).
- **R21. Placeholder IRIs under real prefixes.** `project/nodes.ttl` already publishes `ELMO:TODO_planting`, and 0.4 adds `ENVO:TODO_grassland` and many more. In YAML that is an honest marker; in Turtle it is indistinguishable from a real term. The prompts move them to `TODO:` (D20).
- **R22. SEPIO's placeholder namespace.** `subject`, `predicate`, `object`, `hasEvidenceLines` and `targetProposition` still resolve under `https://example.org/sepio-model/`, so nothing in the reification layer can be published as it stands. **Settled by Q13:** WARP mints its own IRIs for the SEPIO slots it uses, by setting `slot_uri` in `slot_usage` and generating with `--no-use-native-uris`, and publishes an `owl:equivalentProperty` mapping file when SEPIO grounds its terms. The upstream PR is still worth filing.

---

## 5. Phase order

```
0  Orientation, CLAUDE.md, test harness
│
1  Shared foundations (value types, shared slots, modality, not_stated,
│  stated_goal, places, scales, units, dates, prefixes)
│
2  Identity engine (per-group extras, rule v3) + reference checker
│
2.5 RDF and OWL contract (relations file, exporters, projection gate, owl-check)
│
├── 3  Recommendation group
├── 4  Management strategy node ──┬── 6  Cost group (6.1 schema, 6.2 reports and transfer)
├── 5  Tolerance group            │
│                                 └── 7  Sites → implementation and projects → criteria and Target 2
│
8  Consolidation: docs, TODOs, 0.4.0 release
│
9  Optional: feedback-model additions, ThreatAssessment, rate-of-interaction template, tolerance importer
```

Phases 3, 4 and 5 are independent after Phase 2.5 and can run in any order.

**Phase 2.5 is not optional and cannot be deferred.** Each group phase declares
its predicates in the relations file and its projection rule as it is built. If
2.5 comes last, seven groups' worth of predicates, enums and examples have to be
revisited, and the existing examples' derived IDs are at risk. The cost of
getting it right is the same whenever it happens; the cost of getting it wrong
scales with the number of groups already built.

---

## 6. Prompts

### Phase 0: orientation

#### Prompt 0.1: read the repo, write CLAUDE.md, set up tests

```text
Read README.md, TODOS.md, docs/node-templates.md, docs/predicate-groups.md,
src/warp/schema/warp.yaml, src/warp/schema/warp_templates.yaml,
templates/node_templates.yaml, scripts/*.py, the Makefile and examples/.
Also skim the five proposals in docs/proposal-*.html. Don't change any schema
or script yet.

1. If this is a git repo, create and switch to a branch named warp-0.4.
2. Run `make all` on the clean checkout. If it fails, stop and tell me why.
3. If there is no test suite, add pytest under tests/ with one smoke test:
   every file in examples/ validates against the profile. Add a `make test`
   target and make `make all` run it.
4. Write CLAUDE.md at the repo root. Include the conventions and the
   Definition of done below, plus a "How the code works" section with facts a
   future session needs:
   - the exact warp_* annotations that register a predicate group
   - how derive_propositions.py builds the identity key and the proposition
     ID hash, and whether the rule version is part of the hash
   - which slots on CausalClaim are top-level slots and which are inline
     attributes
   - the slot that holds the claimant, and the agent ID SynthesisAssessment
     uses for EcoWeaver as claimant
   - the type of temporal_extent and ecosystem_context
   - how expand_nodes.py and gen_dosdp.py turn templates into OWL and DOSDP
   - which generated file each kind of OWL entity comes from today
     (project/nodes.ttl, project/warp.owl.ttl), and the fact that nothing
     emits claims or propositions as RDF yet: examples/kramer1995.ttl is a
     hand-written rendering, not generated
   - whether `robot` is on PATH, and what `robot validate-profile` reports for
     project/nodes.ttl and project/warp.owl.ttl as they stand
5. Reply with a short list of places where the proposals' schema sketches
   conflict with the actual code (slot names, annotations, ranges). List them
   only; don't fix them.
6. Separately, confirm or correct these five observations about the OWL that
   `make all` produces now. Phase 2.5 is written against them.
   - project/warp.owl.ttl declares predicate IRIs as classes
     (`RO:0002470 a owl:Class ; rdfs:subClassOf warp:InteractionPredicateEnum`)
   - it puts `owl:unionOf` directly on named enum class IRIs
   - enum-ranged slots are declared `owl:ObjectProperty` with a class range,
     while the data writes plain string literals for them
   - node IRIs are `owl:Class` in nodes.ttl and are used as individuals (as the
     object of sepio:subject) in the claim layer
   - project/nodes.ttl has no `owl:Ontology` header, and there is no robot
     target in the Makefile, although the README says node classes are
     "checked to be in OWL 2 EL with ROBOT"

Conventions for CLAUDE.md:
- Never edit src/warp/schema/upstream/. Make every change in the profile, by
  is_a and slot_usage.
- Never hand-edit generated files (patterns/, project/, *.derived.yaml and any
  other generated outputs). Regenerate them with make.
- Every derivation rule has a version constant. Every derived record stores
  the rule version that made it. Changing a rule means bumping its version.
- Derived records (propositions, canonical strategies, projects, transferred
  costs) are never written by annotators or in input examples.
- New predicate groups follow docs/predicate-groups.md and are discovered from
  schema annotations. Derivation code is group-agnostic unless a rule cannot
  be expressed as an identity key.
- Examples are illustrative. Mark placeholders with TODO. Never invent DOIs,
  ontology IDs or figures that could pass as real.
- Use only ontology CURIEs you have verified. Otherwise use a placeholder under
  the TODO: prefix (e.g. TODO:planting, never ELMO:TODO_planting) and add it to
  TODOS.md. Nothing under a real ontology's prefix is invented.
- Every prefix an example uses is declared in the profile. A CURIE that cannot
  be expanded is an error, not a warning.
- The graph rules in docs/rdf-owl.md hold for every group: one IRI is one kind
  of thing; predicates are declared once as object properties; polarity is in
  the predicate, never only in a qualifier; nothing becomes an OWL axiom unless
  it passes the projection gate.
- Ask before adding a new dependency to requirements.txt.

Definition of done (every prompt):
- `make all` passes, including tests, reference checks and `make owl-check`
  (from Phase 2.5 on).
- Existing examples still validate. If any derived ID changed, say which and
  why.
- Every IRI the phase introduces has exactly one kind (class, individual,
  object property, annotation property, datatype), and `scripts/check_owl.py`
  is clean (from Phase 2.5 on).
- An entry under "0.4.0 (unreleased)" in the README's Changes section.
- Open questions you did not resolve are added to TODOS.md, citing the
  proposal and its question number.
- A short reply to me: what changed, every decision you made on my behalf, and
  every placeholder you left.
- One commit: "warp 0.4: <phase name>".
```

---

### Phase 1: shared foundations

#### Prompt 1: value types, shared slots, modality, not_stated, stated_goal

```text
Read CLAUDE.md. Then read the "Schema sketch" and "Related changes" sections of
the five proposals in docs/proposal-*.html. This phase adds only what several
proposals share. No new predicate groups yet.

In src/warp/schema/warp.yaml:

1. Value classes:
   - Quantity {value: float, unit: uriorcurie}
   - QuantityRange {min: float, max: float, unit: uriorcurie}. Either end may
     be absent, but not both. When both are present, min <= max (rule or
     Python check).
   - ScaledValue {value: string, scale: uriorcurie, concept: uriorcurie}.
     `value` is the source's own wording, verbatim. `scale` is the IRI of a
     SKOS scheme in vocab/scales.yaml (see step 7), not a bare token:
     scale:dfo-recovery-priority, not dfo-recovery-priority. `concept` is the
     IRI of that value inside the scheme, and is optional only while a scheme
     is still unregistered. Decision D18.
   - CurvePoint {x: float, suitability: float in [0, 1]}
   - A period type. If temporal_extent already has a class with start and end,
     reuse it under that name. Otherwise add Period {start, end}: ISO 8601
     strings that allow a year, year-month or full date; end optional (open
     or ongoing).
   Wherever a proposal sketch says QuantityValue, it means Quantity.

2. Shared claim-level slots. context, ecosystem_context and temporal_extent
   must be usable by any Claim subclass. If they exist only as inline
   attributes on CausalClaim, promote them to top-level slots in the profile
   and have CausalClaim use the slots. CausalClaim's validation behaviour and
   the existing examples must not change.

3. Add a top-level slot `specified_in` (range EcoDocument, multivalued, not
   inlined) for plan documents. It is used by strategies and implementation
   claims later.

4. Add `modality` to Claim: ModalityEnum {observed, inferred, anticipated},
   optional. Its description must say how it differs from hedging
   (causal_language): modality is whether the claim reports, infers or
   forecasts; hedging is how sure the speaker sounds.

5. Evidence types (decisions D2, D3). Do not edit CAMO. Add a profile enum
   WarpEvidenceTypeEnum that contains every value of CAMO's evidence type enum,
   with the same meanings and mappings, plus `not_stated` (the source asserts
   without giving any basis; distinct from expert_judgment and from leaving
   evidence lines empty). Make it the range of EcoEvidenceLine.evidence_type.
   Use CAMO's existing expert_judgment value; do not add expert_opinion.
   Add a test that fails if CAMO's enum has a value the profile enum lacks, so
   re-vendoring cannot silently drop values. Add a TODOS item to propose
   not_stated upstream in CAMO.

6. Add `stated_goal` (string) to EcoStudyResult. Description: the aim as the
   source states it, recorded without judging success; shared by all groups;
   never placed on nodes or claims.

7. Scales as vocabularies (decision D18). Add vocab/scales.yaml: one entry per
   source scale, each with an id, a label, the body it comes from, and its
   values in order. Start with the scales the proposals name:
   dfo-recovery-priority, dfo-timing-of-influence, eive-1.0-reaction,
   usda-texture-class, usda-tolerance-rating and wetland-indicator-status.
   Mark `practitioner-free` as what it is: not a scale, so a practitioner's
   "wet" goes in `value` with no scale and no concept, and the report says so.
   Add scripts/gen_vocab.py, which writes project/scales.ttl: each scale a
   skos:ConceptScheme, each value a skos:Concept with skos:inScheme,
   skos:prefLabel and an explicit ordinal, so "medium" can be compared with
   "high" without hard-coding the order in a script. Wire it into `make`
   before nodes.

8. Units (decision D18). Add a units section to docs/ and a check: every `unit`
   value must be a CURIE under a declared prefix, and UO CURIEs are numeric
   (UO:0000196, not UO:hectare). Verify hectare, person-day and the pH unit
   against a local source; if you cannot, use TODO: placeholders and list
   them. Where a "unit" is really a count of things (the proposals' `scale:
   [{value: 46, unit: protected_area}]`), record it as a count with its own
   entity CURIE, not as a unit. One vocabulary for one quantity: site area and
   cost scale must not use two different IRIs for the hectare.

9. Place (decision D18). Add a top-level slot `place` (uriorcurie,
   multivalued, optional): the region a claim is about. Declare the prefixes it
   may use (ISO 3166-2 for jurisdictions; an ecoregion scheme or a
   warp:place/ concept otherwise) and check them. Do not change
   `ecosystem_context`: it keeps CAMO's functional-group range and its own
   meaning. Add a description to each saying which is which, because every
   example in the proposals confuses them.

10. Temporal values (decision D19). Fix the ranges now, before four groups use
    them. Any slot that holds a date, a year or a period keeps an ISO 8601
    string with a pattern that allows a year, year-month or full date; no slot
    uses LinkML `date` or `datetime` except recordMetadata, which already
    does. Add one helper, used by every later phase, that turns such a string
    into normalized xsd:dateTime lower and upper bounds, and use it for period
    overlap rather than comparing strings. Reason for the comments: xsd:date,
    xsd:gYear and xsd:duration are not in the OWL 2 datatype map, so they must
    not reach a generated file.

11. OWL entity types (decisions D13, D14, and the appendix). Add `implements:`
    where the OWL generator needs to be told what an element is. This is the
    whole of R13 and R14, and it is three lines of YAML per element:
    - `implements: [owl:ObjectProperty]` on CausalPredicateEnum and
      InteractionPredicateEnum, and on every predicate enum a later phase adds
    - `implements: [owl:NamedIndividual]` on every other enum, including the
      ones inherited from CAMO if their emitted form matters
    - `implements: [owl:AnnotationProperty]` on subject, predicate and object
    Check the result: predicate IRIs must come out as `owl:ObjectProperty`
    with no `rdfs:subClassOf` to the enum, and no covering axiom on a
    predicate enum at all. Add a test that fails if a predicate IRI is ever
    emitted as an `owl:Class`.

12. Prefixes and placeholders (decision D20). Declare in the profile every
    prefix the proposals' examples use: org, person, doc, stmt, prop, site,
    proj, comp, crit, concept, scale, place, and TODO for placeholders. Add a
    check that every CURIE in every example file expands under a declared
    prefix, and that nothing invented sits under a real ontology's prefix.
    Rewrite the existing ELMO:TODO_* placeholders in templates and examples as
    TODO:*.

Acceptance: compare examples/*.derived.yaml before and after. Proposition IDs
must be identical. The generated JSON Schema and OWL include the new classes.
project/scales.ttl loads and every scale has at least two ordered values.
Finish per the Definition of done.
```

---

### Phase 2: identity engine and reference checker

#### Prompt 2: per-group identity extras, rule v3, check_refs.py

```text
Read CLAUDE.md, docs/predicate-groups.md and scripts/derive_propositions.py.
Start in plan mode and show me the plan before changing files.

Goal: groups added later must be able to extend the proposition identity key
without group-specific code.

1. Registry annotations. Add two optional annotations, named in the style of
   the existing warp_* annotations:
   - identity extras: an ordered list of slot paths added to the key, e.g.
     predicate_qualifiers.guidance or place. Dotted paths reach
     into inlined objects.
   - identity rule name: overrides the shared rule ID for one group (the
     criteria group will use warp-criteria-identity/1).
   Document both in docs/predicate-groups.md, with an example.

2. Rule warp-prop-identity/3: the v2 fields plus the group's declared extras,
   in declaration order.
   - Missing extras are encoded as an explicit null, so the claim still groups
     with other claims whose value is also missing. Count these in the
     derivation report under "grouped with missing key fields". Missing or
     unclear scope keeps today's behaviour: not grouped, reported. The null
     marker lives only inside the key string: no exporter ever emits it as a
     value, and no slot is ever written with it (decision D14).
   - Structured values (objects, lists) are canonicalized deterministically
     (JSON with sorted keys; sorted lists where order carries no meaning)
     before hashing.
   - Decision D4: groups that declare no extras must keep their existing
     proposition IDs. If the current code puts the rule version into the hash,
     stop and explain the options before changing it.
   - Every proposition records identity_rule_version.
   - Decision D1 default: add no extras to causal or interaction.

3. scripts/check_refs.py. Using linkml_runtime SchemaView, find every slot
   whose range is a class and that is not inlined. Check that every reference
   in a claim set (nodes, propositions, documents and anything added later)
   resolves within the input file or its derived file. Report unresolved IDs
   with the slot and record they come from. Because it is schema-driven, new
   groups get checked automatically. Wire it into `make validate`.

4. Tests:
   - key building with no extras, with extras, with missing extras, and with
     structured extras in a different key order (must hash the same)
   - unchanged IDs for the existing examples
   - check_refs catching a dangling reference

Finish per the Definition of done.
```

---

### Phase 2.5: the RDF and OWL contract

#### Prompt 2.5: relations file, exporters, projection gate, owl-check

```text
Read CLAUDE.md, scripts/expand_nodes.py, templates/node_templates.yaml,
project/nodes.ttl, project/warp.owl.ttl and examples/kramer1995.ttl. That last
file is the hand-written RDF rendering of one claim, and it is the
specification this phase turns into code. Start in plan mode and show me the
plan before changing files.

Decisions D11 to D20. The goal of this phase is that everything WARP generates
is either valid OWL 2 DL, or valid OWL 2 EL, or plainly labelled as the
reification layer, and that no IRI is ever two kinds of thing.

1. docs/rdf-owl.md. A draft already exists in the repo: read it first, because
   the group phases are checked against it, and correct it where this phase's
   code ends up differing rather than writing a second account. Its "state of
   play" table and its per-group register are the two parts that go stale
   fastest, so update them as you go. It states:
   - the two layers (reification and logical) and the five output files, as in
     section 2.6 of the dev guide
   - the four IRI spaces and the rule that one IRI is one kind of thing (D11)
   - that a claim references a node class through annotation properties, so the
     class is never punned as an individual (D12)
   - that every predicate is declared once, as an object property, in
     warp-relations.ttl, and that RO and CAMO IRIs are reused, never
     re-declared (D13)
   - how enum values appear in RDF, and that sentinel values do not (D14)
   - the projection gate, in full, with the reason for each condition (D15)
   - that polarity belongs in the predicate (D16)
   - what a reader may and may not infer from each file
   Add a section "adding a group" with the five questions a new group must
   answer: which predicates it mints, what kind of thing each end of each
   predicate is, which qualifiers carry polarity, what it exports, and what (if
   anything) it projects.

2. src/warp/owl/warp-relations.ttl, hand-maintained, never generated. It is an
   owl:Ontology with its own IRI and version IRI, and it declares:
   - every predicate WARP mints, as owl:ObjectProperty, with rdfs:label, an
     IAO:0000115 definition taken from the proposal, and rdfs:isDefinedBy
   - the sub-property structure the groups need (D16), with the abstract
     parents marked so nothing asserts them directly
   - the annotation properties the reification layer uses for subject,
     predicate and object (D12)
   - nothing about domains or ranges unless the range is a single kind of
     thing: a domain axiom that is wrong for one predicate in a group is worse
     than none. Where a range varies by predicate, say so in a comment and
     check it in Python (R17).
   For 0.3 that is the causal and interaction predicates only; each later phase
   adds its own and nothing else touches the file.

3. scripts/clean_owl.py, run on gen-owl's output, writing project/warp.owl.ttl.
   Read the appendix at the end of this guide first: most of what this script
   was going to do turns out to be schema settings, done in Phase 1, so the
   script is small.
   - move each enum's covering axiom off the named class: delete
     `<enum> owl:unionOf (…)` or `<enum> owl:oneOf (…)` and re-attach it as
     `<enum> owl:equivalentClass [ a owl:Class ; owl:oneOf (…) ]` (R15). This
     is the one real LinkML defect; the appendix has the upstream patch, and
     if that lands this script can go.
   - drop permissible values that denote absence, listed in one place in the
     script (D14)
   - leave everything else alone, and report every change it makes
   If anything else still needs removing, the schema is missing an
   `implements:` somewhere: fix it there rather than here.
   Wire it into `make gen`, after gen-owl.

4. scripts/export_rdf.py: the reification layer, writing project/statements.ttl
   from one or more statement sets and their derived files.
   - Every claim, proposition, evidence line, study result, agent, document and
     criteria set becomes a named individual under its own prefix. Nothing that
     a later record may need to cite is a blank node: qualifier bundles,
     monetary amounts, quantities, ranges and strategy components all get IRIs
     (D11). This is what lets a transferred cost cite the amount it came from.
   - Node references use the annotation properties from step 2 (D12).
   - Enum values export as IRIs (D14). Temporal values export as the verbatim
     ISO string plus normalized xsd:dateTime bounds, and no xsd:date,
     xsd:gYear or xsd:duration literal is written anywhere (D19).
   - The SEPIO namespace comes from one module-level constant with a comment
     pointing at the upstream TODO, so re-grounding it is a one-line change
     (R22).
   - Negated claims export their own reified record and no relation triple
     (D16).

5. scripts/project_owl.py: the logical layer, writing project/axioms.ttl.
   - The gate, and nothing else gets through: scope universal, negated false,
     every grouped claim's modality observed, and at least one
     SynthesisAssessment with direction supports. Each group registers a
     projection function; a group with none projects nothing, which is the
     default.
   - For 0.3 the only projection is causal and interaction: a proposition that
     passes the gate becomes
     `<subject node> rdfs:subClassOf [ owl:onProperty <predicate> ;
     owl:someValuesFrom <object node> ]`. Existential subsumption, never
     owl:equivalentClass, and never a plain triple between two class IRIs.
   - Every axiom carries an axiom annotation naming the proposition it came
     from, so a reader can get back to the claims and the assessment.
   - The output is an owl:Ontology with its own IRI and imports nodes.ttl.
   - Print how many propositions were considered, how many passed, and the
     reason each group's rejections failed. On the existing examples the answer
     will be "none passed" (bloodroot and kramer1995 are assertional and
     prototypical), and that is the correct answer: say so rather than
     loosening the gate.

6. scripts/check_owl.py, wired into `make validate` as errors. Schema-driven
   where it can be, over every generated .ttl:
   - no IRI is used as more than one kind of entity, across all generated files
     merged (this is the check that would have caught R13 and the node punning)
   - no xsd:date, xsd:gYear or xsd:duration literal (D19)
   - every CURIE expands under a declared prefix, and nothing invented sits
     under a real ontology's prefix (D20)
   - no sentinel value was exported (D14)
   - every predicate used in a relation triple is declared in
     warp-relations.ttl or comes from an upstream ontology (D13)

7. `make owl-check`, in `make all`:
   - robot merge of nodes.ttl, axioms.ttl, sites.ttl and projects.ttl, then
     `robot validate-profile --profile EL`
   - robot merge of warp.owl.ttl and warp-relations.ttl, then
     `robot validate-profile --profile DL`
   - if robot is not on PATH, print a clear warning and exit 0, so the build
     works without it; say in the README that releases are checked with it
   - add an owl:Ontology header to nodes.ttl while you are there: it has none,
     and robot needs one

8. Tests: a fixture claim set through export_rdf and project_owl; the kind
   check catching an IRI used as class and individual; the datatype check
   catching an xsd:date literal; the gate rejecting an assertional, a negated,
   an anticipated and an unassessed proposition, and accepting one that passes;
   clean_owl removing the three shapes in step 3 and nothing else.

Acceptance: `make all` passes; proposition IDs are unchanged; project/axioms.ttl
exists and is empty of axioms, with the report explaining why. Finish per the
Definition of done.
```

---

### Phase 3: recommendation group

#### Prompt 3: suggested_to

```text
Read CLAUDE.md, docs/predicate-groups.md, the interaction group in warp.yaml
(the model to follow), and docs/proposal-recommendation-group.html in full.
Implement the recommendation group.

Schema:
- RecommendationClaim (is_a Claim, registered as a group with the real warp_*
  annotations), RecommendationQualifiers and RecommendationProposition (is_a
  EcoProposition), following the proposal's sketch.
- Enums: RecommendationPredicateEnum {suggested_to: meaning warp:suggested_to},
  GuidanceEnum {do, avoid, consider}, DeonticForceEnum {required, recommended,
  suggested, optional}, ContributionEnum {direct, precursor}.
- Mint warp:suggested_to with the proposal's definition. The subject is the
  action as the source names it, never the recommender; the advice is in
  `guidance`; the predicate says nothing about strength.
- Qualifiers: guidance (required), deontic_force, priority and
  timing_of_influence (ScaledValue), contribution.
- Claim-level slot justified_by: range EcoProposition, multivalued, not
  inlined.
- Identity extra: predicate_qualifiers.guidance.
- ClaimSet collections recommendation_claims and recommendation_propositions.
- Subject may be an action node or (after Phase 4) a strategy node; the object
  is an outcome node. Both use CausalNode, as in the sketch.

RDF and OWL (docs/rdf-owl.md, decisions D13, D15, D16):
- In warp-relations.ttl declare warp:suggested_to as the abstract parent, and
  three sub-properties under it: warp:recommended_to_achieve,
  warp:advised_against_for and warp:suggested_for_consideration. Annotate each
  with the GuidanceEnum value it corresponds to. warp:suggested_to is never
  asserted of anything.
- Why: `guidance` is in the identity key, so "do prescribed burning" and
  "avoid prescribed burning" are two propositions. With one predicate they are
  also two identical triples, and the distinction the whole group exists to
  keep is lost the moment anyone reads the relation layer without the
  qualifiers. The qualifier stays: it is what annotators fill in, and the
  exporter picks the sub-property from it.
- export_rdf.py emits the sub-property for each claim and proposition.
- project_owl.py projects nothing from this group, whatever the scope.
  Guidance is deontic: "you should do X" has no OWL 2 rendering, and a graph
  that cannot tell advice from description is worse than one that holds only
  description. Say this in docs/rdf-owl.md under the group's entry.

Example: examples/recommendation_examples.yaml, plus a derived file through
make.
- Mountain Sucker approaches 11 (avoid stocking predacious sportfish) and 9
  (do water conservation), each with the causal claim it cites. The approach 11
  causal claim is a prediction: modality anticipated, causal_language hedged,
  evidence line typed expert_judgment (decision D2).
- One causal prediction with evidence_type not_stated.
- Spring Salamander road salt as an open-question proposition, not a
  prediction.
- The prescribed burning pair from the proposal: a "do" and an "avoid" from
  two claimants on the same action and outcome, citing one causal
  proposition. They must derive two recommendation propositions.
- Two claimants giving the same guidance, which must derive one proposition
  with two claims.
Node fillings and IDs are placeholders: mark them TODO.

Report: scripts/report_guidance.py writes project/reports/guidance.md and a
CSV:
(a) guidance with empty justified_by;
(b) self-supporting guidance: every justified_by proposition is supported only
    by claims from the same claimant whose evidence lines are all not_stated
    or expert_judgment;
(c) if any SynthesisAssessment exists for a cited proposition, its strength,
    so weakly supported guidance can be sorted.
These are findings, not validation errors.

Docs: a short section in docs/predicate-groups.md with the annotator's test
("telling someone what to do, or describing what happens?") and the rule that
predictions are recorded as causal claims and never derived from guidance
automatically.

Not in this phase (add to TODOS.md with the proposal's question numbers):
research actions with an open-question object (Q3), structured conditions on
guidance (Q4), claimant for government documents (Q1), a shared priority
ordinal (Q2), scope of forward-looking guidance (Q5), CMP results chains (Q6),
and an OBO or IAO search for a closer relation than warp:suggested_to.

Finish per the Definition of done.
```

---

### Phase 4: management strategy node

#### Prompt 4: management_strategy template and strategy identity

```text
Read CLAUDE.md, docs/node-templates.md, warp_templates.yaml,
templates/node_templates.yaml, scripts/expand_nodes.py, scripts/gen_dosdp.py
and docs/proposal-management-strategy.html in full. Start in plan mode.

Schema and template:
- Add a management_strategy template and StrategyDefinition (is_a
  NodeDefinition) with specified_in, components, identity_key and
  identity_rule_version, as in the sketch. Match field names to the existing
  template schema.
- StrategyComponent: action (node reference, required; may be another
  strategy), step (integer >= 1, required; parallel parts share a step), lag
  (ISO 8601 duration, pattern ^P), repeat (Recurrence: every, times, until as
  text), role (StrategyRoleEnum), optional (boolean).
- At least two components.
- No objective field. Add a schema comment explaining why: what counts as
  restoration success is contested, so aims stay on statements and in
  stated_goal.
- StrategyRoleEnum values carry an annotation mapping each role to a cost
  phase: site_preparation → initial, establishment → initial,
  follow_up → follow_up, maintenance → maintenance,
  monitoring → monitoring.

Derivation: scripts/derive_strategies.py, rule warp-strategy-identity/1.
- Flatten nested strategies one level. A nested strategy at outer step k with
  inner steps 1..m becomes its components at steps k..k+m-1, and later outer
  steps shift by m-1. Error on nesting deeper than one level or on cycles.
- Key: the sorted list of (step, action node ID) for non-optional components
  after flattening. Lags, repeats, roles, labels and optional parts are not in
  the key.
- Annotators give strategies local IDs. The script records identity_key and a
  canonical ID (hash of the key) on each definition, groups definitions with
  the same key, and in the derived output rewrites every reference to a merged
  strategy so claims point at the canonical ID.
- In the Makefile, strategy derivation runs before proposition derivation, so
  two sources describing the same strategy meet in one proposition.

OWL (decisions D5, D6, D11, D13):
- In expand_nodes.py, emit each canonical strategy as a **subclass**, not an
  equivalent class: `node:<strategy> rdfs:subClassOf <planned process>` and one
  `rdfs:subClassOf has_part some C` per required component class, using the BFO
  occurrent part relation. Verify the CURIEs for "planned process" and for the
  occurrent has-part relation from a local source. If you cannot verify them,
  use TODO: placeholders and list them.
- Why not owl:equivalentClass, which is what the proposal says. The identity
  key is the sorted list of (step, action) pairs, so order is part of identity:
  earthworks-then-seeding and seeding-then-earthworks are two strategy nodes.
  Their part axioms are identical, because order does not render. Asserted as
  equivalence, those axioms tell a reasoner the two nodes are the same class,
  which contradicts the rule that just held them apart. Asserted as
  subsumption, they say only what is true: this strategy has these parts.
  Containment queries still work, and are the only thing equivalence was wanted
  for: the query class `has_part some hand_seeding` has every strategy
  containing hand seeding among its subclasses.
- Declare the part relation once in warp-relations.ttl, as transitive (BFO's
  occurrent part relation is), and use it only inside someValuesFrom, never in
  a cardinality restriction, so the output stays in EL. Transitivity is also
  what makes the flattening in the derivation agree with the OWL: a nested
  strategy's parts are parts of the outer strategy either way.
- No DOSDP pattern for this template. Add a note to docs/node-templates.md
  explaining why, and note that this is the first template whose OWL is
  generated outside the template machinery: a class expression with a variable
  number of parts cannot be a template with a fixed var list
  (docs/node-templates.md already says list variables are not supported).
- Order, lag, repeat and role stay in the reification layer, and
  export_rdf.py gives each component its own IRI under comp: so the order is
  addressable and queryable rather than buried in a blank node. Optional parts
  are left out of the class expression and kept in RDF.
- Canonical IDs are content hashes, so a component change mints a new class
  IRI. When derivation supersedes an ID, write owl:deprecated true and
  IAO:0100001 (term replaced by) on the old IRI in the generated output, and
  say in docs/node-templates.md that strategy class IRIs are stable only while
  their parts are.
- `make owl-check` must pass: the merged node and axiom files stay in OWL 2 EL.

Example: examples/strategy_examples.yaml with:
- earthworks → hand seeding (lag P2W) → mowing (yearly, 3 times), from the
  proposal
- fill removal and plug planting at step 1 plus an optional spot spray
- a "standard site preparation" strategy nested in another strategy
- a second source describing the first strategy flat, with a different label
  and local ID, which must merge with it
- a causal claim with a strategy as subject, showing that claims about the two
  merged definitions derive one proposition
ELMO terms for component actions are `TODO:*` placeholders (decision D20).

Tests: flattening, optional parts, merging, renumbering, cycle detection,
deep-nesting error.

Not in this phase (add to TODOS.md): conditional steps and alternatives (Q3),
extraction and Loom confirmation of strategy boundaries (Q4), CMP and Miradi
import (Q7), and asking Lars about order in OWL (Q6).

Finish per the Definition of done.
```

---

### Phase 5: tolerance group

#### Prompt 5: tolerates, prefers, intolerant_of, has habitat

```text
Read CLAUDE.md, docs/predicate-groups.md, docs/node-templates.md and
docs/proposal-tolerance-group.html in full.

Node template:
- Add quality_of_environmental_material: a quality (PATO) of an environmental
  material or medium (ENVO), with an optional depth interval (QuantityRange)
  and optional season. It must also cover water and climate variables (water
  depth, velocity, temperature), not only soil (proposal Q5).
- Check that existing templates can express the subject: a taxon, population
  or life stage, e.g. "seedlings of Bouteloua gracilis". If not, add the
  smallest template that can.

Schema:
- ToleranceClaim, ToleranceQualifiers and ToleranceProposition, as in the
  sketch, registered with the real warp_* annotations.
- TolerancePredicateEnum: tolerates, prefers and intolerant_of (minted in
  warp: with the proposal's definitions), and has_habitat (RO:0002303; verify
  the ID before using it). For has_habitat the object is an ENVO habitat or
  environment node.
- Qualifiers: range (QuantityRange), optimum (Quantity), class_value
  (ScaledValue), response (ToleranceResponseEnum: occurrence, germination,
  establishment, growth, survival, reproduction), and response_curve (list of
  CurvePoint).
- Checks: response_curve x values strictly increasing; suitability between 0
  and 1. Also scripts/check_tolerance.py (wired into `make validate`): the
  object of has_habitat must be a node whose definition uses an ENVO habitat
  or environment term, and the object of the other three must be a
  quality_of_environmental_material node. One slot cannot say this in LinkML,
  and no OWL axiom can carry it either, so it is a script (R17).
- Claim-level slot explained_by: range EcoProposition, multivalued, not
  inlined.
- Identity extra: place, not ecosystem_context (decision D18). The proposal's
  examples write europe and florida-usa into ecosystem_context, which ranges
  over CAMO's functional groups; a regional indicator rating is about a place.
  range, optimum and class_value are not in the key.
- ClaimSet collections tolerance_claims and tolerance_propositions.

RDF and OWL (decisions D13, D15):
- In warp-relations.ttl declare warp:tolerates, warp:prefers and
  warp:intolerant_of as object properties with the proposal's definitions.
  RO:0002303 is reused and never re-declared: it is already an object property
  in RO, and declaring it again as anything else is what breaks the merge.
  Comment that the object kind varies by predicate, and point at
  check_tolerance.py.
- export_rdf.py emits the relation for every claim, with range, optimum,
  class_value and response_curve on the claim's own qualifier individual.
- project_owl.py projects only has_habitat, and only through the gate:
  `node:<taxon> rdfs:subClassOf [ owl:onProperty RO:0002303 ;
  owl:someValuesFrom <ENVO habitat> ]`. A prototypical tolerance does not
  project: "typically grows at pH 5.5 to 8" allows exceptions, and OWL 2 has
  no way to say "typically" — a subclass axiom would make it exceptionless.
  Ranges, optima, class values and curves never enter OWL at all; they are
  numbers about populations, not class axioms.
- A tolerance claim with a USDA or EIVE scale must carry scale and concept
  IRIs from project/scales.ttl (D18), not bare tokens.

Example: examples/tolerance_examples.yaml with placeholder values, as in the
proposal:
- a USDA-style pH range (tolerates, response growth, evidence not_stated)
- an EIVE-style prefers with class_value and a range on the EIVE scale
- the practitioner's prairie cordgrass pair (prefers wet; intolerant_of sand),
  contingent scope
- two sources giving different pH ranges for the same taxon, which must derive
  one proposition
- two regional wetland-indicator-style ratings with different `place`, which
  must derive two propositions
- one HSI-style claim with response_curve. Put the combination rule (e.g.
  geometric mean) on an EcoStudyResult as model metadata, not as a statement.
- one tolerance claim with explained_by pointing at a causal proposition
  (saturated soils → root anoxia)

Report: scripts/report_tolerance.py writes project/reports/tolerance.md: for
each proposition, ranges by claimant and response. Flag non-overlapping ranges
when units match. Never convert units silently; flag unit mismatches instead.
Do not aggregate ranges into one envelope: that rule is open (Q3).

Docs: the annotator's test ("under what conditions it lives, or what changes
what?"), and the rule that tolerates and intolerant_of are recorded as stated
and never derived from each other.

Not in this phase (TODOS.md): the group's name (Q1), range aggregation (Q3),
provenance of bulk imports (Q4), and default scope for database records (Q6).
On Q2 (tolerance as a BFO disposition, for Lars): the question is now narrower
than it was. A disposition rendering would need the range as a datatype facet
on a quality, which leaves OWL 2 EL and gains nothing a query over the
reification layer cannot do. Record it that way in TODOS.md so the discussion
with Lars starts from what the two layers already give.

Finish per the Definition of done.
```

---

### Phase 6: cost group

#### Prompt 6.1: cost schema and examples

```text
Read CLAUDE.md, docs/predicate-groups.md and docs/proposal-cost-group.html in
full. Phase 4 (strategies) must already be done. Start in plan mode.

Schema:
- CostClaim, CostQualifiers, CostProposition, MonetaryAmount and CostRatio,
  plus the enums from the sketch (CostPredicateEnum, CostCategoryEnum,
  CostBehaviourEnum, CostPhaseEnum, ReportingLevelEnum, CostBasisEnum,
  CostAdjustmentEnum). Register the group with the real warp_* annotations.
- Mint warp:incurs_cost and warp:costs_relative_to with the proposal's
  definitions.
- Subject: an action or strategy node. Object: a cost category for
  incurs_cost, or an action or strategy node for costs_relative_to. Declare it
  as `any_of` the two ranges (CostCategoryEnum, CausalNode) and enforce which
  per predicate in check_cost.py (R16, R17). Do **not** give cost categories
  CURIEs and do not use a bare `uriorcurie` range: the sketch's `costcat:total`
  is an IRI nothing declares and nothing types, and one slot that is a category
  in one claim and a node in the next has no coherent range in any layer. The
  category reaches RDF through the predicate instead (see RDF and OWL below).
- MonetaryAmount: value; currency (ISO 4217, ^[A-Z]{3}$, required); price_year
  (required); adjustment; adjustment_rate; adjustment_base_year (missing from
  the sketch; the proposal's table asks for it); conversion_rate.
- CostQualifiers: amount, effort (list of Quantity), volunteer_effort, ratio,
  includes_categories, cost_behaviour, scale (list of Quantity), intensity,
  phase (required), reporting_level, cost_basis, and covers_roles
  (StrategyRoleEnum, multivalued, optional: lets a phase-level cost name the
  strategy components it covers).
- Claim-level slots: outcome_reported (Claim refs), starting_conditions
  (text), cost_bearer, transferred_from (CostClaim ref), transfer_rule
  (string). Reuse context, place, ecosystem_context, temporal_extent and care.
- stated_goal stays on EcoStudyResult (Phase 1). Do not add it to CostClaim.

Validation, fixing the sketch (R3, R4): LinkML rules cannot test slots inside
predicate_qualifiers from CostClaim.
- On CostQualifiers: any_of amount, effort or ratio.
- scripts/check_cost.py, wired into `make validate` as errors:
  - incurs_cost needs amount or effort, plus scale and phase
  - incurs_cost with object total needs includes_categories (unknown is
    allowed)
  - costs_relative_to needs ratio and a node as object; scale is not required
  - amount needs currency and price_year
  - transferred_from requires transfer_rule

Identity extras: place, predicate_qualifiers.phase,
predicate_qualifiers.reporting_level. Amount, scale, currency and year are not
in the key. `place` rather than ecosystem_context (decision D18): the rule that
matters is "costs from different regions never merge silently", and
mediterranean-coastal-israel is a place, not a functional group.

ClaimSet collections cost_claims and cost_propositions.

RDF and OWL (decisions D13, D15, D16):
- In warp-relations.ttl declare warp:incurs_cost as an abstract parent with one
  sub-property per category: warp:incurs_total_cost, warp:incurs_labour_cost,
  warp:incurs_capital_equipment_cost, warp:incurs_consumables_cost,
  warp:incurs_overhead_cost. Annotate each with its CostCategoryEnum value.
  warp:incurs_cost itself is never asserted. Declare warp:costs_relative_to
  separately, between two node classes.
- Why: "this action incurs_cost total" is not a relation between an action and
  a category. A cost is three things at once (an action, a category and an
  amount), and the only part of that which is a relation is action-to-amount.
  Putting the category in the predicate leaves a triple that reads correctly,
  and leaves the amount as the object, where it belongs.
- export_rdf.py emits `<action> warp:incurs_<category>_cost <amount IRI>`,
  with the amount as a named individual carrying value (xsd:decimal), currency,
  price_year, adjustment and the rest. Named, not a blank node, because
  transfer_costs.py has to cite it from a derived claim (D11).
- There is no `unknown` sub-property. A total whose categories are unknown is
  warp:incurs_total_cost with includes_categories left as the annotated
  qualifier; `unknown` is a sentinel and is never exported as an IRI (D14).
- project_owl.py projects nothing from this group. A cost is a fact about one
  episode of work in one place and year; there is no universal-scope cost
  claim, and if one appeared it would still not be a class axiom.

Example: examples/cost_examples.yaml:
- the INPA golden wreath wattle costing from the proposal, with outcome_reported
  pointing at two causal claims from the same source (natives regenerate;
  seedlings persist), and stated_goal on its EcoStudyResult
- the Florida program budget, with amount and price year as TODO
- the practitioner's drill seeding vs plugs ratio
- a whole-project cost on the Phase 4 earthworks-seed-mow strategy, plus a
  phase-level cost with covers_roles
- two intervention-level initial costings in the same region, which must derive
  one proposition, and one maintenance costing that must not join it
Figures from Iacona et al.'s worked examples may be used as in the proposal.
Mark everything else TODO. Every example uses `place` with an IRI from a
declared scheme, unit CURIEs that check out, and no costcat: IRIs; the
proposal's `{value: 46, unit: protected_area}` becomes a count, not a unit
(decision D18).

Not in this phase (TODOS.md): opportunity and transaction costs (Q1),
confidentiality through care access levels (Q2: note that care already exists
on Claim), comparison with the Iacona workbook (Q3), payments as costs (Q5),
Cook et al. and Miradi alignment (Q6), and a valuation group (separate
proposal).

Finish per the Definition of done.
```

#### Prompt 6.2: completeness report and explicit transfer

```text
Read CLAUDE.md and the sections "The five standards", "Qualifiers, by
standard" and "Transfer is explicit" in docs/proposal-cost-group.html.

1. scripts/report_cost_completeness.py writes project/reports/cost_completeness.md
   and a CSV. For each cost claim, check Iacona's five standards plus reporting
   level against the slots in the proposal's table: which required and
   recommended fields are filled, which are missing, and a simple completeness
   score. Also flag includes_categories [unknown], and cost_basis payment_rate
   (a payment is not a cost; check cost_bearer). Look up stated_goal through
   reportedIn and its EcoStudyResult. These are findings, not errors.

2. scripts/transfer_costs.py with rule config
   config/cost_transfer/warp-cost-transfer-1.yaml. A rule declares: target
   region (`place`, decision D18), target price year, target currency, a price
   index table per currency, exchange rates, a regional labour rate table for
   re-pricing effort in person-days, and per cost category whether it is
   re-priced, indexed or unchanged. A selection file lists the source claims to
   transfer.
   - Output: new derived CostClaims in a generated file. The claimant is
     EcoWeaver (the same agent ID SynthesisAssessment uses), with
     transferred_from, transfer_rule, the new `place` and a recomputed
     amount. When effort in physical units is present, re-price labour from it
     instead of scaling a dollar total. Record which steps were applied.
     In RDF the derived claim's amount individual cites the source amount
     individual it was computed from, which is why amounts are named and not
     blank nodes (decision D11).
   - Never modify source claims. Refuse, and report, any claim without
     currency or price_year.
   - Ship the config with obviously fake placeholder index values, marked as
     such, and test it with tiny tables. Don't fetch data from the network.
   - Changing the rule version regenerates the derived claims.

3. Tests: a CPI-only transfer, a currency conversion, labour re-pricing from
   effort, and refusal on missing price_year.

Not in this phase (TODOS.md, Q4): which price indices, exchange rates and
regional wage series to use (e.g. Statistics Canada series).

Finish per the Definition of done.
```

---

### Phase 7: sites, implementation and definitions

#### Prompt 7.1: site template

```text
Read CLAUDE.md, docs/node-templates.md and the "Site" section of
docs/proposal-implementation-group.html.

- Add a site template and SiteDefinition (is_a NodeDefinition) with label,
  geometry (GeoJSON or WKT as a string, or a reference), geometry_precision
  (required: exact, generalized, centroid, withheld), area (Quantity),
  area_source (reported, computed), ecosystem_type (ENVO CURIEs, multivalued),
  jurisdiction (ISO 3166-2 code such as CA-SK, or text for Indigenous
  territories), tenure (TenureEnum: public, private, indigenous, mixed,
  unknown) and care (CareMetadata).
- Checks: withheld precision means no geometry. Exact geometry with restricted
  care access is a warning. GeoJSON must parse as JSON. Don't add a geometry
  library without asking.
- Sites are particulars (decisions D7, D11). expand_nodes.py must not emit them
  as classes in nodes.ttl. Emit them as OWL named individuals in
  project/sites.ttl, with id, label, ecosystem type and jurisdiction only.
  Geometry never goes into any generated output.
- Sites get their own IRI prefix, `site:`, not `node:` (decision D11). The
  prefix is what keeps the two kinds apart: `node:` IRIs are classes
  everywhere, `site:` IRIs are individuals everywhere, and check_owl.py can
  then catch a mistake instead of leaving one IRI meaning two things. The
  LinkML range stays CausalNode (R12); only the IRI space differs.
- ecosystem_type is emitted as `rdf:type`, not as a slot: a site is an
  instance of an ENVO environmental system. Emitting it as an object property
  pointing at an ENVO class would put a class in an individual's place.
- jurisdiction is emitted as an IRI where the code has one (ISO 3166-2 for
  CA-SK) and as a literal where it does not, as Indigenous territories often
  will not. Say which in docs/node-templates.md.
- Add a note to docs/node-templates.md: sites are the first node type that is
  a particular, and why they are nodes anyway.
- Example: site:0412 from the proposal (generalized geometry, 64 ha,
  private tenure, restricted care) in examples/implementation_examples.yaml.
  Use a TODO: placeholder for the ENVO term unless you verify one.

Not in this phase (TODOS.md): ask Lars about particulars in the node layer
(Q1). Note for that conversation that D11 answers the mechanical half of it —
particulars are individuals under their own prefix and never classes — and
leaves him the modelling half, which is whether they belong in the node layer
at all.

Finish per the Definition of done.
```

#### Prompt 7.2: implementation group and derived projects

```text
Read CLAUDE.md and the "Implementation group" section of
docs/proposal-implementation-group.html. Phases 4 and 7.1 must be done.
Start in plan mode.

Schema:
- ImplementationClaim, ImplementationQualifiers and ImplementationProposition
  (the derived project), registered as a group. Follow the repo's pattern for
  predicate_qualifiers rather than the sketch's `attributes` (R6).
- Mint warp:carried_out_at. Subject: a strategy or action node. Object: a node
  whose definition uses the site template (check this in Python if LinkML
  can't). Scope must be assertional.
- Qualifiers: period (required; open end allowed), status (required:
  planned, in_progress, completed, maintained, abandoned), reported_on (an ISO
  date string, decision D19), area_treated (Quantity), implemented_by,
  funded_by, specified_in, external_ids.
- external_ids becomes a list of ExternalId {scheme, value} rather than CURIEs
  (decision D20). `agreement:0412` is not an IRI anyone can resolve, and the
  matching rule needs the scheme separately anyway: the report on "two
  different external IDs from the same namespace" cannot be written without
  it.
- ClaimSet collections implementation_claims and implementation_propositions.

Derivation: scripts/derive_projects.py, rule warp-impl-identity/1. Run it
after strategy derivation, using canonical strategy IDs.
- Link two claims when they share any external ID (same scheme and value), or
  when they have the same canonical strategy, the same site ID and overlapping
  periods (an open end means ongoing). Use the Phase 1 helper for the overlap
  test, over normalized bounds, not string comparison: the proposal's periods
  are `2024-05` and `2023`, which no string ordering handles (decision D19).
  Cluster with union-find.
- Report clusters that contain two different external IDs from the same
  namespace; these are candidate bad merges for review.
- Choose a project ID scheme that stays stable when a new claim joins an
  existing project. Explain it in docs/predicate-groups.md and test it. If no
  scheme is fully stable, record superseded IDs in a `replaces` slot.
- Each project records its member claims and aggregates without resolving
  disagreements: status by claimant (latest reported_on wins within one
  claimant only), area_treated values by claimant, the union of implementers
  and funders, and the envelope of periods.
- No spatial matching in v1. Sites match only by node ID. If a geometry
  library is already a dependency, add a candidate report for overlapping exact
  geometries; otherwise leave a TODO.

The project itself (decision D17, replacing D8):
- The sketch writes `ImplementationProposition # = project`, which makes an
  information record the same thing as the work that was done. Keep the
  proposition as what it is — the derived grouping record, with the member
  claims and the aggregates — and have derive_projects.py also mint a project
  individual, `proj:<id>`, for the work.
- In project/projects.ttl, export it as a named individual: `rdf:type` the
  canonical strategy class, located at its site individual (verify the
  located-in relation CURIE or use a TODO: placeholder), with the period's
  normalized bounds. The proposition carries IAO:0000136 (is about) that
  individual.
- Why: a project is an occurrent, something that happened at a place over a
  period, and typing it by its strategy class is what makes the strategy class
  worth having. It also gives criteria claims in 7.3 a subject that is a
  particular, so "this project qualifies as effective restoration" is about the
  work rather than about a record of it.
- Project IRIs must stay stable when a claim joins (the ID scheme above). The
  individual and the proposition share the same local ID, and a superseded one
  gets owl:deprecated and IAO:0100001 in the generated output as for
  strategies.

RDF and OWL (decisions D13, D15):
- Declare warp:carried_out_at in warp-relations.ttl, as an object property
  from a strategy or action to a site. Comment that its subject is a class and
  its object an individual, which is why it is asserted only in the
  reification layer: the claim records that a kind of work was done at a
  particular place, and the thing that happened is the project individual, not
  the triple.
- project_owl.py projects nothing directly from implementation claims. The
  project individuals in step above are the logical-layer output of this
  group, and they come from the derivation, not the gate.

Example: in examples/implementation_examples.yaml, the land trust's and the
funder's claims about site:0412 (42 ha vs 40 ha, shared external ID
{scheme: agreement, value: "0412"}) must derive one project with both areas
attributed, and one project individual typed by the earthworks-seed-mow
strategy class. Add a third claim of the same strategy on a different site,
which must stay separate.

Docs: the annotator's test ("done, or should be done?"), and the rule that
planned work is an implementation claim only when committed to a specific
site.

Not in this phase (TODOS.md): spatial identity (Q2), FERM and CMP mapping
(Q7).

Finish per the Definition of done.
```

#### Prompt 7.3: criteria sets, criteria group and the Target 2 report

```text
Read CLAUDE.md and the sections from "Definitions are not nodes" to "Worked
example" in docs/proposal-implementation-group.html. Phase 7.2 must be done.
Start in plan mode.

Schema:
- CriteriaSet, an information record and not a node, with every field in the
  sketch: operationalizes, issued_by, version, status (draft, adopted,
  superseded), supersedes, specified_in, criteria_text, reference_basis,
  baseline_date, attributes_assessed, threshold_kind, threshold_text,
  human_caused, assessment_unit, assessment_basis. Add all the enums.
  EcosystemAttributeEnum uses SER's six attributes; mark the vocabulary as
  provisional (Q4).
- CriteriaConceptEnum {degraded_area, effective_restoration}. Generate the
  concepts as SKOS into project/criteria_concepts.ttl with gen_vocab.py, and
  set each permissible value's `meaning:` to that same concept IRI (decision
  D14). Do not let the concept exist twice: without the meaning, gen-owl mints
  a second IRI under the enum's own namespace and the graph has two
  degraded_areas. The concepts stay skos:Concept and are never owl:Class.
- CriteriaClaim (predicate warp:qualifies_as) and CriteriaProposition,
  registered as a group. Object: a concept. Qualifiers: criteria_set
  (required), assessed_period (required), assessment_method
  (field_assessment, remote_sensing, rule_applied, expert_judgement,
  self_reported).
- Decision D17 (replacing D8): subject is a site individual or a project
  individual, both particulars, so `subject` is plainly required and there is
  no subject_proposition and no exactly_one_of rule (R7 and R18 both go away).
  The Phase 2 engine needs no alternative-subject support. The claim's
  evidential direction carries the verdict (supports, disputes, neutral) and is
  required.
- Checks: the criteria set's `operationalizes` equals the claim's object;
  warn when the subject kind doesn't match the set's assessment_unit (site
  individuals against `site`, project individuals against the rest).
- Identity, using the Phase 2 engine: rule name warp-criteria-identity/1.
  Key: subject, object, criteria_set, assessed_period.
- ClaimSet collections criteria_sets, criteria_claims and
  criteria_propositions.

RDF and OWL (decisions D13, D15, D16):
- In warp-relations.ttl declare an abstract warp:assessed_against with two
  sub-properties under it, warp:qualifies_as and warp:does_not_qualify_as.
  export_rdf.py picks between them from the claim's direction; a neutral
  claim exports its reified record and no relation triple.
- The object of the exported triple is the **criteria set**, not the concept:
  `site:0412 warp:qualifies_as crit:degraded-area/fed-draft-1`. The concept is
  recoverable through the set's `operationalizes`, and keeping it out of the
  triple is what stops a graph from holding `site:0412 qualifies_as
  degraded_area` and `site:0412 does_not_qualify_as degraded_area` as a flat
  contradiction, when the two verdicts are in fact about different
  definitions. Say this in docs/rdf-owl.md: it is the one place where the
  exported object is not the annotated object, and the reason is worth
  recording.
- project_owl.py projects nothing. A criteria set is a stated, versioned test,
  deliberately not an OWL definition, so a verdict can never be inferred —
  which is also what lets a definition change without any record being
  rewritten. This is the right answer to the Q6 open question about automated
  verdicts: a SHACL or SPARQL rule may propose a verdict as a claim with
  assessment_method rule_applied, and it enters the graph as a claim by
  EcoWeaver like any other, never as an axiom.

Report: scripts/report_target2.py --jurisdiction --year --degraded <set IDs>
--effective <set IDs> [--include-planned] [--show-restricted]
1. sites with a supported degraded_area proposition under the degraded set,
   for the baseline period
2. projects on those sites with status in_progress, completed or maintained
   in the reporting year (planned only with the flag)
3. of those, projects with a supported effective_restoration proposition
   under the effective set
4. area: without geometry, report a lower bound (largest area treated per
   site) and an upper bound (sum per site, capped at the site's area), and
   explain both in the output
Decision D9: "supported" means at least one supporting claim and no disputing
claim. List contested propositions separately. Records under restricted care
count toward totals but are listed individually only with --show-restricted.
Allow several definition sets in one run and print a comparison table, so the
effect of choosing a definition is visible.

Example: the proposal's draft federal degraded-area definition, a second
contrasting definition (e.g. a reference_ecosystem basis without
human_caused), an effectiveness definition with assessment_basis trajectory,
and criteria claims for site 0412 and its project. Include one site that
qualifies under one definition and not the other. All definitions are clearly
fictional placeholders.

Not in this phase (TODOS.md): the element vocabulary (Q4), counting rules
(Q5), whether rule_applied verdicts should count toward reporting or only flag
candidates (Q6 — how they enter the graph is settled above; whether a policy
accepts them is not ours to settle), and who authorizes roll-ups over
restricted records (Q8).

Finish per the Definition of done.
```

---

### Phase 8: consolidation

#### Prompt 8: docs, TODOs and the 0.4.0 release

```text
Read CLAUDE.md, README.md, TODOS.md, docs/ and the 0.4.0 entries in the
README's Changes section.

1. README: update sections 1 to 10 for seven predicate groups, the three new
   templates, criteria sets, all four derivation rules (with a table of rule,
   script and key), the new examples, the reports and the layout. Remove
   statements the work has made untrue, such as "two predicate groups" and
   anything that says node classes are ROBOT-checked, which only became true
   in Phase 2.5. Add the output table from section 2.6 of the dev guide, and
   point at docs/rdf-owl.md.
2. Consolidate the 0.4.0 changelog entry. Bump the schema version to 0.4.0.
   The changelog says plainly that 0.4.0 changes what WARP emits as RDF, lists
   the IRI spaces, and notes that `warp:prop/<hash>` keeps a slash in the
   local part, so it is not a legal Turtle prefixed name unhandled and must be
   written in full or escaped in hand-written SPARQL.
3. Write docs/annotation-tests.md: the annotator's test for each group and for
   strategies, in one place, with one example each.
4. TODOS.md: remove what this work completed. Group the open questions that
   remain by proposal, citing question numbers. Keep the existing sections.
   Add one upstream section for what Phase 2.5's clean_owl.py works around, as
   candidate LinkML issues: predicate meanings typed as classes, `owl:unionOf`
   on named enum classes, enum slots declared as object properties with
   literal values in data.
5. Run `make all` from a clean checkout of the branch. Confirm that the JSON
   Schema generates, every example validates, check_refs and check_owl are
   clean, `make owl-check` passes both profiles (EL for the node, axiom, site
   and project files; DL for the schema and relations files), and every report
   runs.
6. Reply with a list of every TODO: placeholder left in examples/, templates/
   and the schema, so I can fill them, and with the projection report: which
   propositions reached project/axioms.ttl and which were rejected, by reason.

Finish per the Definition of done, without opening a pull request.
```

---

### Phase 9: optional extensions

Run these only once you want them. Each one is self-contained.

#### Prompt 9.1: additions from the feedback-models note

```text
Read CLAUDE.md and the section "What would move models up a category" in
docs/feedback-models-compatibility.md. Start in plan mode.

1. Lag on causal claims: time_to_effect (ISO 8601 duration or Quantity) and
   timescale, as causal predicate qualifiers in the profile.
2. Measurable state variables: slots for quantity and unit on the node
   templates that describe outcomes. If outcome templates already have
   measured-pool or sampling-grain slots, extend those rather than adding
   parallel ones.
3. Quantitative effect size with uncertainty beside the ordinal
   effect_strength: value, measure (e.g. log response ratio), and interval or
   standard error.
4. Self-regulation: allow a causal claim whose subject and object are the same
   node, and document how loop analysis reads it.
Add one example claim for each. Don't change proposition identity.

Finish per the Definition of done.
```

#### Prompt 9.2: ThreatAssessment

```text
Read CLAUDE.md and "Related changes" in docs/proposal-recommendation-group.html.
Add ThreatAssessment (is_a SynthesisAssessment), holding IUCN-CMP threat
calculator fields (impact, scope, severity, timing) and DFO fields
(likelihood, impact, spatial extent, temporal extent), each as a ScaledValue
on the source's own scale. Document how DFO's certainty rating maps to
evidence_object and evidence_type. Add a Mountain Sucker example with
placeholder ratings. Finish per the Definition of done.
```

#### Prompt 9.3: rate-of-interaction node template

```text
Read CLAUDE.md, docs/node-templates.md and "Related changes" in
docs/proposal-recommendation-group.html. Add a node template for the rate of
an interaction (e.g. the rate of salmonid predation on Spring Salamander), so
causal claims can modify interaction claims ("sedimentation increases
salmonid predation on salamanders"). Generate its DOSDP pattern and OWL as
for other templates, and add that example. Finish per the Definition of done.
```

#### Prompt 9.4: tolerance importer prototype

```text
Read CLAUDE.md and the "Structured sources" section of
docs/proposal-tolerance-group.html. Build scripts/import_tolerance.py for ONE
source, reading a local file that I will provide (start with a small CSV
extract of USDA PLANTS characteristics, or of EIVE 1.0). Don't download
anything. Before writing code, tell me the licence terms you know of for that
source and what I should confirm.
- One tolerance claim per record and variable. The claimant is the database
  organization. Use class_value for ordinal ratings and range for numeric
  ones. Default scope prototypical, flagged for review (Q6). Evidence type as
  the proposal suggests for that source.
- Use a mapping file from source column to environmental variable node, so
  new columns need no code.
- A test fixture with five rows.
Finish per the Definition of done.
```

---

## 7. Review checklist for each phase

- [ ] Nothing under `src/warp/schema/upstream/` changed (`git diff --stat`).
- [ ] No generated file edited by hand; regenerated outputs match `make all`.
- [ ] The derived proposition IDs for `bloodroot_claims` are unchanged, or the change is explained.
- [ ] Every new CURIE is real, or a `TODO:` placeholder listed in TODOS.md, and nothing invented sits under a real ontology's prefix.
- [ ] Examples contain no invented figures presented as real.
- [ ] Decisions Claude Code made on your behalf are listed in its reply, and you agree with them.
- [ ] New open questions are in TODOS.md, citing proposal question numbers.

From Phase 2.5 on, also:

- [ ] `make owl-check` passes: EL for nodes, axioms, sites and projects; DL for the schema and relations files.
- [ ] `scripts/check_owl.py` is clean: no IRI has two kinds, no `xsd:date`, `xsd:gYear` or `xsd:duration` literal, every CURIE expands, no sentinel value exported.
- [ ] Every predicate the phase minted is declared once in `warp-relations.ttl`, and nowhere else.
- [ ] Polarity reads correctly from the relation triple alone, with no qualifier (D16).
- [ ] The projection report says what passed the gate and why the rest did not, and the gate was not loosened to make something pass.

## 8. Left open on purpose

These questions stay open after 0.4 and need people, not code: they need Lars,
knowledge holders, the semantics working group or Target 2 policy.

- **Lars:** particulars in the node layer (D11 settles the mechanics, not whether they belong there); strategy order in OWL (D6 and Prompt 4 settle how it renders, so the question left is whether part-to-part `precedes` relations are wanted as well); tolerance as a BFO disposition (narrowed in Phase 5); scope of forward-looking guidance.
- **Policy and reporting:** which definition vocabulary (SER, IUCN RLE, FERM); counting rules for Target 2; authorization for roll-ups over restricted records.
- **Data sources:** price indices and wage series for cost transfer; licences for bulk tolerance imports; the Iacona workbook comparison.
- **Modelling:** opportunity and transaction costs; a valuation group; research actions as recommendation objects; conditional steps and alternatives in strategies.
- **Upstream, and blocking publication:** SEPIO's default prefix is still `https://example.org/sepio-model/`, so `subject`, `predicate`, `object`, `hasEvidenceLines` and `targetProposition` have no real IRIs. Phase 2.5 confines this to one constant (R22), but WARP cannot publish its reification layer until SEPIO grounds those terms or WARP mints its own aliases and maps to SEPIO later. Decide which, with the semantics working group, before 0.5.

---

## Appendix: the upstream LinkML fix

Your answer to Q7 asked for this, so here it is as a work item. The short
version is better than expected: **two of the three things `clean_owl.py` was
going to do are not LinkML bugs at all, they are schema settings WARP has not
used.** Only one is a real defect, and its patch is about ten lines.

Checked against `linkml` and `linkml-runtime` 1.11.1, the versions
`requirements.txt` resolves to, by reading
`linkml/generators/owlgen.py` and running `gen-owl` on a four-enum test
schema.

### What is already configurable

`OwlSchemaGenerator._get_metatype()` reads an `implements:` list on an enum, on
a single permissible value, and on a slot, and uses it to decide what OWL
entity to emit. Nothing in WARP sets it. Setting it fixes R13 and R14 in the
profile, with no patch and no post-processing:

| Put this in `warp.yaml` | And `gen-owl` emits |
|---|---|
| `implements: [owl:ObjectProperty]` on a predicate enum | `RO:0002470 a owl:ObjectProperty ; rdfs:label "eats" ; dcterms:isPartOf warp:InteractionPredicateEnum` — no `owl:Class`, no `rdfs:subClassOf`, **and no covering axiom on the enum at all**, because the mixed-type branch leaves `combo_pred` unset |
| `implements: [owl:NamedIndividual]` on a value enum | `…EvidenceTypeEnum#expert_judgment a owl:NamedIndividual, warp:EvidenceTypeEnum` — exactly the shape D14 asks for |
| `implements: [owl:AnnotationProperty]` on a slot | `warp:subject a owl:AnnotationProperty` — which is how D12's annotation assertions get declared |

So the predicate enums (`CausalPredicateEnum`, `InteractionPredicateEnum` and
the five new ones) take `owl:ObjectProperty`; every other enum takes
`owl:NamedIndividual`; and `subject`, `predicate` and `object` take
`owl:AnnotationProperty`. That is a schema edit in Phase 1, not a script.

### The one real defect

`add_enum()` builds the covering axiom by calling

```python
self._boolean_expression(pv_uris, combo_pred, enum_uri, owl_types={...})
```

and `_boolean_expression()` does `graph.add((node, predicate, listnode))`.
Passing `enum_uri` means `owl:unionOf` — or `owl:oneOf`, once the values are
individuals — is written **onto the named class IRI**:

```turtle
warp:EvidenceTypeEnum a owl:Class ;
    owl:oneOf ( <…#randomized_experiment> <…#natural_experiment> … ) .
```

In OWL 2's mapping from RDF graphs, `owl:unionOf`, `owl:oneOf`,
`owl:intersectionOf` and `owl:complementOf` are recognised only with a blank
node subject: they introduce an anonymous class expression. A named class
carrying one does not map to an OWL 2 DL ontology, so the file fails
`robot validate-profile --profile DL`. (Two commented-out lines just above the
call suggest someone had already circled this.)

The fix is to build the expression on a fresh blank node and attach it:

```python
if combo_pred:
    expr = self._boolean_expression(pv_uris, combo_pred, BNode(), owl_types={...})
    if expr is not None:
        g.add((enum_uri, OWL.equivalentClass, expr))
```

which gives the standard form, and validates:

```turtle
warp:EvidenceTypeEnum a owl:Class ;
    owl:equivalentClass [ a owl:Class ;
        owl:oneOf ( <…#randomized_experiment> … ) ] .
```

I ran that as a monkeypatch over 1.11.1 against a test schema and it produces
the shape above for both the `unionOf` (classes) and `oneOf` (individuals)
cases.

Three things to get right in a real patch:

1. **Single-value enums.** `_boolean_expression()` returns `expr_list[0]`
   unchanged when there is one member, so a one-value enum would emit
   `Enum owl:equivalentClass <that one IRI>` — wrong, and wrong in a way that
   bites WARP specifically, since `RecommendationPredicateEnum`,
   `ImplementationPredicateEnum` and `CriteriaPredicateEnum` all have exactly
   one value. Build the one-item list explicitly, or skip the axiom.
2. **The literal branch.** When every value is a literal the enum is a
   datatype, not a class, so the same move needs `rdfs:Datatype` on the
   anonymous node and `owl:equivalentClass` still works (that is OWL 2's
   `DatatypeDefinition`). Do not emit `owl:Class` there.
3. **Backward compatibility.** This changes everyone's output. Put it behind a
   flag — `--enum-covering-axiom asserted|equivalent|none`, defaulting to
   today's behaviour for a release or two — and say in the help text that
   `asserted` does not round-trip through OWL 2 DL.

### What that leaves `clean_owl.py` doing

One job instead of three: move the covering axiom off the named enum class,
until the upstream change lands and the flag can be set instead. Prompt 2.5 is
written accordingly. If you take the patch upstream and it is accepted,
`clean_owl.py` can be deleted outright rather than reduced.

Worth filing as two issues against `linkml/linkml`: one bug ("enum covering
axioms are not valid OWL 2 DL", with the Turtle above), and one documentation
issue (`implements:` on enums, permissible values and slots is the supported
way to control OWL entity types, and is not mentioned in the OWL generator's
docs).
