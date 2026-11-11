"""Capability routing and six-product transactions, using actual codecs."""
from copy import deepcopy
import importlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

import batch_license
from product_actions import generate_with_backend, verify_with_backend
from product_catalog import PRODUCTS, PRODUCT_BY_KEY

BASE = Path(__file__).resolve().parents[1]
SJS_FIXTURE = json.loads((BASE / "bukti/sjs/smoke_fixture.json").read_text(encoding="utf-8"))
EXPECTED_ORDER = ("face", "fingerprint", "schoolpay", "cbe", "sjs", "letterstore")


def forms():
    snapshots = []
    for product in PRODUCTS:
        values = dict(database_id={"face": "ABCDE", "schoolpay": "Z9X8W", "cbe": "V4YNE",
                                   "sjs": "AB123", "letterstore": "LS123"}.get(product.key, ""),
                      system_id="DDCB4", client_id="", client_name="SYNTHETIC",
                      expires="2030-12-31", capacity="2", previous_license="", file="unused.lic",
                      scanner_serial="SYNTHETIC-SCANNER-001", license_scope="Manager + Client",
                      registration_token=SJS_FIXTURE["registration_token"], school_id=SJS_FIXTURE["school_id"])
        allowed = set(product.input_keys) | {"file"}
        if product.supports_renewal:
            allowed.add("previous_license")
        snapshots.append(dict(product=product.key, label=product.label, codec_module=product.codec_module,
                              filename=product.initial_file, overwrite=False,
                              values={k: v for k, v in values.items() if k in allowed}))
    return snapshots


def test_catalog_order_and_identity_capabilities():
    assert tuple(p.key for p in PRODUCTS) == EXPECTED_ORDER
    assert set(PRODUCT_BY_KEY["fingerprint"].input_keys) == {"scanner_serial", "license_scope", "client_name"}
    assert set(PRODUCT_BY_KEY["letterstore"].input_keys) == {"database_id", "client_name"}
    assert set(PRODUCT_BY_KEY["sjs"].input_keys) == {"database_id", "registration_token", "school_id",
                                                        "client_name", "expires", "capacity"}
    assert {p.key for p in PRODUCTS if p.supports_renewal} == {"face", "schoolpay", "cbe", "sjs"}


@pytest.mark.parametrize("key", EXPECTED_ORDER)
def test_adapter_only_sends_fields_supported_by_product(tmp_path, key):
    product = PRODUCT_BY_KEY[key]
    values = next(item["values"] for item in forms() if item["product"] == key)
    calls = []
    backend = SimpleNamespace(generate_license=lambda **kwargs: calls.append(kwargs) or {"ok": True})
    generate_with_backend(backend, product, values, tmp_path / product.initial_file)
    actual = calls[0]
    expected = {"output_path", "client_name", "overwrite"}
    if product.kind == "fingerprint":
        expected |= {"serial", "license_scope"}
        assert actual["license_scope"] == "both"
    else:
        expected.add("database_id")
        if product.supports_renewal:
            expected |= {"expires", "capacity", "sequence", "previous_license_path"}
            if product.kind == "sjs":
                expected |= {"registration_token", "school_id"}
            else:
                expected |= {"system_id", "client_id"}
    assert set(actual) == expected


def test_all_six_real_codecs_save_and_verify_their_own_identities(tmp_path):
    original = forms()
    before = deepcopy(original)
    result = batch_license.generate_all(original, tmp_path)
    assert original == before
    assert result["ok"] and tuple(result["results"]) == EXPECTED_ORDER
    assert {p.name for p in tmp_path.iterdir()} == {p.initial_file for p in PRODUCTS}
    for item in original:
        product = PRODUCT_BY_KEY[item["product"]]
        codec = importlib.import_module(product.codec_module)
        path = Path(result["paths"][product.key])
        assert path == tmp_path / product.initial_file
        assert result["results"][product.key]["verification"]["valid"] is True
        assert verify_with_backend(codec, product, path, item["values"], for_import=True)["valid"]
        fields = codec.inspect_license(path)["fields"]
        if product.kind == "standard":
            assert fields["DbId"] == item["values"]["database_id"]
            assert fields["Sequence"] == "1"
        elif product.kind == "sjs":
            assert fields["DatabaseId"] == "AB123" and fields["SchoolId"] == SJS_FIXTURE["school_id"]
            assert "Info1" not in fields and "KlienId" not in fields
            assert result["results"]["sjs"]["registration_token"]["database_binding_proven"] is False
        elif product.kind == "fingerprint":
            assert fields["Seri"] == "SYNTHETIC-SCANNER-001" and fields["LicType"] == "CM"
            assert "Sequence" not in fields and "DbId" not in fields
        else:
            assert fields["Info3"] == "LS123" and fields["Klien"] == "SYNTHETIC"
            assert "Sequence" not in fields and "LicenseLimitDate" not in fields


def test_sjs_renewal_recovers_school_id_without_shared_client_id(tmp_path):
    product = PRODUCT_BY_KEY["sjs"]
    codec = importlib.import_module(product.codec_module)
    values = next(f["values"] for f in forms() if f["product"] == "sjs")
    first = generate_with_backend(codec, product, values, tmp_path / "sjs.lic")
    values.update(previous_license=first["path"], school_id="")
    renewed = generate_with_backend(codec, product, values, tmp_path / "sjs-renewal.lic")
    assert renewed["school_id"] == SJS_FIXTURE["school_id"] and renewed["sequence"] == 2
    assert verify_with_backend(codec, product, renewed["path"], values, for_import=True)["valid"]


@pytest.mark.parametrize("scope,lictype", [("Manager + Client", "CM"), ("Manager", "M"), ("Client", "C")])
def test_fingerprint_scope_and_case_sensitive_serial(tmp_path, scope, lictype):
    product = PRODUCT_BY_KEY["fingerprint"]
    codec = importlib.import_module(product.codec_module)
    values = next(f["values"] for f in forms() if f["product"] == "fingerprint")
    values["license_scope"] = scope
    result = generate_with_backend(codec, product, values, tmp_path / "finger.lic")
    assert codec.inspect_license(result["path"])["fields"]["LicType"] == lictype
    assert verify_with_backend(codec, product, result["path"], values, for_import=True)["valid"]
    values["scanner_serial"] = values["scanner_serial"].lower()
    assert not verify_with_backend(codec, product, result["path"], values)["valid"]


def test_letterstore_does_not_require_unrelated_shared_fields(tmp_path):
    product = PRODUCT_BY_KEY["letterstore"]
    codec = importlib.import_module(product.codec_module)
    values = dict(database_id="LS123", client_name="Sekolah Contoh")
    result = generate_with_backend(codec, product, values, tmp_path / "letterstore.lic")
    assert verify_with_backend(codec, product, result["path"], values)["valid"]
    assert codec.inspect_license(result["path"])["fields"]["Klien"] == "Sekolah Contoh"
    assert not verify_with_backend(codec, product, result["path"], dict(values, database_id="ZZ999"))["valid"]


@pytest.mark.parametrize("key,field,value", [
    ("fingerprint", "scanner_serial", ""), ("fingerprint", "license_scope", "unsupported"),
    ("sjs", "registration_token", ""), ("sjs", "school_id", ""),
    ("letterstore", "database_id", ""),
])
def test_new_product_input_errors_block_batch_without_outputs(tmp_path, key, field, value):
    snapshots = forms()
    next(f for f in snapshots if f["product"] == key)["values"][field] = value
    with pytest.raises(batch_license.BatchLicenseError) as caught:
        batch_license.generate_all(snapshots, tmp_path)
    assert caught.value.product == key
    assert list(tmp_path.iterdir()) == []


def test_bad_sjs_token_rejected_by_true_codec_rolls_back_staged_products(tmp_path):
    snapshots = forms()
    next(f for f in snapshots if f["product"] == "sjs")["values"]["registration_token"] = "FAKE"
    with pytest.raises(batch_license.BatchLicenseError, match="Registration Token") as caught:
        batch_license.generate_all(snapshots, tmp_path)
    assert caught.value.product == "sjs"
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("existing", [False, True])
def test_six_product_final_commit_failure_restores_all_outputs(tmp_path, monkeypatch, existing):
    snapshots = forms()
    originals = {}
    if existing:
        for item in snapshots:
            item["overwrite"] = True
            target = tmp_path / item["filename"]
            originals[target] = f"original {item['product']}".encode("ascii")
            target.write_bytes(originals[target])
    real_replace = os.replace
    def fail_final_install(source, destination):
        if Path(source).name == "letterstore.lic":
            raise OSError("simulated last-product commit failure")
        return real_replace(source, destination)
    monkeypatch.setattr(batch_license.os, "replace", fail_final_install)
    with pytest.raises(batch_license.BatchLicenseError, match="dipulihkan") as caught:
        batch_license.generate_all(snapshots, tmp_path)
    assert caught.value.product == "letterstore"
    assert {path: path.read_bytes() for path in tmp_path.iterdir()} == originals
