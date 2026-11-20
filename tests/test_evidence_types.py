"""WarpEvidenceTypeEnum mirrors CAMO's EvidenceTypeEnum plus not_stated (D2, D3).

If CAMO is re-vendored with a new evidence type, this fails until the profile
enum gains it too, so re-vendoring cannot silently drop a value.
"""


def mappings(pv):
    return sorted(pv.broad_mappings or []), pv.meaning, " ".join((pv.description or "").split())


def test_profile_enum_has_every_camo_value(schemaview):
    camo = schemaview.get_enum("EvidenceTypeEnum").permissible_values
    warp = schemaview.get_enum("WarpEvidenceTypeEnum").permissible_values
    missing = set(camo) - set(warp)
    assert not missing, f"add to WarpEvidenceTypeEnum: {sorted(missing)}"


def test_same_meanings_and_mappings(schemaview):
    camo = schemaview.get_enum("EvidenceTypeEnum").permissible_values
    warp = schemaview.get_enum("WarpEvidenceTypeEnum").permissible_values
    for name, pv in camo.items():
        assert mappings(warp[name]) == mappings(pv), name


def test_not_stated_is_the_only_addition(schemaview):
    camo = schemaview.get_enum("EvidenceTypeEnum").permissible_values
    warp = schemaview.get_enum("WarpEvidenceTypeEnum").permissible_values
    assert set(warp) - set(camo) == {"not_stated"}
    assert warp["not_stated"].meaning is None     # a sentinel: no meaning (D14)


def test_expert_opinion_is_not_a_value(schemaview):
    """Proposals write expert_opinion; WARP uses CAMO's expert_judgment (D2)."""
    assert "expert_opinion" not in schemaview.get_enum("WarpEvidenceTypeEnum").permissible_values


def test_evidence_lines_use_the_profile_enum(schemaview):
    assert schemaview.induced_slot("evidence_type", "EcoEvidenceLine").range == "WarpEvidenceTypeEnum"
