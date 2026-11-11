"""Render owned Tk windows with synthetic inputs; never call a product backend."""
from __future__ import annotations

from itertools import combinations
import json
from pathlib import Path
import sys
import tkinter as tk
from tkinter import font as tkfont, ttk

from PIL import Image, ImageGrab


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
import app


DATABASE_IDS = {"face": "V4YNE", "schoolpay": "7VJM4", "cbe": "ABCDE",
                "sjs": "SJS12", "letterstore": "LS123"}
PRODUCT_KEYS = tuple(product.key for product in app.PRODUCTS)
PRODUCT_INPUTS = {
    "fingerprint": {"scanner_serial": "SCANNER-QA-001", "license_scope": "Manager + Client"},
    "sjs": {"school_id": "SCHOOL-QA-001", "registration_token": "REGISTRATION-TOKEN-QA-001"},
}
SHARED = {
    "system_id": "DDCB4", "client_id": "", "client_name": "Contoh Sekolah",
    "expires": "2030-12-31", "capacity": "100",
}
SCENES = [(key, size) for size in ("880x650", "760x560") for key in PRODUCT_KEYS]
reports = []
errors = []


window = tk.Tk()
application = app.LicenseApp(window)


def callback_failed(kind, value, traceback):
    import traceback as traceback_module
    traceback_module.print_exception(kind, value, traceback)
    errors.append("QA callback failed: " + str(value))
    application.close()


window.report_callback_exception = callback_failed
window.title("JIBAS - Generator Lisensi - Visual QA")
window.attributes("-topmost", True)
for name, value in SHARED.items():
    application.panels["face"].inputs[name].set(value)
for key in PRODUCT_KEYS:
    panel = application.panels[key]
    if key in DATABASE_IDS:
        panel.inputs["database_id"].set(DATABASE_IDS[key])
    for name, value in PRODUCT_INPUTS.get(key, {}).items():
        panel.inputs[name].set(value)
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


def capture_owned_window(width, height):
    """Use WM_PRINT for this QA window when the desktop cannot be captured."""
    import ctypes
    from ctypes import wintypes
    user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
    user32.GetDC.argtypes = [wintypes.HWND]
    user32.GetDC.restype = wintypes.HDC
    user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
    gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi32.CreateCompatibleDC.restype = wintypes.HDC
    gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
    gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
    gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
    gdi32.SelectObject.restype = wintypes.HGDIOBJ
    gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi32.DeleteDC.argtypes = [wintypes.HDC]
    gdi32.GetDIBits.argtypes = [wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT,
                              ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT]
    hwnd = int(window.frame(), 0)
    source = user32.GetDC(hwnd)
    memory = gdi32.CreateCompatibleDC(source)
    bitmap = gdi32.CreateCompatibleBitmap(source, width, height)
    old = gdi32.SelectObject(memory, bitmap)
    try:
        if not user32.PrintWindow(hwnd, memory, 3):
            raise OSError("PrintWindow failed")
        header = (ctypes.c_uint32 * 10)(40, width, (-height) & 0xffffffff,
                                        1 | (32 << 16), 0, width * height * 4, 0, 0, 0, 0)
        pixels = ctypes.create_string_buffer(width * height * 4)
        if not gdi32.GetDIBits(memory, bitmap, 0, height, pixels, header, 0):
            raise OSError("GetDIBits failed")
        return Image.frombuffer("RGB", (width, height), pixels.raw, "raw", "BGRX", 0, 1).copy()
    finally:
        gdi32.SelectObject(memory, old)
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(memory)
        user32.ReleaseDC(hwnd, source)


def capture(key, size):
    panel = application.panels[key]
    x, y = window.winfo_rootx(), window.winfo_rooty()
    width, height = window.winfo_width(), window.winfo_height()
    capture_mode = "desktop_client_region"
    screenshot_error = None
    try:
        try:
            picture = ImageGrab.grab(bbox=(x, y, x + width, y + height))
        except OSError:
            capture_mode = "owned_window_PrintWindow"
            picture = capture_owned_window(width, height)
        if all(low == high for low, high in picture.getextrema()):
            raise OSError("Window capture is uniform; it does not establish rendered controls")
        picture.save(HERE / f"gui_{key}_{size}.png")
    except OSError as exc:
        screenshot_error = str(exc)
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
    clipped_label_text = []
    style = ttk.Style(window)
    for widget in labels_buttons:
        if not isinstance(widget, ttk.Label) or int(widget.cget("wraplength") or 0):
            continue
        text = str(widget.cget("text"))
        style_name = widget.cget("style") or widget.winfo_class()
        font = tkfont.Font(root=window, font=style.lookup(style_name, "font"))
        text_width = max((font.measure(line) for line in text.splitlines()), default=0)
        if text_width > widget.winfo_width():
            clipped_label_text.append({**label(widget), "measured_text_width": text_width})
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
    shared_participants = {name: [other for other in PRODUCT_KEYS
                                 if name in application.panels[other].inputs] for name in SHARED}
    shared_identity = {name: len({id(application.panels[other].inputs[name])
                                 for other in participants}) == 1
                       for name, participants in shared_participants.items()}
    shared_values = {name: {other: application.panels[other].inputs[name].get()
                            for other in participants} for name, participants in shared_participants.items()}
    field_widgets = [widget for widget in panel.winfo_children()
                     if isinstance(widget, (ttk.Entry, ttk.Combobox))]
    visible_fields = {name: any(str(widget.cget("textvariable")) == str(variable)
                                and widget.winfo_ismapped() for widget in field_widgets)
                      for name, variable in panel.inputs.items()}
    report = {
        "product": key, "size": [width, height],
        "capture_mode": capture_mode, "screenshot_error": screenshot_error,
        "clipped_widgets": clipped, "compressed_labels_or_buttons": compressed_labels,
        "clipped_label_text": clipped_label_text,
        "overlapping_leaf_widgets": overlaps,
        "save_all": label(save_all), "generate": label(generate),
        "save_all_immediately_left_of_generate": immediately_left,
        "result_lines": int(panel.output.cget("height")),
        "result_pixels": panel.output.winfo_height(),
        "result_scroll_range": list(panel.output.yview()),
        "shared_variable_identity": shared_identity, "shared_values": shared_values,
        "shared_field_participants": shared_participants,
        "visible_input_fields": visible_fields,
        "field_rows": len(panel.product.fields),
        "status_text": panel.status.get(),
        "product_specific_inputs": {other: {name: application.panels[other].inputs[name].get()
                                            for name in values}
                                    for other, values in PRODUCT_INPUTS.items()},
        "database_ids": {other: application.panels[other].inputs["database_id"].get()
                         for other in DATABASE_IDS},
        "database_id_variables_distinct": len({id(application.panels[other].inputs["database_id"])
                                              for other in DATABASE_IDS}) == len(DATABASE_IDS),
        "sequence_input": "sequence" in panel.inputs,
        "source": "Owned Tk QA window; synthetic values; exact client-region capture; no backend calls",
    }
    (HERE / f"gui_layout_{key}_{size}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    reports.append(report)
    for passed, reason in (
        (not clipped, "widgets leave window bounds"),
        (screenshot_error is None, "window capture failed: " + str(screenshot_error)),
        (not compressed_labels, "labels or buttons are compressed"),
        (not clipped_label_text, "label text exceeds its allocated width"),
        (not overlaps, "leaf widgets overlap"),
        (immediately_left, "Save All is not immediately left of Buat & simpan"),
        (report["result_lines"] == 6, "results do not have six lines"),
        (all(shared_identity.values()), "shared fields use separate variables"),
        (all(set(values.values()) == {SHARED[name]} for name, values in shared_values.items()),
         "shared field values do not match"),
        (report["database_ids"] == DATABASE_IDS, "database IDs were overwritten"),
        (report["database_id_variables_distinct"], "database ID variables are shared"),
        (all(visible_fields.values()), "a product input is missing or hidden"),
        (report["product_specific_inputs"] == PRODUCT_INPUTS, "product-specific identifiers were overwritten"),
        (not report["sequence_input"], "sequence input is exposed"),
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
