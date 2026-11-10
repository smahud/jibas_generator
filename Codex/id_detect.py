"""Automatic Database ID / System ID detection for JIBAS Face Server 16.5.

Database ID (proven):
  FaceServer.exe method 0x06000AC3 builds it live from the jbssat database:

    DbId = UPPER(
        hex_decode(@uhh)[14] +   # @uhh = OUT parameter index 7 dari jbssat.splang04
        hex_decode(@uhf)[5]  +   # @uhf = OUT parameter index 5 dari jbssat.splang02
        hex_decode(@uhc)[25] +   # @uhc = OUT parameter index 2 dari jbssat.splang09
        hex_decode(@uhe)[37] +   # @uhe = OUT parameter index 4 dari jbssat.splang11
        hex_decode(@uhb)[47])    # @uhb = OUT parameter index 1 dari jbssat.splang01

  Urutan kerja metode asli: "USE jbssat", tolak bila skema kosong, verifikasi
  12 prosedur splang lewat information_schema.ROUTINES, lalu jalankan tiap
  prosedur dengan 9 keluaran (@uha..@uhi) dan dekode payload hex ASCII-nya.

System ID (proven on this machine):
  FaceServer.exe 0x0600059B:
    serial = Win32_PhysicalMedia.SerialNumber of the physical drive holding C:\
    uuid   = Win32_ComputerSystemProduct.UUID
    SystemId = MD5_ASCII(serial + uuid) lowercase hex, chars [5,17,30,24,3], upper.

IMPORTANT: preserve every trailing space of the physical-media serial number.
The original 0x06000599 returns WMI's raw string with no Trim call. On this
host it is '30029941042         ', producing DDCB4, not the old detector's
7738F. See bukti/id_audit/ for fresh original-method execution evidence.
"""
from __future__ import annotations

import binascii
import hashlib
import os
import re
import subprocess


class DetectError(ValueError):
    pass


def database_password(explicit=None) -> str:
    """Read a caller-supplied credential without storing it in source code."""
    password = explicit if explicit is not None else os.environ.get("JIBAS_DB_PASSWORD")
    if password is None:
        raise DetectError("Credential database belum tersedia. Atur environment "
                          "JIBAS_DB_PASSWORD melalui pengelola credential lokal.")
    return password


def _safe_database_error(exc: Exception, password: str) -> str:
    """Do not propagate a connector error containing the supplied secret."""
    detail = str(exc)
    return detail.replace(password, "[REDACTED]") if password else detail


DB_RECIPE = [
    # (procedure, output_parameter_index, substring_position)
    (4, 7, 14),
    (2, 5, 5),
    (9, 2, 25),
    (11, 4, 37),
    (1, 1, 47),
]
SPLANG_PROCEDURES = [f"splang{i:02d}" for i in range(1, 13)]


def _hex_to_ascii(hex_text: str) -> str:
    text = (hex_text or "").strip()
    if len(text) % 2 != 0 or not re.fullmatch(r"[0-9A-Fa-f]{4,}", text or ""):
        raise DetectError("Nilai hex variabel splang tidak valid.")
    try:
        return binascii.unhexlify(text).decode("ascii")
    except (binascii.Error, UnicodeError) as exc:
        raise DetectError(f"Payload splang bukan teks ASCII heksadesimal: {exc}") from exc


class DbIdDetector:
    """Reads an existing Database ID using original 0x06000AC3's recipe.

    Unlike the application's bootstrap branch, this detector never creates
    missing routines. It fails with DetectError if they are unavailable.
    """

    def __init__(self, host="127.0.0.1", port=3434, user="root", password=None,
                 database="jbssat"):
        self.host, self.port, self.user, self.password = host, port, user, password
        self.database = database

    def _connect(self):
        password = database_password(self.password)
        try:
            import pymysql
        except ImportError as exc:
            raise DetectError(
                "Modul pymysql tidak tersedia. Install dengan: python -m pip install pymysql") from exc
        try:
            return pymysql.connect(host=self.host, port=self.port, user=self.user,
                                   password=password, database=self.database,
                                   charset="utf8mb4", connect_timeout=10)
        except Exception as exc:
            raise DetectError(f"Tidak dapat terhubung MySQL {self.host}:{self.port}: "
                              + _safe_database_error(exc, password)) from None

    def verify_procedures(self, conn) -> dict:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT specific_name FROM information_schema.ROUTINES "
            "WHERE routine_schema = %s AND routine_type = 'PROCEDURE'",
            (self.database,))
        existing = {row[0] for row in cursor.fetchall()}
        missing = [name for name in SPLANG_PROCEDURES if name not in existing]
        return {"present": sorted(existing), "missing": missing}

    def detect(self) -> tuple[str, dict]:
        conn = self._connect()
        try:
            cursor = conn.cursor()
            info = self.verify_procedures(conn)
            if info["missing"]:
                raise DetectError(
                    "Prosedur splang hilang: " + ", ".join(info["missing"]))
            pieces = []
            variables = []
            for proc, index, position in DB_RECIPE:
                var = "@uh" + "abcdefghi"[index]
                names = [f"@uh{c}" for c in "abcdefghi"]
                cursor.execute(
                    f"CALL `{self.database}`.splang{proc:02d}({', '.join(names)})")
                cursor.execute(f"SELECT {', '.join(names)}")
                row = cursor.fetchone()
                if not row or row[index] is None:
                    raise DetectError(f"Nilai keluaran {var} splang{proc:02d} kosong.")
                decoded = _hex_to_ascii(row[index])
                if position >= len(decoded):
                    raise DetectError(
                        f"Posisi {position} di luar payload splang{proc:02d} {var}.")
                character = decoded[position]
                pieces.append(character)
                variables.append({
                    "procedure": f"splang{proc:02d}", "variable": var,
                    "position": position, "character": character,
                })
        except DetectError:
            raise
        except Exception as exc:
            raise DetectError("Pemeriksaan Database ID gagal: "
                              + _safe_database_error(exc, database_password(self.password))) from None
        finally:
            conn.close()
        db_id = "".join(pieces).upper()
        return db_id, {"method": "jbssat splang procedure recipe (original 0x06000AC3)",
                       "pieces": variables, "connection": f"{self.host}:{self.port}/{self.database}"}


class SystemIdDetector:
    """Reads the System ID like original 0x06000599 + 0x0600059A + 0x0600059B.

    Uses PowerShell WMI, preserving the original raw serial number, then
    reproduces the original .NET ASCII/MD5 operation in Python.
    """

    WMI_DISK_QUERY = "select * from Win32_DiskDrive where InterfaceType='SCSI' or InterfaceType='IDE'"

    def __init__(self, disk_serial=None, cs_uuid=None):
        self._disk_serial, self._cs_uuid = disk_serial, cs_uuid

    def read_wmi(self) -> tuple[str, str]:
        script = r"""
$ErrorActionPreference = 'SilentlyContinue'
$drives = Get-WmiObject -Query "select * from Win32_DiskDrive where InterfaceType='SCSI' or InterfaceType='IDE'"
$media = @(Get-WmiObject -Query "SELECT Tag, SerialNumber FROM Win32_PhysicalMedia")
$csp = @(Get-WmiObject -Query 'SELECT UUID FROM Win32_ComputerSystemProduct')
foreach ($drive in $drives) {
  $devId = $drive.DeviceID
  $parts = @(Get-WmiObject -Query ("ASSOCIATORS OF {Win32_DiskDrive.DeviceID='" + $devId + "'} WHERE AssocClass = Win32_DiskDriveToDiskPartition"))
  foreach ($part in $parts) {
    $logicals = @(Get-WmiObject -Query ("ASSOCIATORS OF {Win32_DiskPartition.DeviceID='" + $part.DeviceID + "'} WHERE AssocClass = Win32_LogicalDiskToPartition"))
    foreach ($logical in $logicals) {
      if ($logical.DeviceID -eq 'C:') {
        $match = @($media | Where-Object { ('' + $_.Tag) -eq $devId })
        if ($match.Count -gt 0) {
          $raw = '' + $match[0].SerialNumber
          Write-Output ('DISK ' + $raw)
          if ($csp.Count -gt 0) { Write-Output ('UUID ' + ('' + $csp[0].UUID)) }
          exit 0
        }
      }
    }
  }
}
Write-Output 'DISK NOT FOUND'
exit 0
"""
        try:
            completed = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace")
        except subprocess.TimeoutExpired as exc:
            raise DetectError("Pemeriksaan WMI melewati batas waktu 60 detik.") from exc
        except OSError as exc:
            raise DetectError(f"PowerShell tidak dapat dijalankan: {exc}") from exc
        if completed.returncode != 0:
            raise DetectError(f"Pemeriksaan WMI gagal (PowerShell exit {completed.returncode}).")
        disk, cs_uuid = "", ""
        for line in (completed.stdout or "").splitlines():
            if line.startswith("DISK "):
                disk = line[5:]
            elif line.startswith("UUID "):
                cs_uuid = line[5:]
        if not disk or disk == "NOT FOUND":
            raise DetectError("Serial fisik disk C: tidak ditemukan lewat WMI.")
        return disk, cs_uuid

    # ---------- hashing ----------
    @staticmethod
    def _md5_hex(ascii_input: str) -> str:
        # Encoding.ASCII.GetBytes uses '?' for each non-ASCII UTF-16 code
        # unit. Do not normalize, strip, or change case before hashing.
        units = ascii_input.encode("utf-16le", errors="surrogatepass")
        raw = bytes(units[i] if units[i + 1] == 0 and units[i] < 128 else 63
                    for i in range(0, len(units), 2))
        return hashlib.md5(raw).hexdigest().lower()

    @classmethod
    def compute(cls, disk_serial: str, cs_uuid: str) -> str:
        digest = cls._md5_hex((disk_serial or "") + (cs_uuid or ""))
        return "".join(digest[i] for i in (5, 17, 30, 24, 3)).upper()

    def detect(self) -> tuple[str, dict]:
        if self._disk_serial is None or self._cs_uuid is None:
            disk, cs_uuid = self.read_wmi()
        else:
            disk, cs_uuid = self._disk_serial, self._cs_uuid
        try:
            system_id = self.compute(disk, cs_uuid)
        except UnicodeError as exc:
            raise DetectError(f"Nilai hardware mengandung karakter non-ASCII: {exc}") from exc
        return system_id, {
            "disk_serial_raw": disk, "csproduct_uuid": cs_uuid,
            "algorithm": "MD5(disk_serial + csproduct_uuid) hex[5,17,30,24,3].upper()",
        }
