"""Diagnostic failures use fakes; these tests never access the local database."""
import subprocess
import sys
from types import SimpleNamespace

import pytest

import id_detect
import search_db


def test_missing_database_credential_fails_before_connect(monkeypatch):
    monkeypatch.delenv("JIBAS_DB_PASSWORD", raising=False)
    monkeypatch.setitem(sys.modules, "pymysql", SimpleNamespace(
        connect=lambda **kwargs: pytest.fail("Must not attempt a connection")))
    with pytest.raises(id_detect.DetectError, match="JIBAS_DB_PASSWORD"):
        id_detect.DbIdDetector().detect()
    with pytest.raises(id_detect.DetectError, match="JIBAS_DB_PASSWORD"):
        search_db.search("V4YNE", ["jbssat"])


def test_database_credential_is_read_at_connection_time(monkeypatch):
    detector = id_detect.DbIdDetector()
    monkeypatch.setenv("JIBAS_DB_PASSWORD", "fake-session-secret")
    sentinel = object()
    seen = {}

    def connect(**kwargs):
        seen.update(kwargs)
        return sentinel

    monkeypatch.setitem(sys.modules, "pymysql", SimpleNamespace(connect=connect))
    assert detector._connect() is sentinel
    assert seen["password"] == "fake-session-secret"
    assert search_db.connect_kwargs()["password"] == "fake-session-secret"


def test_explicit_password_can_override_environment_including_empty(monkeypatch):
    monkeypatch.setenv("JIBAS_DB_PASSWORD", "fake-environment-secret")
    assert id_detect.database_password("fake-explicit-secret") == "fake-explicit-secret"
    assert id_detect.database_password("") == ""


def test_connection_error_does_not_expose_credential(monkeypatch):
    secret = "fake-sensitive-credential"
    monkeypatch.setenv("JIBAS_DB_PASSWORD", secret)

    def connect(**kwargs):
        raise RuntimeError("connector included password=" + kwargs["password"])

    monkeypatch.setitem(sys.modules, "pymysql", SimpleNamespace(connect=connect))
    with pytest.raises(id_detect.DetectError) as caught:
        id_detect.DbIdDetector().detect()
    assert secret not in str(caught.value)
    assert "[REDACTED]" in str(caught.value)
    assert caught.value.__suppress_context__


def test_query_error_is_wrapped_and_connection_closed(monkeypatch):
    secret = "fake-query-secret"
    monkeypatch.setenv("JIBAS_DB_PASSWORD", secret)
    closed = []

    def execute(*args):
        raise RuntimeError("query rejected " + secret)

    connection = SimpleNamespace(cursor=lambda: SimpleNamespace(execute=execute),
                                 close=lambda: closed.append(True))
    monkeypatch.setattr(id_detect.DbIdDetector, "_connect", lambda self: connection)
    with pytest.raises(id_detect.DetectError, match="Database ID") as caught:
        id_detect.DbIdDetector().detect()
    assert secret not in str(caught.value)
    assert closed == [True]


def test_wmi_timeout_is_a_diagnostic_error(monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("powershell", 60)

    monkeypatch.setattr(id_detect.subprocess, "run", timeout)
    with pytest.raises(id_detect.DetectError, match="60 detik"):
        id_detect.SystemIdDetector().detect()


def test_wmi_nonzero_exit_cannot_accept_partial_output(monkeypatch):
    monkeypatch.setattr(id_detect.subprocess, "run", lambda *args, **kwargs:
                        subprocess.CompletedProcess("powershell", 1,
                            stdout="DISK serial\nUUID uuid\n", stderr="failure"))
    with pytest.raises(id_detect.DetectError, match="exit 1"):
        id_detect.SystemIdDetector().detect()
