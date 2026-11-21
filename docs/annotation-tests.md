# Annotator's tests

One question per predicate group, and one for strategies, that tells you where
a sentence belongs. When a sentence passes two tests, record two statements and
link them (the links are named below). Examples are illustrative; the worked
examples in `examples/` show each in full.

## Causal or interaction

**Is the source saying that a change in one thing brings a change in
another, or that organisms of one population act on another?**

- "Planting bloodroot reduced garlic mustard growth" → **causal**
  (`prevents`), subject and object node variables.
- "Deer do not browse garlic mustard" → **interaction** (`eats`, negated),
  subject and object population nodes.

## Recommendation or causal

**Is the source telling someone what to do, or describing what happens?**

- "Avoid stocking predacious sportfish in the Milk River" → **recommendation**
  (`guidance: avoid`).
- "Stocking predacious sportfish can reduce Mountain Sucker abundance" →
  **causal**, `modality: anticipated`.

When a sentence does both, record both; the guidance cites the causal
proposition through `justified_by`. Predictions are never derived from guidance
automatically.

## Strategy or part

**Does the source report this for the actions together, or for each one?**

- "Recontouring and seeding the site cost $48,000" → about the **strategy**:
  the subject is the strategy node.
- "Seeding added $9,000" → about **one part**: the subject is the seeding
  action node.

Never divide a strategy-level figure among its parts.

## Tolerance or causal

**Is the source saying under what conditions the organism can live, or what
changes what?**

- "Grows on soils of pH 5.5 to 8" → **tolerance** (`tolerates`, with a range).
- "Compaction reduces root penetration" → **causal**.

A tolerance explained by a mechanism links to the causal proposition through
`explained_by`. `tolerates` and `intolerant_of` are recorded as stated, never
derived from each other.

## Cost or causal

**Is the source saying what an action took, or what it did?**

- "Treating 600 ha took two seasons and cost NIS 17,600" → **cost**
  (`incurs_cost total`, with amount, scale and phase).
- "Treatment led to regeneration of native vegetation" → **causal**.

The cost statement points at the causal statements through
`outcome_reported`. The aim goes on the source's study result
(`stated_goal`), never on the cost.

## Implementation or recommendation

**Does the source say this was done, or that it should be done?**

- "We recontoured and seeded 42 ha of site 0412 in 2024" → **implementation**
  (`carried_out_at`, a site, a period, a status).
- "Recontouring is recommended for sites like this" → **recommendation**.

Scheduled work is an implementation statement with `status: planned` only if
it is committed to a specific site.

## Criteria

**Is someone applying a named, versioned definition to a site or project?**

- "Under the federal draft definition (version draft-1), site 0412 qualified
  as degraded in 2023" → **criteria** (`qualifies_as degraded_area`,
  `criteria_set`, `assessed_period`, `direction: supports`).
- "The site is degraded", with no definition named → **context**, not a
  criteria statement.

A criteria statement always names its criteria set and the period assessed.
A verdict about restoration work is about the project (`proj:`), not about the
site or a record of the work.
