# Units, counts, scales, places and dates

How WARP records the values that several predicate groups share: a quantity
and its unit, a count of things, a value on a source's own scale, the region a
statement is about, and a date or period. Decisions D18 to D20 of the 0.4 dev
guide; checked by `scripts/check_values.py` (`make check`).

The rule behind all of it: **every value that names something is an IRI under
a declared prefix, and nothing invented sits under a real ontology's prefix.**
A bare token (`ha`, `dfo-recovery-priority`, `florida-usa`) looks fine in YAML
and becomes a relative IRI in RDF, resolved against whatever base the reader
uses: silent garbage that only shows up when two files disagree.

---

## 1. Units

`Quantity` is `{value, unit}`; `QuantityRange` is `{min, max, unit}` with
either end optional (not both) and `min <= max`.

`unit` is a CURIE, in this order of preference:

1. **UO** (Units of Measurement Ontology). UO IDs are numeric:
   `UO:0000008`, never `UO:hectare`.
2. **QUDT** (`unit:`), where UO has no term.
3. **A scale** (`scale:`), when the number is a position on a source's own
   scale rather than a physical quantity. EIVE reaction values (0 to 10) are
   an example: `range: {min: 5.9, max: 7.7, unit: scale:eive-1.0-reaction}`.
4. **A `TODO:` placeholder** when the term has not been verified. Placeholders
   are listed in `TODOS.md` and replaced before release.

**One quantity, one IRI.** Site area and cost scale must use the same IRI for
the hectare, or nothing aggregates. These are the units the examples use:

| Quantity | Use | Status |
|---|---|---|
| hectare | `TODO:unit_hectare` | Not verified offline. Candidates: a UO term, else QUDT `unit:HA`. |
| person-day (labour effort) | `TODO:unit_person_day` | Not verified offline. UO has no person-day that we know of; check QUDT. |
| pH | `TODO:unit_pH` | Not verified offline. Candidate: the UO pH term. |
| centimetre (depth) | `TODO:unit_centimetre` | Not verified offline. Candidate: the UO centimetre term. |

Replace a placeholder everywhere at once (search the repository for it), so
the one-IRI rule keeps holding.

**A count is not a unit.** "46 protected areas" is a `Count`:
`{value: 46, entity: TODO:protected_area}`. `entity` names the kind of thing
counted (a node, an ENVO term, or a placeholder). Writing
`{value: 46, unit: protected_area}` would claim that "protected area" is a
unit of measurement.

## 2. Scales

A `ScaledValue` is a value on a source's own ordinal or categorical scale:

```yaml
priority: {value: medium,
           scale: scale:dfo-recovery-priority,
           concept: scale:dfo-recovery-priority/medium}
```

- `value` is the source's wording, verbatim.
- `scale` is the IRI of a SKOS concept scheme registered in
  `vocab/scales.yaml`.
- `concept` is the IRI of the value inside that scheme:
  `scale:<scale id>/<value id>`.

`make vocab` (`scripts/gen_vocab.py`) writes `project/scales.ttl`: one
`skos:ConceptScheme` per scale and one `skos:Concept` per value, each with an
explicit `warp:ordinal`, so "medium" can be compared with "high" in SPARQL
without a script knowing DFO's order. Each scheme's `skos:scopeNote` says what
the ordinal measures.

**A practitioner's wording is not a scale.** "Prefers wet ground" is recorded
as `{value: wet}`, with no scale and no concept. `practitioner-free` is listed
in `vocab/scales.yaml` only so the check can refuse it as a `scale`.

To add a scale: add an entry to `vocab/scales.yaml` with an `id`, a `label`,
the `body` it comes from, what its `ordinal` measures, and at least two
`values` in ascending order. Value ids must be IRI-safe (letters, digits,
`.`, `_`, `-`).

## 3. Places

`place` is the **region** a statement is about. It is not `ecosystem_context`,
which is the **kind** of ecosystem, one of CAMO's IUCN Global Ecosystem
Typology functional groups:

| | `place` | `ecosystem_context` |
|---|---|---|
| Says | where | what kind of system |
| Example | `ISO3166-2:US-FL` (Florida) | `warm_temperate_forests` |
| Range | an IRI from a place scheme | `EcosystemFunctionalGroupEnum` |
| In identity keys | tolerance, cost | none |

A statement can be about a municipality, a watershed or a treaty area, which
says more than a coordinate pair with an unclear radius around it. So `place`
takes an IRI, never a name and never a point standing in for an area.

### Finding an IRI for a place

Work down this list and stop at the first that has the place:

1. **ISO 3166-2**, for a country subdivision (province, territory, state):
   `ISO3166-2:CA-SK` for Saskatchewan. The code is on the ISO Online Browsing
   Platform and in the Wikidata item's "ISO 3166-2 code" (P300).
2. **Wikidata**, for anything with a settled identity: a municipality, a
   park, a lake, a watershed, a First Nation's territory. Search
   <https://www.wikidata.org>, check the item is the place you mean (look at
   its "instance of" and its coordinates), and use its QID: `wd:Q1234`.
3. **A gazetteer**, where Wikidata has no item:
   - GeoNames (<https://www.geonames.org>): `geonames:<id>`, the number in the
     feature's URL.
   - Getty Thesaurus of Geographic Names (<https://www.getty.edu/research/tools/vocabularies/tgn/>):
     `tgn:<id>`.
4. **An ENVO ecoregion individual**, for an ecoregion as such (ENVO has the
   WWF ecoregions as named individuals): `ENVO:<number>`.
5. **A local concept**, failing all of these: `place:<slug>`, with a label and
   the place it nests inside recorded in the example's comments, and a TODO
   to replace it. Use this rather than inventing a Wikidata QID.

For Indigenous territories, prefer the IRI the nation itself uses or
endorses, and follow the CARE metadata on the statement. Where a territory's
boundary is itself sensitive, a broader place (the province) is the honest
choice.

The allowed prefixes are the `warp_allowed_prefixes` annotation on the
`place` slot in `warp.yaml`; `check_values.py` refuses anything else.

## 4. Dates and periods

Dates, years and periods are ISO 8601 strings at whatever granularity the
source gives: a year (`2023`), a year and month (`2024-05`) or a full date
(`2026-03-31`). A `Period` is `{start, end}`; an absent `end` means open or
ongoing.

Never compare the strings. `scripts/warp_time.py` turns each into half-open
bounds (`2024-05` covers 2024-05-01T00:00:00Z up to, not including,
2024-06-01T00:00:00Z), and every overlap test uses those bounds. Exporters
write the verbatim string plus the bounds as `xsd:dateTime`.

`xsd:date`, `xsd:gYear` and `xsd:duration` never appear in a generated file.
They are not in the OWL 2 datatype map, so a reasoner or profile checker
rejects them. The one exception in the schema is
`recordMetadata.dateRecordCreated`, which is a full timestamp already.

## 5. Prefixes and placeholders

Every prefix an example uses is declared in `warp.yaml`. WARP's own spaces:

| Prefix | Expands to | Holds |
|---|---|---|
| `prop:` | `…/warp/prop/` | propositions (same IRIs as `warp:prop/…`) |
| `stmt:` | `…/warp/statement/` | statements (same as `warp:statement/…`) |
| `doc:` | `…/warp/doc/` | documents (same as `warp:doc/…`) |
| `org:`, `person:` | `…/warp/agent/org/`, `…/warp/agent/person/` | agents |
| `site:` | `…/warp/site/` | sites: OWL individuals |
| `proj:` | `…/warp/project/` | projects: OWL individuals |
| `comp:` | `…/warp/component/` | strategy components |
| `crit:` | `…/warp/criteria/` | criteria sets |
| `concept:` | `…/warp/concept/` | criteria concepts |
| `scale:` | `…/warp/scale/` | source scales and their values |
| `place:` | `…/warp/place/` | locally minted places |
| `TODO:` | `…/warp/TODO/` | placeholders for unverified terms |

`…` is `https://w3id.org/ecoweaver`. **Placeholders always use `TODO:`.**
`TODO:planting` can never be mistaken for an ELMO term; `ELMO:TODO_planting`
can, and in Turtle it is indistinguishable from a real one.
`check_values.py` refuses a placeholder under a real prefix, and a
non-numeric ID under an OBO prefix.
