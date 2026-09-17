from htcn.harmonic.rules import CARNEY_RULES


def test_core_xabcd_registry_is_present() -> None:
    assert {
        "gartley",
        "bat",
        "alternate_bat",
        "butterfly",
        "crab",
        "deep_crab",
    }.issubset(CARNEY_RULES)


def test_gartley_and_butterfly_use_strict_three_point_b_tolerance() -> None:
    gartley = CARNEY_RULES["gartley"].constraints["b_xa"]
    butterfly = CARNEY_RULES["butterfly"].constraints["b_xa"]

    assert gartley.contains(0.618)
    assert not gartley.contains(0.60)
    assert gartley.contains(0.60, include_tolerance=True)
    assert not gartley.contains(0.57, include_tolerance=True)

    assert butterfly.contains(0.786)
    assert butterfly.contains(0.81, include_tolerance=True)
    assert not butterfly.contains(0.83, include_tolerance=True)


def test_standard_xabcd_rules_enforce_c_point_family() -> None:
    for pattern_id in (
        "gartley",
        "bat",
        "alternate_bat",
        "butterfly",
        "crab",
        "deep_crab",
    ):
        c_point = CARNEY_RULES[pattern_id].constraints["c_ab"]
        assert c_point.minimum == 0.382
        assert c_point.maximum == 0.886


def test_bat_and_crab_remain_distinct() -> None:
    bat = CARNEY_RULES["bat"]
    crab = CARNEY_RULES["crab"]

    assert bat.constraints["d_xa"].ideal == 0.886
    assert crab.constraints["d_xa"].ideal == 1.618
    assert bat.constraints["bc_projection"].maximum == 2.618
    assert crab.constraints["bc_projection"].minimum == 2.618
    assert bat.abcd_minimum == 1.0
    assert crab.abcd_minimum == 1.0


def test_alternate_bat_conflict_is_explicit_and_not_a_hard_abcd_gate() -> None:
    alternate = CARNEY_RULES["alternate_bat"]
    assert alternate.source_conflict
    assert alternate.abcd_types == (1.618,)
    assert alternate.abcd_minimum is None
    assert "Volume Two explicitly says AB=CD is not included" in alternate.implementation_note


def test_special_schemas_use_dedicated_evaluators_not_generic_xabcd_identity() -> None:
    shark = CARNEY_RULES["shark"]
    five_zero = CARNEY_RULES["five_zero"]

    assert shark.schema == "0XABC"
    assert not shark.executable_identity
    assert five_zero.schema == "FIVE_ZERO"
    assert not five_zero.executable_identity
    assert five_zero.source_conflict


def test_shark_source_ratios_are_explicit() -> None:
    shark = CARNEY_RULES["shark"]
    assert (shark.constraints["a_0x"].minimum, shark.constraints["a_0x"].maximum) == (0.382, 0.618)
    assert (shark.constraints["b_xa"].minimum, shark.constraints["b_xa"].maximum) == (1.13, 1.618)
    assert (shark.constraints["c_ab"].minimum, shark.constraints["c_ab"].maximum) == (1.618, 2.24)
    assert (shark.constraints["c_0b"].minimum, shark.constraints["c_0b"].maximum) == (0.886, 1.13)


def test_five_zero_structural_source_is_resolved_but_v3_label_conflict_stays_quarantined() -> None:
    five_zero = CARNEY_RULES["five_zero"]
    assert (five_zero.constraints["b_xa"].minimum, five_zero.constraints["b_xa"].maximum) == (1.13, 1.618)
    assert (five_zero.constraints["c_ab"].minimum, five_zero.constraints["c_ab"].maximum) == (1.618, 2.24)
    assert "d_bc" not in five_zero.constraints
    assert five_zero.source_conflict is True
    assert five_zero.executable_identity is False
    assert "structural 5-0 Raw PRZ as 50% BC retracement + Reciprocal AB=CD" in five_zero.source_note
    assert "Research-only production quarantine" in five_zero.implementation_note
    assert "structural Source Raw PRZ is resolved" in five_zero.implementation_note
    assert "must never be collapsed into a generic 50%-61.8% band" in five_zero.implementation_note
    assert "raw_prz_membership=false" in five_zero.implementation_note
    assert "Volume Three's inconsistent leg labels" in five_zero.implementation_note
