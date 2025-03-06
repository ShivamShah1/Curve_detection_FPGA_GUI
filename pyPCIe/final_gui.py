import struct
import threading
import tkinter as tk
import os
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from pypcie import Device

# Constants
TRIGGER_REG = 0x0
BUSY_REG = 0x8
BLOCK_SIZE = 4 * 1024

# Buffer size (16384 per channel, total 32768)
SAMPLES = 4 * BLOCK_SIZE
NUM_SAMPLES = 2 * SAMPLES  # 32768 total samples
CHANNEL_SAMPLES = NUM_SAMPLES // 2  # 16384 per channel

# Global Variables
running = False
continuous_mode = False
bars = None
latest_A_samples = np.zeros(CHANNEL_SAMPLES, dtype=np.int16)
latest_B_samples = np.zeros(CHANNEL_SAMPLES, dtype=np.int16)

# Lock for thread-safe updates
data_lock = threading.Lock()

# Initialize PCIe
def pcie_init():
    os.system("setpci -s 01:00.0 COMMAND=0x2")
    d = Device("0000:01:00.0")
    if not d:
        print("ERROR PCIE: Unable to open PCIe device")
        os.exit()
    print("PCIE: Initialized")
    return [d.bar[1], d.bar[0]]

# Trigger Function
def trigger(bar):
    print("Triggering FPGA...")
    bar.write(TRIGGER_REG, 0x1)
    bar.write(TRIGGER_REG, 0x0)
    print(f"Trigger Completed. Status: {bar.read(TRIGGER_REG)}")

# Check Busy State
def busy_state(bar):
    return bar.read(BUSY_REG) & 0xFFFFFFFF

# Fetch Data from PCIe
def generate_samples():
    global latest_A_samples, latest_B_samples
    if bars is None:
        return

    control_bar, samples_bar = bars[0], bars[1]
    trigger(control_bar)

    while busy_state(control_bar):
        print("Acquisition busy...")

    sample_array = bytearray()
    for word in range(SAMPLES):
        word_offset = word * 4
        sample = samples_bar.read(word_offset) & 0xFFFFFFFF
        packed_sample = struct.pack('<i', (sample & 0xFFFFFFFF))
        sample_array.extend(packed_sample)

    # Ensure data is multiple of 2 (16-bit samples)
    process_size = len(sample_array) // 2 * 2
    sample_array = sample_array[:process_size]
    
    # Convert to 16-bit integers
    int_samples_list = struct.unpack('<' + 'h' * (len(sample_array) // 2), sample_array)

    # Separate channels
    A_samples = int_samples_list[::2]
    B_samples = int_samples_list[1::2]

    with data_lock:
        latest_A_samples[:] = A_samples[-CHANNEL_SAMPLES:]
        latest_B_samples[:] = B_samples[-CHANNEL_SAMPLES:]

# Continuous Data Acquisition Thread
def data_acquisition():
    while running:
        generate_samples()
        update(1)
        time.sleep(0.1)  # Small delay to avoid excessive CPU usage

# Start Continuous Data Acquisition
def start_server():
    global running, bars, continuous_mode
    if running:
        print("[Server] Already running.")
        return

    bars = pcie_init()
    if not bars:
        print("[Server] PCIe initialization failed.")
        return

    running = True
    continuous_mode = True
    threading.Thread(target=data_acquisition, daemon=True).start()
    print("[Server] Data acquisition started.")

# Stop Data Acquisition
def stop_server():
    global running, continuous_mode
    if not running:
        return
    
    running = False
    continuous_mode = False
    print("[Server] Stopped data acquisition.")

# One-Time Triggered Data Acquisition
def trigger_once():
    global continuous_mode
    if bars is None:
        return

    continuous_mode = False
    generate_samples()
    update_plot()

# Matplotlib Plot Setup
fig, ax = plt.subplots(figsize=(6, 4))
ax.set_xlim(0, NUM_SAMPLES // 2)
ax.set_ylim(1800, 5000)
line_A, = ax.plot([], [], 'b-', label="Channel A")
line_B, = ax.plot([], [], 'g-', label="Channel B")
ax.legend()
ax.set_title('Live ADC Samples')
ax.set_xlabel('Sample Index')
ax.set_ylabel('Sample Value')

# Fix: Proper Continuous Update for FuncAnimation
def update(_):
    if continuous_mode:
        with data_lock:
            x_values = np.arange(CHANNEL_SAMPLES)
            line_A.set_data(x_values, latest_A_samples)
            line_B.set_data(x_values, latest_B_samples)
        canvas.draw_idle()
        return line_A, line_B

# Function to Update Plot Manually (For Single Trigger)
def update_plot():
    with data_lock:
        ax.set_xlim(0, NUM_SAMPLES // 2)
        ax.set_ylim(1800, 5000)
        line_A.set_data(np.arange(CHANNEL_SAMPLES), latest_A_samples)
        line_B.set_data(np.arange(CHANNEL_SAMPLES), latest_B_samples)

    canvas.draw_idle()

ani = animation.FuncAnimation(fig, update, interval=50)

# GUI Setup
root = tk.Tk()
root.title("PCIe Data Server GUI")

# Buttons
tk.Button(root, text="Start Continuous", command=start_server).pack()
tk.Button(root, text="Trigger Once", command=trigger_once).pack()
tk.Button(root, text="Stop", command=stop_server).pack()

# Embed Matplotlib Figure in Tkinter
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack()

# Function to handle window closing event
def on_close():
    global running
    print("[Exit] Stopping data acquisition and closing GUI.")
    running = False  # Ensure the acquisition thread stops
    root.quit()  # Stop the Tkinter main loop
    root.destroy()  # Destroy the window and exit cleanly
    os._exit(0)  # Ensure all threads terminate

# Bind the window close event
root.protocol("WM_DELETE_WINDOW", on_close)

# Run Tkinter GUI in the main thread
root.mainloop()
