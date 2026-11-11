"""Explicit product capabilities: unrelated identity fields are never aliased."""
from dataclasses import dataclass

SHARED_FIELDS = ('system_id', 'client_id', 'client_name', 'expires', 'capacity')


@dataclass(frozen=True)
class Product:
    key: str
    label: str
    subtitle: str
    codec_module: str
    capacity_label: str
    initial_file: str
    kind: str = 'standard'

    @property
    def supports_renewal(self):
        return self.kind in ('standard', 'sjs')

    @property
    def fields(self):
        """Rows of (key, label); a singleton row spans the available width."""
        if self.kind == 'fingerprint':
            return ((('scanner_serial', 'Nomor seri scanner'), ('license_scope', 'Tujuan lisensi')),
                    (('client_name', 'Nama klien'),))
        if self.kind == 'letterstore':
            return ((('database_id', 'Database ID'), ('client_name', 'Nama klien')),)
        if self.kind == 'sjs':
            return ((('database_id', 'Database ID'), ('school_id', 'School ID')),
                    (('registration_token', 'Registration Token'),),
                    (('client_name', 'Nama sekolah'), ('expires', 'Berlaku sampai')),
                    (('capacity', self.capacity_label),))
        return ((('database_id', 'Database ID'), ('system_id', 'System ID')),
                (('client_id', 'Client ID'), ('client_name', 'Nama klien')),
                (('expires', 'Berlaku sampai'), ('capacity', self.capacity_label)))

    @property
    def input_keys(self):
        return tuple(key for row in self.fields for key, _label in row)

    @property
    def hint(self):
        if self.kind == 'fingerprint':
            return 'Lisensi Finger memakai nomor seri scanner, bukan Database ID atau System ID.'
        if self.kind == 'letterstore':
            return 'LetterStore memakai Database ID; tidak menggunakan System ID atau Sequence.'
        if self.kind == 'sjs':
            return 'SJS memakai Registration Token. School ID wajib untuk baru, atau diambil dari lisensi lama.'
        return 'Perpanjangan: pilih lisensi lama; Client ID dipertahankan, urutan naik otomatis.'


PRODUCTS = (
    Product('face', 'Absensi Wajah', 'Face Server16.5 / Client FACE16.10',
            'license_codec', 'Kapasitas wajah', 'absensi-wajah.lic'),
    Product('fingerprint', 'Absensi Finger', 'Fingerprint Manager16.5 / Client14.0',
            'fingerprint_codec', '', 'absensi-finger.lic', 'fingerprint'),
    Product('schoolpay', 'SchoolPay', 'SchoolPay Secure Server10.5',
            'schoolpay_codec', 'Kapasitas vendor', 'schoolpay.lic'),
    Product('cbe', 'CBE Server', 'CBE Server26.5',
            'cbe_codec', 'Kapasitas klien', 'cbe-server.lic'),
    Product('sjs', 'SJS', 'Sinkronisasi Jendela Sekolah7.10',
            'sjs_codec', 'Maks. agent', 'sjs.lic', 'sjs'),
    Product('letterstore', 'LetterStore', 'Letter Store7.0',
            'letterstore_codec', '', 'letterstore.lic', 'letterstore'),
)
PRODUCT_BY_KEY = {product.key: product for product in PRODUCTS}


def get_product(key):
    return PRODUCT_BY_KEY[key]
