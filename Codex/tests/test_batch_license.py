"""Batch behavior exercised with real product codecs and temporary outputs."""
from copy import deepcopy
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

import batch_license
import cbe_codec
import license_codec
import schoolpay_codec


BACKENDS = {"face": license_codec, "schoolpay": schoolpay_codec, "cbe": cbe_codec}


def forms():
    return [dict(product=key, label=label, codec_module=module, filename=filename, overwrite=False,
                 values=dict(database_id=dbid, system_id=systemid, client_id="", client_name="",
                             expires="2030-12-31", capacity="25", previous_license="",
                             file="unused-individual-destination.lic"))
            for key, label, module, filename, dbid, systemid in (
                ("face", "Absensi Wajah", "license_codec", "absensi-wajah.lic", "ABCDE", "123AB"),
                ("schoolpay", "SchoolPay", "schoolpay_codec", "schoolpay.lic", "Z9X8W", "A1B2C"),
                ("cbe", "CBE Server", "cbe_codec", "cbe-server.lic", "V4YNE", "DDCB4"))]


def test_new_and_renewal_round_trip_for_all_three_products(tmp_path):
    original_forms = forms()
    snapshot = deepcopy(original_forms)
    new = batch_license.generate_all(original_forms, tmp_path)
    assert original_forms == snapshot
    assert new["ok"] is True
    assert len(list(tmp_path.iterdir())) == 3
    for item in original_forms:
        key = item["product"]
        result = new["results"][key]
        path = Path(new["paths"][key])
        assert path == tmp_path / item["filename"]
        assert result["path"] == str(path)
        assert result["mode"] == "new" and result["sequence"] == 1
        assert result["verification"]["valid"] is True
        fields = BACKENDS[key].inspect_license(path)["fields"]
        assert fields["DbId"] == item["values"]["database_id"]
        assert fields["Klien"] == fields["DbId"]  # optional name is supported
        item["values"].update(client_id=result["client_id"], previous_license=str(path), capacity="42")
        item["overwrite"] = True
    renewed = batch_license.generate_all(original_forms, tmp_path)
    assert len(list(tmp_path.iterdir())) == 3
    for item in original_forms:
        key = item["product"]
        result = renewed["results"][key]
        assert result["client_id"] == new["results"][key]["client_id"]
        assert result["previous_sequence"] == 1 and result["sequence"] == 2
        assert result["mode"] == "renewal"
        assert BACKENDS[key].verify_license(result["path"], item["values"]["database_id"],
                                          item["values"]["system_id"], result["client_id"],
                                          for_import=True)["valid"] is True


@pytest.mark.parametrize("field,value", [
    ("database_id", ""), ("database_id", "ABCD_"), ("system_id", "G1234"),
    ("expires", "2030-2-02"), ("expires", "2030-02-30"), ("expires", "2000-01-01"),
    ("capacity", ""), ("capacity", "0"), ("capacity", "2147483648"), ("capacity", "2.5"),
    ("client_id", "EXISTING-CLIENT"),
])
def test_invalid_final_form_never_writes_outputs(tmp_path, field, value):
    snapshots = forms()
    snapshots[-1]["values"][field] = value
    with pytest.raises(ValueError, match="CBE Server") as caught:
        batch_license.generate_all(snapshots, tmp_path)
    assert caught.value.product == "cbe"
    assert list(tmp_path.iterdir()) == []


def test_preflight_collects_product_errors_and_does_not_mutate_forms():
    snapshots = forms()
    snapshots[0]["values"]["database_id"] = ""
    snapshots[2]["values"]["capacity"] = "0"
    before = deepcopy(snapshots)
    with pytest.raises(ValueError) as caught:
        batch_license.preflight_forms(snapshots)
    assert "Absensi Wajah" in str(caught.value) and "CBE Server" in str(caught.value)
    assert snapshots == before


def test_missing_old_file_is_rejected_before_generation(tmp_path):
    snapshots = forms()
    snapshots[2]["values"].update(client_id="OLD", previous_license=str(tmp_path / "missing.lic"))
    with pytest.raises(ValueError, match="lisensi lama"):
        batch_license.generate_all(snapshots, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_existing_final_target_blocks_all_products_before_codecs_run(tmp_path):
    snapshots = forms()
    existing = tmp_path / snapshots[-1]["filename"]
    existing.write_bytes(b"keep existing third product")
    def unexpected(**kwargs):
        pytest.fail("codec ran before checking every destination")
    backends = {key: SimpleNamespace(generate_license=unexpected) for key in BACKENDS}
    with pytest.raises(ValueError, match="CBE Server.*overwrite"):
        batch_license.generate_all(snapshots, tmp_path, backends)
    assert list(tmp_path.iterdir()) == [existing]
    assert existing.read_bytes() == b"keep existing third product"


@pytest.mark.parametrize("failure", ["exception", "verification"])
def test_failure_staging_final_product_leaves_no_partial_outputs(tmp_path, failure):
    def failed(**kwargs):
        if failure == "exception":
            raise ValueError("simulated codec failure")
        result = cbe_codec.generate_license(**kwargs)
        result["verification"]["valid"] = False
        return result
    backends = dict(BACKENDS, cbe=SimpleNamespace(generate_license=failed))
    with pytest.raises(ValueError, match="CBE Server"):
        batch_license.generate_all(forms(), tmp_path, backends)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("existing", [False, True])
def test_mid_commit_failure_restores_original_set(tmp_path, monkeypatch, existing):
    snapshots = forms()
    originals = {}
    if existing:
        for item in snapshots:
            item["overwrite"] = True
            target = tmp_path / item["filename"]
            originals[target] = f"original {item['product']}".encode()
            target.write_bytes(originals[target])
    real_replace = os.replace
    def fail_third_install(source, destination):
        if Path(source).name == "cbe-server.lic":
            raise OSError("simulated replace failure")
        return real_replace(source, destination)
    monkeypatch.setattr(batch_license.os, "replace", fail_third_install)
    with pytest.raises(ValueError, match="dipulihkan") as caught:
        batch_license.generate_all(snapshots, tmp_path)
    assert caught.value.product == "cbe"
    assert {path: path.read_bytes() for path in tmp_path.iterdir()} == originals


def test_wrong_renewal_client_id_preserves_every_old_license(tmp_path):
    snapshots = forms()
    initial = batch_license.generate_all(snapshots, tmp_path)
    originals = {p: p.read_bytes() for p in tmp_path.iterdir()}
    for item in snapshots:
        key = item["product"]
        item["overwrite"] = True
        item["values"].update(previous_license=initial["paths"][key],
                               client_id=initial["results"][key]["client_id"])
    snapshots[-1]["values"]["client_id"] = "DIFFERENT-CLIENT"
    with pytest.raises(ValueError, match="CBE Server.*Client ID berbeda"):
        batch_license.generate_all(snapshots, tmp_path)
    assert {p: p.read_bytes() for p in tmp_path.iterdir()} == originals


def test_output_names_cannot_alias_or_escape_selected_folder(tmp_path):
    snapshots = forms()
    snapshots[-1]["filename"] = snapshots[0]["filename"].upper()
    with pytest.raises(ValueError, match="sama dengan produk lain"):
        batch_license.generate_all(snapshots, tmp_path)
    snapshots[-1]["filename"] = "../escape.lic"
    with pytest.raises(ValueError, match="nama berkas"):
        batch_license.generate_all(snapshots, tmp_path)
    assert list(tmp_path.iterdir()) == []
