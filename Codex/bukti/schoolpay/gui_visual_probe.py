"""Render synthetic data for window-only visual QA; no backend/DB calls."""
import json
from pathlib import Path
import sys
import tkinter as tk
from PIL import ImageGrab

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import app

window = tk.Tk()
application = app.LicenseApp(window)
window.title("JIBAS — Generator Lisensi — QA")
window.geometry("880x710+20+0")
window.attributes("-topmost", True)
for product, dbid, capacity in (("face", "V4YNE", "100"), ("schoolpay", "7VJM4", "25")):
    panel = application.panels[product]
    for key, value in dict(database_id=dbid, system_id="DDCB4", capacity=capacity,
                           client_name="Contoh Sekolah", expires="2030-12-31").items():
        panel.inputs[key].set(value)
    panel.show_result({"contoh_tampilan": True, "produk": panel.product.label,
                       "catatan": "Data sintetis untuk pemeriksaan tampilan; tidak ada aktivasi atau koneksi database.",
                       "fields": {"Database ID": dbid, "System ID": "DDCB4", "Kapasitas": capacity},
                       "pemeriksaan": [{"nama": f"Contoh pemeriksaan {i}", "hasil": "contoh"} for i in range(1, 9)]})


def record_layout():
    window.update_idletasks()
    clipped = []
    nodes = [application]
    while nodes:
        widget = nodes.pop()
        nodes.extend(widget.winfo_children())
        if not widget.winfo_ismapped():
            continue
        x = widget.winfo_rootx() - window.winfo_rootx()
        y = widget.winfo_rooty() - window.winfo_rooty()
        if x < 0 or y < 0 or x + widget.winfo_width() > window.winfo_width() or y + widget.winfo_height() > window.winfo_height():
            clipped.append({"widget": str(widget), "class": widget.winfo_class(),
                            "bounds": [x, y, widget.winfo_width(), widget.winfo_height()]})
    result = {"product": application.active_panel().product.key,
              "size": [window.winfo_width(), window.winfo_height()],
              "screen_size": [window.winfo_screenwidth(), window.winfo_screenheight()],
              "client_origin": [window.winfo_rootx(), window.winfo_rooty()],
              "clipped_widgets": clipped}
    path = Path(__file__).with_name(f"gui_layout_{result['product']}_{result['size'][0]}x{result['size'][1]}.json")
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")


def resize(size):
    window.geometry(size)
    window.after(200, record_layout)


window.bind("<Control-m>", lambda event: resize("760x650"))
window.bind("<Control-n>", lambda event: resize("880x710"))
application.notebook.bind("<<NotebookTabChanged>>", lambda event: window.after(200, record_layout))
window.after(500, record_layout)


def capture(name):
    # Capture this application's exact client rectangle only. This fallback
    # does not inspect or interact with any other desktop application.
    window.lift()
    window.update_idletasks()
    x, y = window.winfo_rootx(), window.winfo_rooty()
    ImageGrab.grab(bbox=(x, y, x + window.winfo_width(), y + window.winfo_height())).save(
        Path(__file__).with_name(name))
    record_layout()


def scene(product, geometry, filename, next_step):
    window.geometry(geometry)
    application.notebook.select(application.panels[product])
    window.after(300, lambda: (capture(filename), window.after(250, next_step)))


if "--capture" in sys.argv:
    window.after(700, lambda: scene("face", "880x710+20+0", "gui_absensi.png",
        lambda: scene("schoolpay", "880x710+20+0", "gui_schoolpay.png",
        lambda: scene("face", "760x650+20+0", "gui_absensi_min.png",
        lambda: scene("schoolpay", "760x650+20+0", "gui_schoolpay_min.png", application.close)))))
window.mainloop()
