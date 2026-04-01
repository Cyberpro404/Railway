"""
PROJECT GANDIVA — Full Parameter Monitor
TCP Modbus client with time-domain signal, FFT spectrum and all 21 registers.
"""
import tkinter as tk
from tkinter import ttk
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from pymodbus.client import ModbusTcpClient
import threading
import time
import datetime
from collections import deque

# ==============================================================================
# 1. SYSTEM CONFIGURATION
# ==============================================================================
CONFIG = {
    "HOST":      "192.168.0.1",   # DXM controller IP
    "PORT":      502,              # Modbus TCP port
    "SLAVE":     1,
    "TIMEOUT":   1.5,
    "POLL_HZ":   10,               # polls per second (10 Hz)
    "HIST_LEN":  300,              # 30 s of history @ 10 Hz
    "FFT_LEN":   256,              # FFT window (≤ HIST_LEN)
}

# ==============================================================================
# 2. REGISTER MAP  (index, label, divisor, unit)
#    Based on live scan of 192.168.0.1:502 slave=1
# ==============================================================================
REGS = [
    ( 0, "Z-Axis RMS",      100.0,   "mm/s"),
    ( 1, "Z-RMS Velocity",  1000.0,  "mm/s"),
    ( 2, "ISO Peak-Peak",   1000.0,  "mm/s"),
    ( 3, "Temperature",     100.0,   "°C  "),
    ( 4, "Z-True Peak",     1000.0,  "mm/s"),
    ( 5, "X-RMS Velocity",  1000.0,  "mm/s"),
    ( 6, "Z-Peak Accel",    1000.0,  "G   "),
    ( 7, "X-Peak Accel",    1000.0,  "G   "),
    ( 8, "Z-Peak Freq",     10.0,    "Hz  "),
    ( 9, "X-Peak Freq",     10.0,    "Hz  "),
    (10, "Z-Band RMS",      1000.0,  "mm/s"),
    (11, "X-Band RMS",      1000.0,  "mm/s"),
    (12, "Z-Kurtosis",      1000.0,  "    "),
    (13, "X-Kurtosis",      1000.0,  "    "),
    (14, "Z-Crest Factor",  1000.0,  "    "),
    (15, "X-Crest Factor",  1000.0,  "    "),
    (16, "Z-Envelope RMS",  1000.0,  "mm/s"),
    (17, "Z-Peak Velocity", 1000.0,  "mm/s"),
    (18, "X-Envelope RMS",  1000.0,  "mm/s"),
    (19, "X-Peak Velocity", 1000.0,  "mm/s"),
    (20, "Device Status",   1.0,     "raw "),
]

# KPI cards: (reg_label, display_name, bar_color, y_max)
KPI_DEFS = [
    ("Z-RMS Velocity",  "Z-RMS Vel",    "#00f5ff", 10.0),
    ("X-RMS Velocity",  "X-RMS Vel",    "#00ff88", 10.0),
    ("Z-Peak Velocity", "Z-Peak Vel",   "#5599ff", 10.0),
    ("X-Peak Velocity", "X-Peak Vel",   "#aa55ff", 10.0),
    ("Z-Peak Accel",    "Z-Pk Accel",   "#ff4444", 20.0),
    ("X-Peak Accel",    "X-Pk Accel",   "#ff00cc", 20.0),
    ("Temperature",     "Temp",         "#ffcc00", 80.0),
    ("Z-Peak Freq",     "Z-Peak Freq",  "#ff8833", 200.0),
    ("X-Peak Freq",     "X-Peak Freq",  "#33ff99", 200.0),
    ("Z-Kurtosis",      "Z-Kurtosis",   "#cc99ff", 15.0),
    ("X-Kurtosis",      "X-Kurtosis",   "#99ccff", 15.0),
    ("Z-Crest Factor",  "Z-Crest",      "#ffcc99", 20.0),
    ("X-Crest Factor",  "X-Crest",      "#99ffcc", 20.0),
    ("Z-Axis RMS",      "Z-Axis RMS",   "#888888", 10.0),
]

COLORS = {
    "bg":     "#08080f",
    "card":   "#0f1120",
    "border": "#1c2035",
    "cyan":   "#00f5ff",
    "green":  "#00ff88",
    "yellow": "#ffcc00",
    "red":    "#ff4444",
    "mag":    "#ff00cc",
    "text":   "#d0d8e8",
    "dim":    "#3a4258",
    "hdr":    "#060a12",
}

POLL_INTERVAL = 1.0 / CONFIG["POLL_HZ"]

# ==============================================================================
# 3. SHARED STATE
# ==============================================================================
class SharedState:
    def __init__(self):
        self.lock      = threading.Lock()
        self.connected = False
        self.last_ts   = "—"
        self.raw_regs  = [0] * 21
        self.scaled    = {r[1]: 0.0 for r in REGS}
        n = CONFIG["HIST_LEN"]
        self.hist_z  = deque(maxlen=n)   # Z-RMS velocity  (fills from real data)
        self.hist_x  = deque(maxlen=n)   # X-RMS velocity
        self.n_real  = 0                 # polls received from device
        self._t0     = time.time()

STATE = SharedState()

# ==============================================================================
# 4. BACKEND (TCP Modbus polling thread)
# ==============================================================================
def backend_worker():
    host, port = CONFIG["HOST"], CONFIG["PORT"]
    slave      = CONFIG["SLAVE"]
    print(f"[BACKEND] Connecting → {host}:{port}")
    client = ModbusTcpClient(host, port=port, timeout=CONFIG["TIMEOUT"])

    while True:
        try:
            # ── Connect ──────────────────────────────────────────
            if not client.connected:
                if client.connect():
                    print("[BACKEND] Connected!")
                    with STATE.lock:
                        STATE.connected = True
                else:
                    with STATE.lock:
                        STATE.connected = False
                    time.sleep(2.0)
                    continue

            # ── Read all 21 registers ────────────────────────────
            rr = client.read_holding_registers(address=0, count=21, slave=slave)
            if rr.isError():
                with STATE.lock:
                    STATE.connected = False
                time.sleep(0.5)
                continue

            regs = list(rr.registers)
            scaled = {}
            for idx, label, div, unit in REGS:
                raw = regs[idx] if idx < len(regs) else 0
                val = raw / div
                # signed 16-bit correction for temperature
                if label == "Temperature" and raw > 32767:
                    val = (raw - 65536) / div
                scaled[label] = round(val, 4)

            with STATE.lock:
                STATE.connected = True
                STATE.last_ts   = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                STATE.raw_regs  = regs
                STATE.scaled    = scaled
                STATE.hist_z.append(scaled.get("Z-RMS Velocity", 0.0))
                STATE.hist_x.append(scaled.get("X-RMS Velocity", 0.0))
                STATE.n_real   += 1

        except Exception as exc:
            print(f"[BACKEND ERROR] {exc}")
            with STATE.lock:
                STATE.connected = False
            try:
                client.close()
            except Exception:
                pass
            time.sleep(2.0)
            client = ModbusTcpClient(host, port=port, timeout=CONFIG["TIMEOUT"])

        time.sleep(POLL_INTERVAL)

# ==============================================================================
# 5. GUI
# ==============================================================================
class GandivaUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PROJECT GANDIVA | Full Parameter Monitor")
        self.root.geometry("1760x980")
        self.root.configure(bg=COLORS["bg"])
        self.root.resizable(True, True)
        self._fft_poly = None   # fill_between polygon, replaced each frame

        self._build_header()
        self._build_body()
        self._build_charts()
        self._update_loop()

    # ──────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self.root, bg=COLORS["hdr"], pady=7, padx=16)
        hdr.pack(fill="x", side="top")

        tk.Label(hdr, text="PROJECT GANDIVA",
                 font=("Segoe UI", 18, "bold"),
                 bg=COLORS["hdr"], fg=COLORS["cyan"]).pack(side="left")
        tk.Label(hdr, text="  |  FULL PARAMETER MONITOR  |  192.168.0.1:502",
                 font=("Segoe UI", 10),
                 bg=COLORS["hdr"], fg=COLORS["dim"]).pack(side="left")

        self.ts_lbl = tk.Label(hdr, text="--:--:--.---",
                               font=("Consolas", 13, "bold"),
                               bg=COLORS["hdr"], fg=COLORS["text"])
        self.ts_lbl.pack(side="right", padx=20)

        self.status_lbl = tk.Label(hdr, text="● CONNECTING…",
                                   font=("Consolas", 10, "bold"),
                                   bg=COLORS["hdr"], fg=COLORS["yellow"],
                                   padx=12, pady=4)
        self.status_lbl.pack(side="right")

    # ──────────────────────────────────────────────────────────
    def _build_body(self):
        body = tk.Frame(self.root, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=5, pady=5)

        # Right panel — MUST be packed before chart_frame so it gets its
        # requested width; if packed after, chart_frame's expand=True steals
        # all horizontal space and the right panel becomes invisible.
        right = tk.Frame(body, bg=COLORS["bg"], width=430)
        right.pack(side="right", fill="y", padx=(5, 0))
        right.pack_propagate(False)

        # Left: matplotlib charts (fills remaining space)
        self.chart_frame = tk.Frame(body, bg=COLORS["bg"])
        self.chart_frame.pack(side="left", fill="both", expand=True)

        # ── KPI cards grid ────────────────────────────────────
        kpi_outer = tk.Frame(right, bg=COLORS["bg"])
        kpi_outer.pack(fill="x", padx=2, pady=(0, 4))

        self.kpi_vals = {}
        self.kpi_bars = {}
        COLS = 2
        for i, (reg_key, name, color, max_v) in enumerate(KPI_DEFS):
            r, c = divmod(i, COLS)
            cell = tk.Frame(kpi_outer, bg=COLORS["card"],
                            highlightbackground=COLORS["border"],
                            highlightthickness=1,
                            padx=8, pady=5)
            cell.grid(row=r, column=c, padx=2, pady=2, sticky="nsew")
            kpi_outer.columnconfigure(c, weight=1)

            tk.Frame(cell, bg=color, height=2).pack(fill="x", pady=(0, 3))
            tk.Label(cell, text=name, font=("Segoe UI", 7),
                     bg=COLORS["card"], fg=COLORS["dim"]).pack(anchor="w")
            val_lbl = tk.Label(cell, text="—",
                               font=("Consolas", 14, "bold"),
                               bg=COLORS["card"], fg="#ffffff")
            val_lbl.pack(anchor="w")
            bar_bg = tk.Frame(cell, bg=COLORS["border"], height=3)
            bar_bg.pack(fill="x", pady=(3, 0))
            bar_fill = tk.Frame(bar_bg, bg=color, height=3, width=0)
            bar_fill.place(x=0, y=0, relheight=1.0)

            self.kpi_vals[reg_key] = (val_lbl, max_v)
            self.kpi_bars[reg_key] = (bar_bg, bar_fill, color, max_v)

        # ── Register table ────────────────────────────────────
        tk.Label(right, text="LIVE REGISTERS  (21 total)",
                 font=("Segoe UI", 9, "bold"),
                 bg=COLORS["bg"], fg=COLORS["dim"]).pack(fill="x", padx=4, pady=(4, 2))

        tbl = tk.Frame(right, bg=COLORS["card"],
                       highlightbackground=COLORS["border"],
                       highlightthickness=1)
        tbl.pack(fill="both", expand=True, padx=2, pady=(0, 4))

        self.tree = ttk.Treeview(tbl,
                                 columns=("reg", "name", "raw", "val", "unit"),
                                 show="headings", height=21)
        for col, w, lbl in [("reg", 40, "Reg"), ("name", 118, "Parameter"),
                             ("raw", 58, "Raw"), ("val", 70, "Value"), ("unit", 44, "Unit")]:
            self.tree.heading(col, text=lbl)
            self.tree.column(col, width=w, anchor="center" if col != "name" else "w")

        vsb = ttk.Scrollbar(tbl, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background=COLORS["card"], foreground=COLORS["text"],
                        fieldbackground=COLORS["card"], rowheight=23,
                        font=("Consolas", 9))
        style.configure("Treeview.Heading",
                        background=COLORS["border"], foreground=COLORS["text"],
                        font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", COLORS["border"])])

        self._tree_ids = []
        for idx, label, div, unit in REGS:
            iid = self.tree.insert("", "end",
                                   values=(f"R{idx:02d}", label.strip(), "—", "—", unit.strip()))
            self._tree_ids.append(iid)

    # ──────────────────────────────────────────────────────────
    def _build_charts(self):
        plt.style.use("dark_background")
        self.fig = plt.Figure(figsize=(9.5, 7.2), facecolor=COLORS["bg"])
        gs = gridspec.GridSpec(2, 1, figure=self.fig,
                               hspace=0.5, top=0.95, bottom=0.08,
                               left=0.09, right=0.98)

        # ── Time-Domain ───────────────────────────────────────
        self.ax_td = self.fig.add_subplot(gs[0])
        self.ax_td.set_facecolor(COLORS["card"])
        self.ax_td.set_title(
            f"Time-Domain Signal  (rolling {CONFIG['HIST_LEN']//CONFIG['POLL_HZ']} s "
            f"@ {CONFIG['POLL_HZ']} Hz)",
            color=COLORS["dim"], fontsize=9, pad=6)
        self.ax_td.set_ylabel("Velocity  (mm/s)", color=COLORS["dim"], fontsize=8)
        self.ax_td.set_xlabel("Time (s)", color=COLORS["dim"], fontsize=8)
        self.ax_td.tick_params(colors=COLORS["dim"], labelsize=7)
        for sp in self.ax_td.spines.values():
            sp.set_edgecolor(COLORS["border"])
        self.ax_td.grid(True, color=COLORS["border"], linestyle="--", alpha=0.5)

        n = CONFIG["HIST_LEN"]
        xs = np.linspace(0, n / CONFIG["POLL_HZ"], n)
        self.line_z, = self.ax_td.plot(xs, np.zeros(n),
                                       color=COLORS["cyan"], lw=1.6, label="Z-RMS")
        self.line_x, = self.ax_td.plot(xs, np.zeros(n),
                                       color=COLORS["green"], lw=1.4, label="X-RMS", alpha=0.85)
        self.ax_td.axhline(y=4.5, color=COLORS["yellow"], lw=0.9, ls="--", alpha=0.6, label="Warn 4.5")
        self.ax_td.axhline(y=7.1, color=COLORS["red"],    lw=1.0, ls="-",  alpha=0.6, label="Crit 7.1")
        self.ax_td.legend(loc="upper left", frameon=False, labelcolor=COLORS["text"], fontsize=7.5)
        self.ax_td.set_xlim(0, n / CONFIG["POLL_HZ"])
        self.ax_td.set_ylim(0, 0.5)

        # ── FFT Spectrum ──────────────────────────────────────
        self.ax_fft = self.fig.add_subplot(gs[1])
        self.ax_fft.set_facecolor(COLORS["card"])
        nyquist = CONFIG["POLL_HZ"] / 2
        self.ax_fft.set_title(
            f"FFT Spectrum  (vibration envelope, Nyquist = {nyquist:.0f} Hz)",
            color=COLORS["dim"], fontsize=9, pad=6)
        self.ax_fft.set_ylabel("Amplitude  (mm/s)", color=COLORS["dim"], fontsize=8)
        self.ax_fft.set_xlabel("Frequency  (Hz)",   color=COLORS["dim"], fontsize=8)
        self.ax_fft.tick_params(colors=COLORS["dim"], labelsize=7)
        for sp in self.ax_fft.spines.values():
            sp.set_edgecolor(COLORS["border"])
        self.ax_fft.grid(True, color=COLORS["border"], linestyle="--", alpha=0.5)
        self.ax_fft.set_xlim(0, nyquist)
        self.ax_fft.set_ylim(0, 0.1)

        # Frequency axis for one-sided FFT
        N = CONFIG["FFT_LEN"]
        self._fft_freqs = np.fft.rfftfreq(N, d=1.0 / CONFIG["POLL_HZ"])[: N // 2]

        # Placeholder line + dominant freq marker
        self.fft_line, = self.ax_fft.plot([], [],
                                           color=COLORS["mag"], lw=1.5, label="Z-axis")
        self.fft_x_line, = self.ax_fft.plot([], [],
                                              color=COLORS["green"], lw=1.0,
                                              alpha=0.7, label="X-axis")
        self.vline_dom = self.ax_fft.axvline(x=0, color=COLORS["yellow"],
                                              lw=1.2, ls="--", alpha=0.7)
        self._fft_dom_lbl = self.ax_fft.text(
            0.0, 0.0, "", color=COLORS["yellow"], fontsize=7, va="bottom")
        self._fft_info = self.ax_fft.text(
            0.5, 0.5, f"Collecting samples…  0 / {CONFIG['FFT_LEN']}  (0%)",
            ha="center", va="center", transform=self.ax_fft.transAxes,
            color=COLORS["dim"], fontsize=10, style="italic")
        self.ax_fft.legend(loc="upper right", frameon=False,
                           labelcolor=COLORS["text"], fontsize=7.5)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    # ──────────────────────────────────────────────────────────
    def _update_loop(self):
        with STATE.lock:
            connected = STATE.connected
            ts        = STATE.last_ts
            raw_regs  = list(STATE.raw_regs)
            scaled    = dict(STATE.scaled)
            hist_z    = np.array(STATE.hist_z, dtype=float)
            hist_x    = np.array(STATE.hist_x, dtype=float)
            n_real    = STATE.n_real

        # ── Header ────────────────────────────────────────────
        if connected:
            self.status_lbl.config(text="● LIVE", fg=COLORS["green"])
        else:
            self.status_lbl.config(text="● NO SIGNAL", fg=COLORS["red"])
        self.ts_lbl.config(text=ts)

        # ── KPI cards ─────────────────────────────────────────
        for reg_key, (val_lbl, max_v) in self.kpi_vals.items():
            v = scaled.get(reg_key, 0.0)
            val_lbl.config(text=f"{v:.3f}")
            if "Vel" in reg_key or "RMS" in reg_key:
                fg = COLORS["red"] if v > 4.5 else COLORS["yellow"] if v > 2.8 else "#ffffff"
                val_lbl.config(fg=fg)
            elif reg_key == "Temperature":
                fg = COLORS["red"] if v > 70 else COLORS["yellow"] if v > 55 else "#ffffff"
                val_lbl.config(fg=fg)
            else:
                val_lbl.config(fg="#ffffff")

        for reg_key, (bar_bg, bar_fill, color, max_v) in self.kpi_bars.items():
            v    = scaled.get(reg_key, 0.0)
            w    = bar_bg.winfo_width()
            frac = min(abs(v) / max_v, 1.0) if max_v > 0 else 0
            bar_fill.place(x=0, y=0, relheight=1.0, width=max(1, int(w * frac)))

        # ── Register table ────────────────────────────────────
        for iid, (idx, label, div, unit) in zip(self._tree_ids, REGS):
            raw = raw_regs[idx] if idx < len(raw_regs) else 0
            v   = scaled.get(label, 0.0)
            tag = "active" if raw != 0 else "zero"
            self.tree.item(iid,
                           values=(f"R{idx:02d}", label.strip(), raw, f"{v:.3f}", unit.strip()),
                           tags=(tag,))
        self.tree.tag_configure("active", foreground=COLORS["cyan"])
        self.tree.tag_configure("zero",   foreground=COLORS["dim"])

        # ── Time-Domain chart ─────────────────────────────────
        n_hist = CONFIG["HIST_LEN"]
        if len(hist_z) > 0:
            # Scroll right-to-left: pad left with zeros until buffer fills
            z_pad = np.concatenate([np.zeros(max(0, n_hist - len(hist_z))), hist_z])
            x_pad = np.concatenate([np.zeros(max(0, n_hist - len(hist_x))), hist_x])
            xs = np.linspace(0, n_hist / CONFIG["POLL_HZ"], n_hist)
            self.line_z.set_data(xs, z_pad)
            self.line_x.set_data(xs, x_pad)
            y_max = max(float(z_pad.max()), float(x_pad.max()), 0.5)
            self.ax_td.set_ylim(0, y_max * 1.35)

        # ── FFT Spectrum ──────────────────────────────────────
        N = CONFIG["FFT_LEN"]
        if n_real >= N:
            self._fft_info.set_visible(False)
            # Z axis spectrum
            sig_z = hist_z[-N:] - hist_z[-N:].mean()
            win   = np.hanning(N)
            mag_z = np.abs(np.fft.rfft(sig_z * win)) * 2.0 / N
            mag_z = mag_z[: N // 2]

            # X axis spectrum
            sig_x = hist_x[-N:] - hist_x[-N:].mean()
            mag_x = np.abs(np.fft.rfft(sig_x * win)) * 2.0 / N
            mag_x = mag_x[: N // 2]

            freqs = self._fft_freqs

            # Update lines
            self.fft_line.set_data(freqs, mag_z)
            self.fft_x_line.set_data(freqs, mag_x)

            # Remove old fill and redraw
            if self._fft_poly is not None:
                self._fft_poly.remove()
            self._fft_poly = self.ax_fft.fill_between(
                freqs, 0, mag_z, color=COLORS["mag"], alpha=0.25)

            # Dominant frequency marker (skip DC bin 0)
            if len(mag_z) > 1 and mag_z[1:].max() > 0:
                dom_idx = int(np.argmax(mag_z[1:])) + 1
                dom_hz  = float(freqs[dom_idx])
                self.vline_dom.set_xdata([dom_hz, dom_hz])
                self._fft_dom_lbl.set_text(f"dom: {dom_hz:.3f} Hz")
                self._fft_dom_lbl.set_x(min(dom_hz + 0.05, CONFIG["POLL_HZ"] / 2 * 0.8))

            y_fft = max(float(mag_z.max()), float(mag_x.max()), 0.001)
            self.ax_fft.set_ylim(0, y_fft * 1.6)
        else:
            pct = int(100 * n_real / N) if N > 0 else 0
            self._fft_info.set_text(
                f"Collecting samples…  {n_real} / {N}  ({pct}%)")
            self._fft_info.set_visible(True)

        self.canvas.draw_idle()
        self.root.after(100, self._update_loop)   # 10 Hz


# ==============================================================================
# 6. MAIN
# ==============================================================================
if __name__ == "__main__":
    t = threading.Thread(target=backend_worker, daemon=True)
    t.start()

    root = tk.Tk()
    app  = GandivaUI(root)

    def on_close():
        root.quit()
        root.destroy()
        import sys; sys.exit(0)

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()