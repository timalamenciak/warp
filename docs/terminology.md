# Terminology: which term to use, and where it lives

Every value in WARP that names something (a habitat, an action, a place, a
unit, a kind of cost) is a term. This page says how to choose one, and what
to do when no existing ontology has it. The per-slot details (which unit
ontology, which place schemes) are in `docs/values.md`; node template terms
are in `docs/node-templates.md`.

## 1. The order of preference

Work down this list and stop at the first that fits.

| Tier | What | Looks like | When |
|---|---|---|---|
| 1 | **An ontology term** | `ENVO:01000177`, `UO:0000008`, `wd:Q1234` | Always the first choice. The term exists, you have checked its label and definition, and it means what you mean. |
| 2 | **A local term with an upstream plan** | `place:northern-great-plains`, `term:hand_seeding` with `upstream: {status: to_request}` | No ontology has it, but one should: the term is general, the ontology's scope covers it, and its definition does not depend on a WARP decision. Request it, and deprecate the local term once the ontology has it. |
| 3 | **A local term alone** | `concept:degraded_area` with `upstream: {status: not_appropriate, reason: ...}` | Upstreaming is not appropriate, and the register says why: the term only exists because of a WARP design decision, it is a source's own wording, or its governance belongs to a community and not to an ontology (see 4.3). |
| 4 | **Plain text** | `{value: wet}`, `jurisdiction: "<territory name>"` | Last resort, and a corner case: only in slots that say they accept text (section 6). If you find yourself writing text because no term fits, the answer is almost always tier 2 or 3. |

**`TODO:` is not a tier.** `TODO:grassland` means "the lookup has not been
done yet", not "there is no term". Every placeholder is resolved to tier 1, 2
or 3 before a release, and listed in `TODOS.md` (8.1) until then. Use one
when you cannot check a term now (offline, no access to the ontology), never
as a way of recording that a term is missing: that is a tier-2 entry.

## 2. Finding a tier-1 term

1. Search the ontology the slot allows (its `warp_allowed_prefixes`, or the
   template variable's `allowed_prefixes`) in OLS
   (<https://www.ebi.ac.uk/ols4/>), or Wikidata for places.
2. Read the **definition**, not just the label. "Grassland" in ENVO is a
   biome, an ecosystem and an area of land, three terms.
3. Check the term is not obsolete. An obsolete term names its replacement
   (`IAO:0100001`, "term replaced by").
4. Offline, the ECOCORE imports in `C:\ODK\harvest\ecocore\imports\*.owl`
   have BFO, RO, IAO, ENVO, PATO, PCO, PO, UBERON, CHEBI and GO terms. They
   are **subsets** (only the terms ECOCORE uses), so a term missing from them
   may still exist: use a `TODO:` placeholder and check online later.

Never put a guessed or invented ID under a real ontology's prefix.
`check_values.py` refuses non-numeric OBO IDs and anything marked TODO under
a real prefix, but it cannot tell a plausible wrong number from a right one.

## 3. Concept or class: where the term is used decides

A local term is written one of two ways, and the slot decides which:

| The term is used as | So it is | Examples | Written to |
|---|---|---|---|
| a **value**: the object of a property | a SKOS concept (an individual) | `place`, scale values, an enum value's `meaning` | `project/local_terms.ttl` |
| a **class**: a node template filler, an `rdf:type`, or a kind of thing | an OWL class | template fillers (actions, taxa, qualities), a site's `ecosystem_type`, a `Count`'s `entity` | `project/local_classes.ttl` |

A SKOS concept cannot fill a template variable: node definitions become
`owl:equivalentClass` expressions, and a concept there would make one IRI
both an individual and a class, which `check_owl.py` refuses (docs/rdf-owl.md,
"one IRI is one kind of thing"). So an action ELMO lacks is a tier-2
**class** stub under `term:`, not a SKOS concept. A template variable
accepts one only if it lists `term` in its `allowed_prefixes`; give the stub
a `broader` upstream class (the ELMO action it is a kind of) so it still sits
in the right place in the hierarchy.

## 4. The local term register

Local terms (tiers 2 and 3) are listed in `vocab/local/`, one file per
scheme. `make vocab` (`scripts/gen_vocab.py`) writes them out, and
`check_values.py` refuses a local IRI that is not in the register.

### 4.1 Format

An illustration (the real entries are in `vocab/local/`). The upstream
fields are shown together for reference; each status needs only its own
(4.2), and `replaced_by` is refused on any status but `accepted`.

```yaml
scheme:
  id: local-places              # the scheme's IRI is <prefix>:<id>
  label: WARP local places
  prefix: place                 # a WARP prefix declared in warp.yaml
  kind: concept                 # concept (SKOS) or class (OWL)

terms:
  - id: northern-great-plains   # the term's IRI is <prefix>:<id>
    label: northern Great Plains
    definition: >-
      The northern part of the North American Great Plains, as the
      tolerance and cost examples' sources use it.
    broader: place:great-plains  # optional: in this scheme -> skos:broader,
                                 # elsewhere -> skos:broadMatch (concepts)
                                 # or rdfs:subClassOf (classes)
    upstream:
      target: Wikidata          # where the term should live
      status: to_request
      issue: https://...        # required once status is requested
      reason: ...               # required when status is not_appropriate
      replaced_by: wd:Q...      # required when status is accepted
```

`id`, `label`, `definition` and `upstream.status` are required. The
prefixes a scheme may use are WARP's own: `concept:` and `place:` for SKOS
concepts, `term:` for OWL classes (all declared in `warp.yaml`). `TODO:` and
`scale:` are not register prefixes (scales have `vocab/scales.yaml`).

### 4.2 Upstream status

| `status` | Tier | Means | Needs |
|---|---|---|---|
| `not_checked` | 2 until decided | Nobody has yet searched the upstream or decided whether it belongs there. | `target` optional |
| `to_request` | 2 | Searched; absent; should be requested. | `target` |
| `requested` | 2 | The request is filed. | `target`, `issue` |
| `accepted` | retired | The upstream has the term. The local term is deprecated. | `target`, `replaced_by` |
| `not_appropriate` | 3 | Stays local, permanently. | `reason` |

`not_checked` exists so that terms minted before this workflow can be listed
honestly. A new term should start at `to_request` or `not_appropriate`.

### 4.3 When upstreaming is not appropriate

Say which of these applies in `reason`:

- **A WARP design decision.** The term only exists because of how WARP models
  something (criteria concepts name what a criteria set defines, D14).
- **A source's own wording.** A value on a source's scale belongs to that
  source; scales have their own file for this reason.
- **Community governance.** An Indigenous territory, practice or knowledge
  category whose naming and boundaries belong to the nation or community.
  Follow its protocols and the statement's CARE metadata; a broader public
  place may be the honest choice (docs/values.md, section 3).
- **The upstream declined.** Link the issue.

### 4.4 Retiring a term once it is upstreamed

1. Set `status: accepted` and `replaced_by` to the new CURIE (and
   `issue` if there is one). Never delete the entry: published IRIs stay
   resolvable. `gen_vocab.py` writes it as `owl:deprecated true` with
   `IAO:0100001` (term replaced by), and for a concept `skos:exactMatch`.
2. Replace every use in the input files (`examples/*_statements.yaml`,
   `templates/`, `config/`, the schema) in one change, so one thing keeps one
   IRI. `check_values.py` refuses a deprecated term in a statement set and
   names its replacement; templates and config are not checked for this
   yet, so search the repository for the old CURIE as well.
3. `make all`. A term in an identity key (`place` in tolerance and cost, or
   a node filler) changes the derived proposition and node IDs that use it:
   name them in `CHANGELOG.md`, as for any derived ID change.

## 5. Placeholders (`TODO:`)

- Always under the `TODO:` prefix (`TODO:planting`), never under a real one
  (`ELMO:TODO_planting`): in Turtle the second is indistinguishable from a
  real term (D20, R21).
- Listed in `TODOS.md` 8.1 with what each stands for.
- Replaced everywhere at once when resolved, to a tier-1 term or to a
  register entry.

## 6. Plain text

Text in place of a term is allowed only where a slot says so:

| Slot | Text means |
|---|---|
| `ScaledValue.value` with no `scale` | A practitioner's wording that is on no scale ("wet") |
| `SiteDefinition.jurisdiction` | A jurisdiction with no ISO 3166-2 code, as for many Indigenous territories |

Wording fields (`statementText`, `original_text`, labels, definitions) are
not terminology and are not covered here. A slot that should take text in
future says so in its description, and is added to this table.

## 7. Enum values

An enum value is a term too. Where a profile enum names things in the domain
(not workflow states such as `CriteriaStatusEnum`), each value should carry a
`meaning:` that follows the same order: an ontology term, else a register
concept (as `CriteriaConceptEnum` does with `concept:`). Most domain enums do
not do this yet (`TODOS.md`, "Terminology").

## 8. What checks what

| Check | Where |
|---|---|
| Undeclared prefix, placeholder under a real prefix, non-numeric OBO ID, prefix outside the slot's allowed list | `check_values.py` |
| A local IRI (`place:`, `concept:`, `term:`) in a statement set that is not in the register, or is deprecated | `check_values.py` |
| A register entry missing a required field for its status, a duplicate IRI, a prefix that is not WARP's | `gen_vocab.py` (`make vocab`) |
| A template filler outside the variable's allowed prefixes | `expand_nodes.py` |
| One IRI used as two kinds (a concept used as a class) | `check_owl.py` |
