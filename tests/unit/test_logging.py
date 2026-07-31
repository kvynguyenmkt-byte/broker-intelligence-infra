"""Credentials KHÔNG BAO GIỜ được lọt vào log (CLAUDE.md mục 5)."""
import logging

from research_agent.core import logging as rlog


def test_redact_masks_known_secret_values():
    out = rlog.redact("login ok with s3cr3t-pass", secret_values=("s3cr3t-pass",))
    assert "s3cr3t-pass" not in out
    assert "***REDACTED***" in out


def test_redact_masks_key_value_patterns():
    for text in [
        "DATAFORSEO_PASSWORD=hunter2",
        "api_key: abc123",
        "Authorization=Bearer_xyz",
        "token = t0ken",
    ]:
        out = rlog.redact(text)
        assert "***REDACTED***" in out
        assert "hunter2" not in out
        assert "abc123" not in out
        assert "t0ken" not in out


def test_secret_redactor_filter_uses_env(monkeypatch):
    monkeypatch.setenv("AHREFS_API_TOKEN", "super-secret-token")
    record = logging.LogRecord(
        name="research_agent.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="calling ahrefs with super-secret-token now",
        args=(),
        exc_info=None,
    )
    assert rlog.SecretRedactor().filter(record) is True
    assert "super-secret-token" not in record.getMessage()
    assert "***REDACTED***" in record.getMessage()


def test_get_logger_prefixes_run_id():
    adapter = rlog.get_logger("intake", run_id="run_20260731T0930Z_exness-com")
    msg, _ = adapter.process("validating input", {})
    assert msg == "[run=run_20260731T0930Z_exness-com] validating input"


def test_get_logger_without_run_id_uses_dash():
    adapter = rlog.get_logger("intake")
    msg, _ = adapter.process("hello", {})
    assert msg == "[run=-] hello"
