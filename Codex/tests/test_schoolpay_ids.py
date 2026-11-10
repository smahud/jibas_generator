"""SchoolPay ID regressions from original method CIL and live oracle capture."""
from schoolpay_id_detect import DB_RECIPE, DbIdDetector, SystemIdDetector, DetectError
import pytest


def test_schoolpay_recipe_is_distinct_from_face():
    assert DB_RECIPE == ((2, 2, 9), (7, 3, 21), (10, 6, 12), (1, 6, 32), (9, 6, 45))
    detector = DbIdDetector()
    assert detector.database == "jbsfina"


def test_schoolpay_rejects_unsafe_database_identifier():
    with pytest.raises(DetectError):
        DbIdDetector(database="jbsfina`; DROP DATABASE jbssat")


def test_shared_hardware_raw_serial_parity():
    # Original SchoolPay 0945 and Face 059B independently returned DDCB4.
    assert SystemIdDetector.compute("30029941042         ", "E0813C3C-120B-02FE-5F00-BCAEC5319E78") == "DDCB4"


def test_query_error_redacts_supplied_secret(monkeypatch):
    class FakeConnection:
        closed=False
        def cursor(self):
            raise RuntimeError('connector failed with SYNTHETIC_SECRET')
        def close(self):
            self.closed=True
    connection=FakeConnection()
    detector=DbIdDetector(password='SYNTHETIC_SECRET')
    monkeypatch.setattr(detector,'_connect',lambda:connection)
    with pytest.raises(DetectError) as error:
        detector.detect()
    assert 'SYNTHETIC_SECRET' not in str(error.value)
    assert '[REDACTED]' in str(error.value)
    assert connection.closed


def test_empty_schema_does_not_call_splang(monkeypatch):
    class FakeCursor:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def execute(self,statement,parameters):
            assert 'information_schema.TABLES' in statement
        def fetchone(self): return (0,)
    class FakeConnection:
        closed=False
        def cursor(self): return FakeCursor()
        def close(self): self.closed=True
    connection=FakeConnection()
    detector=DbIdDetector(password='SYNTHETIC_SECRET')
    monkeypatch.setattr(detector,'_connect',lambda:connection)
    with pytest.raises(DetectError,match='tidak mempunyai tabel'):
        detector.detect()
    assert connection.closed
