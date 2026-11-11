"""Render owned Tk windows with synthetic inputs; never call a product backend."""
from __future__ import annotations

from itertools import combinations
import json
from pathlib import Path
import sys
import tkinter as tk
from tkinter import ttk

from PIL import ImageGrab


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
import app


DATABASE_IDS = {"face": "V4YNE", "schoolpay": "7VJM4", "cbe": "ABCDE"}
SHARED = {
    "system_id": "DDCB4", "client_id": "", "client_name": "Contoh Sekolah",
    "expires": "2030-12-31", "capacity": "100",
}
SCENES = [(key, size) for size in ("880x650", "760x560") for key in DATABASE_IDS]
reports = []
errors = []


window = tk.Tk()
application = app.LicenseApp(window)
window.title("JIBAS - Generator Lisensi - Visual QA")
window.attributes("-topmost", True)
for name, value in SHARED.items():
    application.panels["face"].inputs[name].set(value)
for key, dbid in DATABASE_IDS.items():
    panel = application.panels[key]
    panel.inputs["database_id"].set(dbid)
    panel.show_result({
        "contoh_tampilan": True, "produk": panel.product.label,
        "catatan": "Data sintetis; tanpa koneksi database atau aktivasi.",
        "pemeriksaan": [{"nama": f"Contoh pemeriksaan {i}", "hasil": "contoh"}
                        for i in range(12)],
    })


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


def rectangle(widget):
    return [widget.winfo_rootx() - window.winfo_rootx(),
            widget.winfo_rooty() - window.winfo_rooty(),
            widget.winfo_width(), widget.winfo_height()]


def label(widget):
    text = widget.cget("text") if "text" in widget.keys() else ""
    return {"widget": str(widget), "class": widget.winfo_class(),
            "text": text, "bounds": rectangle(widget),
            "requested": [widget.winfo_reqwidth(), widget.winfo_reqheight()]}


def capture(key, size):
    panel = application.panels[key]
    x, y = window.winfo_rootx(), window.winfo_rooty()
    width, height = window.winfo_width(), window.winfo_height()
    ImageGrab.grab(bbox=(x, y, x + width, y + height)).save(HERE / f"gui_{key}_{size}.png")
    mapped = [widget for widget in descendants(application) if widget.winfo_ismapped()]
    clipped = []
    for widget in mapped:
        left, top, w, h = rectangle(widget)
        if left < 0 or top < 0 or left + w > width or top + h > height:
            clipped.append(label(widget))
    labels_buttons = [widget for widget in mapped if isinstance(widget, (ttk.Label, ttk.Button, ttk.Checkbutton))]
    compressed_labels = [label(widget) for widget in labels_buttons
                         if widget.winfo_width() < widget.winfo_reqwidth()
                         or widget.winfo_height() < widget.winfo_reqheight()]
    leaves = [widget for widget in mapped if not widget.winfo_children()]
    overlaps = []
    for first, second in combinations(leaves, 2):
        ax, ay, aw, ah = rectangle(first)
        bx, by, bw, bh = rectangle(second)
        if min(ax + aw, bx + bw) > max(ax, bx) and min(ay + ah, by + bh) > max(ay, by):
            overlaps.append([label(first), label(second)])
    save_all = panel.save_all_button
    generate = panel.generate_button
    save_x, save_y, save_w, save_h = rectangle(save_all)
    gen_x, gen_y, gen_w, gen_h = rectangle(generate)
    immediately_left = save_x + save_w <= gen_x and save_y == gen_y and gen_x - (save_x + save_w) <= 12
    shared_identity = {name: all(application.panels[other].inputs[name] is panel.inputs[name]
                                 for other in DATABASE_IDS) for name in SHARED}
    shared_values = {name: {other: application.panels[other].inputs[name].get()
                            for other in DATABASE_IDS} for name in SHARED}
    report = {
        "product": key, "size": [width, height],
        "clipped_widgets": clipped, "compressed_labels_or_buttons": compressed_labels,
        "overlapping_leaf_widgets": overlaps,
        "save_all": label(save_all), "generate": label(generate),
        "save_all_immediately_left_of_generate": immediately_left,
        "result_lines": int(panel.output.cget("height")),
        "result_pixels": panel.output.winfo_height(),
        "result_scroll_range": list(panel.output.yview()),
        "shared_variable_identity": shared_identity, "shared_values": shared_values,
        "database_ids": {other: application.panels[other].inputs["database_id"].get()
                         for other in DATABASE_IDS},
        "database_id_variables_distinct": len({id(application.panels[other].inputs["database_id"])
                                              for other in DATABASE_IDS}) == 3,
        "sequence_input": "sequence" in panel.inputs,
        "source": "Owned Tk QA window; synthetic values; exact client-region capture; no backend calls",
    }
    (HERE / f"gui_layout_{key}_{size}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    reports.append(report)
    for passed, reason in (
        (not clipped, "widgets leave window bounds"),
        (not compressed_labels, "labels or buttons are compressed"),
        (not overlaps, "leaf widgets overlap"),
        (immediately_left, "Save All is not immediately left of Buat & simpan"),
        (report["result_lines"] == 6, "results do not have six lines"),
        (all(shared_identity.values()), "shared fields use separate variables"),
        (all(set(values.values()) == {SHARED[name]} for name, values in shared_values.items()),
         "shared field values do not match"),
        (report["database_ids"] == DATABASE_IDS, "database IDs were overwritten"),
        (report["database_id_variables_distinct"], "database ID variables are shared"),
    ):
        if not passed:
            errors.append(f"{key} at {size}: {reason}")


def finish():
    if len({report["result_pixels"] for report in reports}) != 1:
        errors.append("Output height changed across products or window sizes")
    result = {"scenes": len(reports), "passed": not errors, "errors": errors,
              "output_pixels": sorted({report["result_pixels"] for report in reports}),
              "screenshots": [f"gui_{key}_{size}.png" for key, size in SCENES],
              "synthetic_values": {"shared": SHARED, "database_ids": DATABASE_IDS}}
    (HERE / "gui_visual_report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    application.close()


def next_scene(index=0):
    if index >= len(SCENES):
        finish()
        return
    key, size = SCENES[index]
    window.geometry(f"{size}+20+0")
    application.notebook.select(application.panels[key])
    window.lift()
    window.after(250, lambda: (capture(key, size), window.after(100, lambda: next_scene(index + 1))))


window.after(300, next_scene)
window.mainloop()
if errors:
    raise SystemExit(1)
