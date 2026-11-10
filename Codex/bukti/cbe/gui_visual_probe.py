"""Render three manual-input tabs with synthetic data, without backend calls."""
import json
from pathlib import Path
import sys
import tkinter as tk

from PIL import ImageGrab

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
import app

window = tk.Tk()
application = app.LicenseApp(window)
window.title("JIBAS — Generator Lisensi — QA")
window.attributes("-topmost", True)
for key, dbid, capacity in (("face", "V4YNE", "100"), ("schoolpay", "7VJM4", "25"), ("cbe", "ABCDE", "30")):
    panel = application.panels[key]
    for name, value in dict(database_id=dbid, system_id="DDCB4", capacity=capacity,
                            client_name="Contoh Sekolah", expires="2030-12-31").items():
        panel.inputs[name].set(value)
    panel.show_result({"contoh_tampilan": True, "produk": panel.product.label,
                       "catatan": "Input manual; data sintetis, tanpa koneksi database atau aktivasi.",
                       "pemeriksaan": [{"nama": f"Contoh pemeriksaan {i}", "hasil": "contoh"} for i in range(12)]})


def capture(key, size):
    panel = application.panels[key]
    window.geometry(f"{size}+20+0")
    application.notebook.select(panel)
    window.lift()
    window.update()
    x, y = window.winfo_rootx(), window.winfo_rooty()
    filename = f"gui_{key}_{size}.png"
    ImageGrab.grab(bbox=(x, y, x + window.winfo_width(), y + window.winfo_height())).save(HERE / filename)
    clipped = []
    nodes = [application]
    while nodes:
        widget = nodes.pop()
        nodes.extend(widget.winfo_children())
        if not widget.winfo_ismapped():
            continue
        left = widget.winfo_rootx() - x
        top = widget.winfo_rooty() - y
        if (left < 0 or top < 0 or left + widget.winfo_width() > window.winfo_width()
                or top + widget.winfo_height() > window.winfo_height()):
            clipped.append(str(widget))
    report = {"product": key, "size": [window.winfo_width(), window.winfo_height()],
              "clipped_widgets": clipped, "result_lines": panel.output.cget("height"),
              "result_pixels": panel.output.winfo_height(), "sequence_input": "sequence" in panel.inputs,
              "database_settings": hasattr(application, "connection"),
              "source": "Owned Tk QA window, synthetic values, exact client-region capture"}
    (HERE / f"gui_layout_{key}_{size}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    assert not clipped, report


scenes = [(key, size) for size in ("880x650", "760x560") for key in ("face", "schoolpay", "cbe")]


def next_scene(index=0):
    if index >= len(scenes):
        application.close()
        return
    key, size = scenes[index]
    window.geometry(f"{size}+20+0")
    application.notebook.select(application.panels[key])
    window.after(250, lambda: (capture(key, size), window.after(100, lambda: next_scene(index + 1))))


window.after(300, next_scene)
window.mainloop()
