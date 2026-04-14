import pytest


def test_build_result_success():
    from archi.kernel.result import BuildResult

    r = BuildResult(shape="mock_shape", valid=True, volume=1000.0)
    assert r.shape == "mock_shape"
    assert r.valid is True
    assert r.volume == 1000.0
    assert r.diagnostics == {}
    assert r.code_violations == []
    assert r.affected_rooms == []


def test_build_result_failure():
    from archi.kernel.result import BuildResult

    r = BuildResult(
        shape=None,
        valid=False,
        volume=None,
        diagnostics={"reason": "boolean failed", "hint": "simplify geometry"},
    )
    assert r.shape is None
    assert r.valid is False
    assert r.diagnostics["reason"] == "boolean failed"
    assert r.diagnostics["hint"] == "simplify geometry"


def test_build_result_with_violations():
    from archi.kernel.result import BuildResult

    violation = {
        "rule": "IRC-R303.1",
        "severity": "error",
        "message": "Bedroom has no egress window",
        "room": "bedroom_1",
    }
    r = BuildResult(
        shape="mock",
        valid=True,
        volume=500.0,
        code_violations=[violation],
        affected_rooms=["bedroom_1"],
    )
    assert len(r.code_violations) == 1
    assert r.code_violations[0]["severity"] == "error"
    assert r.affected_rooms == ["bedroom_1"]


def test_build_result_ok_property():
    from archi.kernel.result import BuildResult

    good = BuildResult(shape="s", valid=True, volume=100.0)
    assert good.ok is True

    bad_invalid = BuildResult(shape="s", valid=False, volume=100.0)
    assert bad_invalid.ok is False

    bad_no_shape = BuildResult(shape=None, valid=True, volume=100.0)
    assert bad_no_shape.ok is False


def test_build_result_has_errors_property():
    from archi.kernel.result import BuildResult

    no_errors = BuildResult(shape="s", valid=True, volume=100.0)
    assert no_errors.has_errors is False

    warning_only = BuildResult(
        shape="s",
        valid=True,
        volume=100.0,
        code_violations=[{"severity": "warning", "message": "x"}],
    )
    assert warning_only.has_errors is False

    with_error = BuildResult(
        shape="s",
        valid=True,
        volume=100.0,
        code_violations=[{"severity": "error", "message": "x"}],
    )
    assert with_error.has_errors is True


def test_build_result_fail_classmethod():
    from archi.kernel.result import BuildResult

    r = BuildResult.fail("it broke", hint="try again")
    assert r.shape is None
    assert r.valid is False
    assert r.diagnostics["reason"] == "it broke"
    assert r.diagnostics["hint"] == "try again"


def test_build_result_fail_no_hint():
    from archi.kernel.result import BuildResult

    r = BuildResult.fail("it broke")
    assert r.diagnostics["reason"] == "it broke"
    assert "hint" not in r.diagnostics
