import pytest

from research_agent.core.errors import (
    ErrorCode,
    ResearchError,
    ResearchInputError,
    Severity,
)


def test_error_requires_remediation():
    with pytest.raises(ValueError):
        ResearchError(ErrorCode.E_URL_INVALID, message="URL sai", remediation="")


def test_error_requires_message():
    with pytest.raises(ValueError):
        ResearchError(ErrorCode.E_URL_INVALID, message="", remediation="Sửa URL")


def test_error_as_dict_matches_phase2_shape():
    err = ResearchError(
        error_code=ErrorCode.E_MARKET_UNSUPPORTED,
        message="Không provider nào hỗ trợ market này.",
        remediation="Bỏ market XK hoặc bổ sung provider hỗ trợ.",
        field_path="markets[2].country",
        received="XK",
    )
    d = err.as_dict()
    assert d == {
        "error_code": "E_MARKET_UNSUPPORTED",
        "severity": "error",
        "field_path": "markets[2].country",
        "received": "XK",
        "message": "Không provider nào hỗ trợ market này.",
        "remediation": "Bỏ market XK hoặc bổ sung provider hỗ trợ.",
        "is_retryable": False,
    }


def test_input_error_collects_all_and_filters_blocking():
    errors = [
        ResearchError(
            ErrorCode.E_MARKET_UNSUPPORTED,
            message="market XK không hỗ trợ",
            remediation="bỏ XK",
            severity=Severity.ERROR,
        ),
        ResearchError(
            ErrorCode.E_URL_INVALID,
            message="domain không phân giải",
            remediation="kiểm tra DNS",
            severity=Severity.WARNING,
        ),
    ]
    exc = ResearchInputError(errors)
    assert len(exc.errors) == 2
    assert len(exc.blocking) == 1
    assert exc.blocking[0].error_code is ErrorCode.E_MARKET_UNSUPPORTED
    assert "E_MARKET_UNSUPPORTED" in str(exc)
    assert "E_URL_INVALID" in str(exc)


def test_input_error_needs_at_least_one():
    with pytest.raises(ValueError):
        ResearchInputError([])
