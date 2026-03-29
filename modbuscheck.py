import tkinter as tk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from pymodbus.client import ModbusSerialClient
import threading
import time
import datetime
from collections import deque

# ==============================================================================
# 1. SYSTEM CONFIGURATION
# ==============================================================================
CONFIG = {
    "PORT": 'COM5',
    "BAUD": 19200,
    "SLAVE": 1,
    "TIMEOUT": 1.0,
    "SCALE_VIB": 100.0,  # 145 -> 1.45 mm/s
    "SCALE_TEMP": 100.0, # 9688 -> 96.88 °C
    "HISTORY_LEN": 60    # Keep 60 seconds of data for the graph
}

# ==============================================================================
# 2. SHARED MEMORY (The Bridge between Backend & Frontend)
# ==============================================================================
class SharedState:
    def __init__(self):
        self.lock = threading.Lock()
        self.connected = False
        self.last_update = "Waiting..."
        
        # Current Values (Real-Time)
        self.sensors = {"vib_z": 0.0, "vib_x": 0.0, "temp": 0.0}
        
        # Raw Registers (For the Grid - 21 Total)
        self.raw_regs = [0] * 21 
        
        # History (For the Graph)
        self.history = {
            "z": deque(maxlen=CONFIG["HISTORY_LEN"]),
            "x": deque(maxlen=CONFIG["HISTORY_LEN"]),
            "t": deque([0]*CONFIG["HISTORY_LEN"], maxlen=CONFIG["HISTORY_LEN"]) # Init with zeros
        }

STATE = SharedState()

# ==============================================================================
# 3. BACKEND ENGINE (Modbus Poller Thread)
# ==============================================================================
def backend_worker():
    print(f"--- [BACKEND] Starting Modbus Poller on {CONFIG['PORT']} ---")
    
    client = ModbusSerialClient(
        port=CONFIG['PORT'],
        baudrate=CONFIG['BAUD'],
        parity='N',
        stopbits=1,
        bytesize=8,
        timeout=CONFIG['TIMEOUT']
    )

    while True:
        try:
            # A. Connection Logic
            if not client.connected:
                if client.connect():
                    print("--- [BACKEND] Connected! ---")
                    with STATE.lock: STATE.connected = True
                else:
                    with STATE.lock: STATE.connected = False
                    time.sleep(2.0)
                    continue

            # B. Data Acquisition (Read ONLY 3 Registers for Stability)
            # We fetch 3 real ones and fake the other 18 to prevent crashes.
            rr = client.read_holding_registers(address=0, count=3, slave=CONFIG['SLAVE'])

            if not rr.isError():
                regs = rr.registers # [57, 145, 9688]
                
                # C. Engineering Unit Conversion
                val_z = round(regs[0] / CONFIG['SCALE_VIB'], 2)
                val_x = round(regs[1] / CONFIG['SCALE_VIB'], 2)
                val_t = round(regs[2] / CONFIG['SCALE_TEMP'], 2)

                # D. Update Shared Memory (Thread-Safe)
                with STATE.lock:
                    STATE.connected = True
                    STATE.last_update = datetime.datetime.now().strftime("%H:%M:%S")
                    
                    # Update Sensors
                    STATE.sensors = {"vib_z": val_z, "vib_x": val_x, "temp": val_t}
                    
                    # Update Grid Data (3 Real + 18 Virtual Zeros)
                    STATE.raw_regs = list(regs) + [0] * 18
                    
                    # Update Graph History
                    STATE.history["z"].append(val_z)
                    STATE.history["x"].append(val_x)
            
            else:
                # Read Error (Timeout)
                with STATE.lock: STATE.connected = False
                time.sleep(1.0)

        except Exception as e:
            print(f"--- [BACKEND ERROR] {e} ---")
            with STATE.lock: STATE.connected = False
            time.sleep(2.0)
            
        # Poll Rate (10Hz for smoothness)
        time.sleep(0.1)

# ==============================================================================
# 4. FRONTEND ENGINE (Professional GUI)
# ==============================================================================
class GandivaUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PROJECT GANDIVA | Industrial Monitor")
        self.root.geometry("1200x800")
        self.root.configure(bg="#0f0f0f") # Deep Black Background

        # --- COLORS & FONTS ---
        self.colors = {
            "bg": "#0f0f0f",
            "card": "#1a1a1a",
            "cyan": "#00f2ff",
            "green": "#00ff88",
            "text": "#e0e0e0",
            "dim": "#555555"
        }
        self.fonts = {
            "header": ("Segoe UI", 24, "bold"),
            "val": ("Consolas", 42, "bold"),
            "label": ("Segoe UI", 12),
            "small": ("Consolas", 10)
        }

        self.setup_ui()
        self.setup_graph()
        
        # Start Animation Loop
        self.update_ui()

    def setup_ui(self):
        # 1. Header Section
        header = tk.Frame(self.root, bg=self.colors["bg"], pady=15, padx=20)
        header.pack(fill="x")
        
        tk.Label(header, text="PROJECT GANDIVA", font=self.fonts["header"], 
                 bg=self.colors["bg"], fg=self.colors["cyan"]).pack(side="left")
        
        self.status_badge = tk.Label(header, text="CONNECTING...", font=("Segoe UI", 10, "bold"),
                                     bg="#333", fg="#fff", padx=15, pady=5, relief="flat")
        self.status_badge.pack(side="right")

        # 2. KPI Cards (Live Values)
        cards_frame = tk.Frame(self.root, bg=self.colors["bg"], pady=10)
        cards_frame.pack(fill="x", padx=10)

        self.lbl_z = self.create_card(cards_frame, "VIBRATION Z", "mm/s", self.colors["green"])
        self.lbl_x = self.create_card(cards_frame, "VIBRATION X", "mm/s", "#ff00ff")
        self.lbl_t = self.create_card(cards_frame, "TEMPERATURE", "°C", "#ffaa00")

        # 3. Main Content Area (Graph + Grid)
        content_frame = tk.Frame(self.root, bg=self.colors["bg"])
        content_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Left Side: Graph
        self.graph_container = tk.Frame(content_frame, bg=self.colors["card"], bd=1, relief="solid")
        self.graph_container.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # Right Side: Data Grid
        grid_container = tk.Frame(content_frame, bg=self.colors["card"], width=300, bd=1, relief="solid")
        grid_container.pack(side="right", fill="y", padx=(10, 0))
        grid_container.pack_propagate(False) # Force width
        
        tk.Label(grid_container, text="SYSTEM REGISTERS", font=("Segoe UI", 12, "bold"), 
                 bg=self.colors["card"], fg="#888", pady=10).pack(fill="x")
        
        # Scrollable Listbox for 21 Registers
        self.reg_list = tk.Listbox(grid_container, bg=self.colors["card"], fg=self.colors["text"],
                                   font=self.fonts["small"], bd=0, highlightthickness=0, height=25)
        self.reg_list.pack(fill="both", expand=True, padx=10, pady=10)

    def create_card(self, parent, title, unit, accent):
        """Helper to make beautiful cards"""
        card = tk.Frame(parent, bg=self.colors["card"], padx=20, pady=15)
        card.pack(side="left", fill="x", expand=True, padx=10)
        
        # Color Bar
        tk.Frame(card, bg=accent, height=3).pack(fill="x", pady=(0, 10))
        
        tk.Label(card, text=title, font=self.fonts["label"], bg=self.colors["card"], fg=self.colors["dim"]).pack(anchor="w")
        val = tk.Label(card, text="--", font=self.fonts["val"], bg=self.colors["card"], fg="#fff")
        val.pack(anchor="w")
        tk.Label(card, text=unit, font=self.fonts["small"], bg=self.colors["card"], fg=self.colors["dim"]).pack(anchor="w")
        return val

    def setup_graph(self):
        """Embed Matplotlib in Tkinter"""
        plt.style.use('dark_background')
        self.fig, self.ax = plt.subplots()
        self.fig.patch.set_facecolor(self.colors["card"])
        self.ax.set_facecolor(self.colors["card"])
        
        # Plot Lines
        self.line_z, = self.ax.plot([], [], color=self.colors["green"], lw=2, label="Vib Z")
        self.line_x, = self.ax.plot([], [], color="#ff00ff", lw=2, label="Vib X")
        
        # Style
        self.ax.grid(True, color="#333", ls="--")
        self.ax.legend(loc="upper left", frameon=False, labelcolor="white")
        self.ax.set_ylim(0, 5)
        self.ax.set_title("Real-Time Vibration Spectrum (60s)", color="#888", fontsize=10)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_container)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def update_ui(self):
        """The Animation Loop - Refreshes GUI from Shared Memory"""
        with STATE.lock:
            connected = STATE.connected
            sensors = STATE.sensors
            history_z = list(STATE.history["z"])
            history_x = list(STATE.history["x"])
            regs = list(STATE.raw_regs)

        # A. Update Status
        if connected:
            self.status_badge.config(text="● SYSTEM ONLINE", bg="#004400", fg=self.colors["green"])
            
            # B. Update Cards
            self.lbl_z.config(text=f"{sensors['vib_z']:.2f}")
            self.lbl_x.config(text=f"{sensors['vib_x']:.2f}")
            self.lbl_t.config(text=f"{sensors['temp']:.2f}")

            # C. Update Graph
            if len(history_z) > 0:
                self.line_z.set_data(range(len(history_z)), history_z)
                self.line_x.set_data(range(len(history_x)), history_x)
                
                self.ax.set_xlim(0, max(60, len(history_z)))
                # Auto-scale Y Axis
                curr_max = max(max(history_z) if history_z else 0, max(history_x) if history_x else 0)
                self.ax.set_ylim(0, max(5, curr_max * 1.2))
                self.canvas.draw()

            # D. Update Grid List
            self.reg_list.delete(0, tk.END)
            for i, val in enumerate(regs):
                # Highlight the first 3 (Real Sensors)
                prefix = ">> " if i < 3 else "   "
                color = self.colors["green"] if i < 3 else self.colors["dim"]
                desc = "Reserved"
                if i == 0: desc = "Vib Z-Axis"
                if i == 1: desc = "Vib X-Axis"
                if i == 2: desc = "Temperature"
                
                row_text = f"{prefix} REG_{i+1:02d} : {val:<6} [{desc}]"
                self.reg_list.insert(tk.END, row_text)
                if i < 3:
                    self.reg_list.itemconfig(i, {'fg': self.colors["cyan"]})
                else:
                    self.reg_list.itemconfig(i, {'fg': self.colors["dim"]})

        else:
            self.status_badge.config(text="● DISCONNECTED", bg="#440000", fg="#ff5555")

        # Schedule next update (100ms)
        self.root.after(100, self.update_ui)

# ==============================================================================
# 5. MAIN EXECUTION
# ==============================================================================
if __name__ == "__main__":
    # 1. Start Backend Thread
    t = threading.Thread(target=backend_worker, daemon=True)
    t.start()

    # 2. Start Frontend GUI
    root = tk.Tk()
    app = GandivaUI(root)
    
    # Handle Exit
    def on_closing():
        root.quit()
        root.destroy()
        import sys
        sys.exit()
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()