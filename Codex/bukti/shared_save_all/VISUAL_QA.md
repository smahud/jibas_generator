# Shared fields and Save All: visual QA

Checked 2026-11-11 with one owned Tk interpreter. The probe only constructs the
GUI and inserts synthetic inputs/results; it never invokes a product backend.
Pillow captures exactly the application's client area.

All six screenshots were inspected: FACE, SchoolPay, and CBE at both 880x650 and
the minimum 760x560. Every case passed the geometry checks in the matching
`gui_layout_*.json` and the summary `gui_visual_report.json`.

- Save All is immediately left of Buat & simpan…, on the same row with a 6px gap.
- No mapped widget exceeds the client bounds; no leaf controls overlap.
- All labels and buttons retain at least their requested width and height.
- The results area is six text lines and 102px high in every scene, with a
  scrollbar for the long synthetic result.
- All five common inputs reference the same StringVar objects across tabs:
  System ID, Client ID, Nama klien, Berlaku sampai, and capacity.
- Database ID variables remain distinct: FACE `V4YNE`, SchoolPay `7VJM4`,
  CBE `ABCDE`.

The common values are System ID `DDCB4`, blank Client ID, Nama klien
`Contoh Sekolah`, date `2030-12-31`, and capacity `100`. No database or live
JIBAS data was read or written.

Reproduce with Python 3.12, Tk, and Pillow by running `gui_visual_probe.py`.
The QA run used Pillow from a task-specific dependency directory under TEMP;
Pillow is not an application runtime dependency.
