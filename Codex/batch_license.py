"""Validate manual license forms and save their outputs as one transaction.

Only the chosen output directory is written. Product codecs continue to own
license formats, renewal rules, sequence selection, and offline verification.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib
import os
from pathlib import Path
import re
import shutil
import tempfile
from product_actions import product_for, normalize_values, generate_with_backend


JAKARTA = timezone(timedelta(hours=7))


class BatchLicenseError(ValueError):
    """A user-facing batch error, optionally associated with one product."""

    def __init__(self, message, *, product=None, errors=()):
        super().__init__(message)
        self.product = product
        self.errors = tuple(errors)


def _validate_form(form):
    item = dict(form)
    product = str(item.get("product", "")).strip()
    if not product:
        raise ValueError("Produk tidak tersedia.")
    item["product"] = product
    item["label"] = str(item.get("label") or product)
    if not item.get("codec_module"):
        raise ValueError("Modul lisensi tidak tersedia.")
    filename = str(item.get("filename", ""))
    if (not filename or filename in (".", "..") or
            re.search(r'[<>:"/\\|?*\x00-\x1f]', filename) or
            filename.endswith((".", " "))):
        raise ValueError("Nama berkas keluaran harus berupa satu nama berkas yang valid.")
    item["filename"] = filename
    if not isinstance(item.get("overwrite", False), bool):
        raise ValueError("Pilihan overwrite tidak valid.")
    item["overwrite"] = item.get("overwrite", False)
    item["values"] = normalize_values(product_for(product), item.get("values") or {})
    return item


def preflight_forms(forms):
    """Return independent normalized forms; read files only, never write them.

    Every product is checked before raising, so a bad final tab cannot let the
    earlier products reach generation. Destination paths are chosen separately.
    """
    normalized, errors = [], []
    products, filenames = set(), set()
    for form in forms:
        product = form.get("product")
        label = form.get("label") or product or "Produk"
        try:
            item = _validate_form(form)
            if item["product"] in products:
                raise ValueError("Produk tercantum lebih dari sekali.")
            if item["filename"].casefold() in filenames:
                raise ValueError("Nama berkas keluaran sama dengan produk lain.")
            products.add(item["product"])
            filenames.add(item["filename"].casefold())
            normalized.append(item)
        except (ValueError, TypeError, OSError) as exc:
            errors.append((product, f"{label}: {exc}"))
    if errors:
        raise BatchLicenseError("\n".join(detail for _, detail in errors),
                                product=errors[0][0], errors=errors)
    if not normalized:
        raise BatchLicenseError("Tidak ada formulir lisensi untuk disimpan.")
    return normalized


def _targets(forms, output_dir):
    targets = {}
    for item in forms:
        target = output_dir / item["filename"]
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise BatchLicenseError(f"{item['label']}: Tujuan bukan berkas keluaran biasa: {target}",
                                    product=item["product"])
        if target.exists() and not item["overwrite"]:
            raise BatchLicenseError(f"{item['label']}: Berkas keluaran sudah ada; aktifkan overwrite: {target}",
                                    product=item["product"])
        for earlier in targets.values():
            if target.exists() and earlier.exists() and os.path.samefile(target, earlier):
                raise BatchLicenseError(f"{item['label']}: Berkas keluaran sama dengan produk lain.",
                                        product=item["product"])
        targets[item["product"]] = target
    return targets


def generate_all(forms, output_dir, backends=None):
    """Generate and verify everything in staging, then commit or roll back all.

    The GUI supplies one existing folder and product filenames. The individual
    form's ``file`` field is deliberately ignored for destination selection.
    """
    forms = preflight_forms(forms)
    output_dir = Path(output_dir).resolve()
    if not output_dir.is_dir():
        raise BatchLicenseError(f"Folder keluaran tidak ditemukan: {output_dir}")
    targets = _targets(forms, output_dir)  # Check every target before any write.
    stage = Path(tempfile.mkdtemp(prefix=".jibas-save-all-", dir=output_dir))
    cleanup = True
    try:
        staged_outputs = stage / "outputs"
        staged_outputs.mkdir()
        backup_dir = stage / "backups"
        results = {}
        for item in forms:
            key, values = item["product"], item["values"]
            try:
                backend = (backends or {}).get(key)
                if backend is None:
                    backend = importlib.import_module(item["codec_module"])
                result = generate_with_backend(backend, product_for(key), values,
                    staged_outputs / item["filename"], overwrite=False)
                if not (staged_outputs / item["filename"]).is_file():
                    raise ValueError("Codec tidak menghasilkan berkas lisensi.")
                if result.get("verification", {}).get("valid") is not True:
                    raise ValueError("Verifikasi berkas lisensi gagal; tidak ada keluaran yang disimpan.")
                results[key] = dict(result, path=str(targets[key]))
            except Exception as exc:
                raise BatchLicenseError(f"{item['label']}: {exc}", product=key) from exc
        # A file may have appeared while the codecs worked. Check the whole set
        # again before taking backups or replacing any destination.
        targets = _targets(forms, output_dir)
        backups = {}
        for index, (key, target) in enumerate(targets.items()):
            if target.exists():
                backup_dir.mkdir(exist_ok=True)
                backup = backup_dir / str(index)
                shutil.copy2(target, backup)
                backups[key] = backup
        installed = []
        try:
            for item in forms:
                key = item["product"]
                os.replace(staged_outputs / item["filename"], targets[key])
                installed.append(key)
        except Exception as exc:
            failed_product = key
            rollback_errors = []
            for key in reversed(installed):
                try:
                    if key in backups:
                        try:
                            os.replace(backups[key], targets[key])
                        except OSError:
                            shutil.copy2(backups[key], targets[key])
                    else:
                        targets[key].unlink()
                except OSError as rollback_exc:
                    rollback_errors.append(str(rollback_exc))
            detail = f"Gagal menyimpan semua lisensi; keluaran dipulihkan: {exc}"
            if rollback_errors:
                cleanup = False  # Preserve backups for recovery if the OS denies restoration.
                detail = f"Gagal memulihkan keluaran: {'; '.join(rollback_errors)}. Cadangan: {stage}"
            raise BatchLicenseError(detail, product=failed_product) from exc
        return {"ok": True, "results": results,
                "paths": {key: str(path) for key, path in targets.items()}}
    except BatchLicenseError:
        raise
    except Exception as exc:
        raise BatchLicenseError(f"Gagal menyimpan semua lisensi: {exc}") from exc
    finally:
        if cleanup:
            shutil.rmtree(stage)
