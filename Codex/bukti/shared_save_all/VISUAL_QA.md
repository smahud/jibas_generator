# Six products, shared fields and Save All: visual QA

Checked 2026-11-11 using primary Python 3.12 and one owned Tk interpreter.
The probe constructs the GUI and inserts synthetic inputs/results without
invoking any product backend. All **12 scenes pass**: Absensi Wajah, Absensi
Finger, SchoolPay, CBE Server, SJS, and LetterStore at 880x650 and minimum
760x560. Evidence is in `gui_layout_*.json`, `gui_*.png`, and
`gui_visual_report.json`.

An earlier run could not capture the desktop, so the probe now supports
Windows `PrintWindow` for its own QA window. The final 12 images all used
successful desktop client-region capture; each image was checked for rendered
content. Both sizes were visually reviewed, including the four-row SJS form
and its bottom controls.

- No mapped widget exceeds the client bounds; no leaf controls overlap.
- Labels and buttons retain their requested dimensions. Unwrapped label text
  also fits according to its actual font metrics; the scanner-serial and
  Registration Token labels now display completely.
- SJS's four input rows, previous-file picker, output, actions, progress bar,
  and status fit at 760x560.
- Save All is immediately left of Buat & simpan…, on the same row with a 6px gap.
- Results remain six text lines and 102px high in every scene, with a scrollbar
  for the long synthetic result.
- Shared-field identity and values are checked only for products that expose
  that field. Nama klien is shared across all six; expiry and capacity across
  Wajah/SchoolPay/CBE/SJS; System ID and Client ID across Wajah/SchoolPay/CBE.
- All five Database ID variables remain distinct: FACE `V4YNE`, SchoolPay
  `7VJM4`, CBE `ABCDE`, SJS `SJS12`, LetterStore `LS123`.
- Finger has scanner serial `SCANNER-QA-001` and Manager + Client scope.
  SJS retains separate School ID `SCHOOL-QA-001` and token
  `REGISTRATION-TOKEN-QA-001`. All relevant input controls are visible; no
  Sequence input is exposed.

Common synthetic values: System ID `DDCB4`, blank Client ID, name
`Contoh Sekolah`, date `2030-12-31`, and capacity `100`. No database or live
JIBAS data was read or written.

Reproduce from `Codex` with Python 3.12, Tk, and Pillow:

```powershell
$env:PYTHONPATH = Join-Path $env:TEMP 'jibas-shared-qa-deps'
python bukti/shared_save_all/gui_visual_probe.py
```

Pillow was already available in that task-specific TEMP directory. It is not
an application runtime dependency. The probe closes its owned window on
completion or callback failure.
