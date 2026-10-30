# How to add a predicate group

A **predicate group** is one kind of statement: causal statements, biotic interaction
statements, occurrence statements, and so on. Each group brings:

- a **predicate list**: the controlled verbs statements can use;
- **predicate qualifiers**: what *kind* of relation is asserted (for causal
  statements: the philosophical account and causal features);
- a **statement class** and a **proposition class**, constraining subject,
  predicate and object;
- two **StatementSet lists**: one for statements, one for propositions.

Groups share everything else: the SEPIO frame, scope, hedging conventions,
CARE metadata, evidence lines, synthesis assessments and proposition
derivation.

The repository has two groups. **causal** reuses CAMO's predicates and
features. **interaction** (biotic interactions) is a small worked example of
adding a group; every step below points at it in
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
causal: 2 proposition(s) under warp-prop-identity/3
interaction: 1 proposition(s) under warp-prop-identity/3
```

If your group is missing, the registry annotations are incomplete or the
predicate's range is not an enum.

Then:

1. Add at least one example statement to `examples/` (the interaction example is
   `warp:statement/notebook-i1` in `bloodroot_statements.yaml`).
2. Check the rendered proposition text reads sensibly.
3. Bump the schema `version` and note the new group in the README.

## Identity: what makes two statements the same proposition

All groups share identity rule `warp-prop-identity/3`: two statements share a
proposition when **group, subject, predicate, object, negated and scope**
match. Predicate qualifiers do not count, so disagreements about, say,
reversibility show up as variation across statements of one proposition rather
than as separate propositions.

If a group genuinely needs a different identity rule (for example, if an
interaction's life stage should split propositions), that is a change to
`derive_propositions.py`: make it, bump `RULE_VERSION`, and expect existing
proposition ids for that group to change.

## Checklist

- [ ] Predicate enum with `meaning` and `rosetta_template` for every value
- [ ] Qualifier class, no slot names that collide with SEPIO
- [ ] Statement class: `is_a: EcoStatement`, four registry annotations, subject / predicate / object constrained
- [ ] Proposition class: `is_a: EcoProposition`, same constraints
- [ ] Two StatementSet lists, named as in the annotations
- [ ] Node templates exist for the subjects and objects
- [ ] Example statement; `make all` passes; version bumped
