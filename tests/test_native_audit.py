"""Failure auditing must neither fabricate a launch nor hide missing native work."""

import pytest
from audit_native_v2_run import audit_catalog, audit_unlaunched, audit_verdict


@pytest.mark.parametrize(
    "parent_status,expected",
    [("harness_failure", "dependency_missing"), ("build_failed", "dependency_failed")],
)
def test_audit_accepts_only_declared_failed_build_dependencies(tmp_path, parent_status, expected):
    trial = {"id": "use", "role": "consume", "parent": "build", "build": 1}
    result = {
        "status": expected,
        "parent": "build",
        "reason": parent_status,
        "launched": False,
    }
    results = {"build": {"status": parent_status}}
    audit_unlaunched(tmp_path, trial, result, results)
    with pytest.raises(AssertionError):
        audit_unlaunched(tmp_path, {**trial, "parent": None, "build": None}, result, results)
    with pytest.raises(AssertionError):
        audit_unlaunched(tmp_path, trial, result, {"build": {"status": "package_ready"}})
    with pytest.raises(AssertionError):
        audit_unlaunched(tmp_path, trial, {**result, "reason": "unrecorded"}, results)
    (tmp_path / "attempts/use").mkdir(parents=True)
    with pytest.raises(AssertionError):
        audit_unlaunched(tmp_path, trial, result, results)


def test_catalog_drift_fails_even_when_other_evidence_is_complete():
    assert audit_catalog("use", {"declared"}, {"declared"}) == []
    violations = audit_catalog("use", {"extra"}, {"declared"})
    assert violations == [
        {
            "trial": "use",
            "check": "declared_skill_catalog",
            "unexpected": ["extra"],
            "missing": ["declared"],
        }
    ]
    assert audit_verdict([], violations) == "failed"
    assert audit_verdict([{"unavailable": "output"}], violations) == "failed"
    assert audit_verdict([{"unavailable": "output"}], []) == "qualified"
    assert audit_verdict([], []) == "pass"
