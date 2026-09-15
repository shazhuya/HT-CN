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


def test_bat_and_crab_remain_distinct() -> None:
    bat = CARNEY_RULES["bat"]
    crab = CARNEY_RULES["crab"]

    assert bat.constraints["d_xa"].ideal == 0.886
    assert crab.constraints["d_xa"].ideal == 1.618
    assert bat.constraints["bc_projection"].maximum == 2.618
    assert crab.constraints["bc_projection"].minimum == 2.618


def test_special_schemas_are_not_forced_through_xabcd_identity() -> None:
    shark = CARNEY_RULES["shark"]
    five_zero = CARNEY_RULES["five_zero"]

    assert shark.schema == "0XABC"
    assert not shark.executable_identity
    assert five_zero.schema == "0XABCD"
    assert not five_zero.executable_identity
    assert five_zero.source_conflict


def test_shark_limits_are_explicit() -> None:
    shark = CARNEY_RULES["shark"]
    assert shark.constraints["a_0x"].minimum == 0.382
    assert shark.constraints["a_0x"].maximum == 0.618
    assert shark.constraints["extreme_impulse"].minimum == 1.618
    assert shark.constraints["extreme_impulse"].maximum == 2.24
    assert shark.constraints["completion_0b"].minimum == 0.886
    assert shark.constraints["completion_0b"].maximum == 1.13
