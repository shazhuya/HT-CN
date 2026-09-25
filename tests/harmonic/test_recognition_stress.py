from htcn.harmonic.recognition_stress import (
    corpus_fingerprint,
    negative_stress_cases,
    positive_stress_cases,
)


def test_positive_stress_corpus_is_deterministic_and_stratified() -> None:
    first = positive_stress_cases(seeds_per_depth=2)
    second = positive_stress_cases(seeds_per_depth=2)

    assert len(first) == 60
    assert [case.truth.case_id for case in first] == [
        case.truth.case_id for case in second
    ]
    assert {case.minor_pairs for case in first} == {1, 2, 3}
    assert all(len(case.contaminated_legs) == case.minor_pairs for case in first)


def test_negative_stress_corpus_covers_independent_failure_axes() -> None:
    cases = negative_stress_cases(copies_per_kind=4)

    assert len(cases) == 12
    assert {case.kind for case in cases} == {
        "invalid_b",
        "invalid_c",
        "invalid_d",
    }


def test_stress_corpus_fingerprint_is_repeatable() -> None:
    positives_a = positive_stress_cases(seeds_per_depth=1)
    negatives_a = negative_stress_cases(copies_per_kind=2)
    positives_b = positive_stress_cases(seeds_per_depth=1)
    negatives_b = negative_stress_cases(copies_per_kind=2)

    assert corpus_fingerprint(positives_a, negatives_a) == corpus_fingerprint(
        positives_b,
        negatives_b,
    )
