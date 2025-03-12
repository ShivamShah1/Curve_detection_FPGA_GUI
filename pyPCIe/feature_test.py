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
DACVALUE_REG = 0x10
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

# Default range
selected_start = 0
selected_end = CHANNEL_SAMPLES
selected_ylim = [1800, 5000]  # Initial Y range

# Initialize PCIe
def pcie_init():
    os.system("setpci -s 01:00.0 COMMAND=0x2")
    d = Device("0000:01:00.0")
    if not d:
        print("ERROR PCIE: Unable to open PCIe device")
        os.exit()
    print("PCIE: Initialized")
    return [d.bar[1], d.bar[0]]

root = tk.Tk()
root.title("PCIe Data Server GUI")

# DAC Value Frame
dac_frame = tk.Frame(root)
dac_frame.pack(pady=5)

tk.Label(dac_frame, text="DAC Value (Decimal):").grid(row=0, column=0)

# Entry field with default value 20
dac_value_entry = tk.Entry(dac_frame, width=10)
dac_value_entry.grid(row=0, column=1)
dac_value_entry.insert(0, "20")  # Default value set to 20

# Initialize a variable to track the last valid DAC value
last_valid_dac_value = 20  # Default value

def update_dac_value():
    """Fetches user input, converts decimal to integer, and returns its hex equivalent (as an integer)."""
    global last_valid_dac_value  # Access the global variable for the last valid DAC value

    try:
        decimal_value = dac_value_entry.get().strip()  # Get user input and remove spaces

        if not decimal_value:  # If empty, use the last valid or default value
            decimal_value = last_valid_dac_value
        else:
            decimal_value = int(decimal_value)  # Convert input to integer

        if decimal_value == 0:  # If the value is 0, revert to the last valid value
            print("Error: 0 is not a valid input. Using last valid DAC value:", last_valid_dac_value)
            return last_valid_dac_value
        
        if 0 < decimal_value <= 65535:  # Ensure it's in valid range
            last_valid_dac_value = decimal_value  # Update the last valid DAC value
            return decimal_value  # Return as integer (hex conversion happens automatically)
        else:
            print("Error: Value out of range (0-65535). Using last valid DAC value.")
            return last_valid_dac_value
    except ValueError:
        print("Error: Invalid input. Using last valid DAC value.")
        return last_valid_dac_value

# Trigger Function
def trigger(bar):
    print("Triggering FPGA...")
    hex_val = update_dac_value()
    bar.write(DACVALUE_REG, hex_val)
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
        time.sleep(0.1)

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
    global running, bars, continuous_mode
    if running:
        print("[Server] Already running.")
        return

    bars = pcie_init()
    if not bars:
        print("[Server] PCIe initialization failed.")
        return

    continuous_mode = False
    generate_samples()
    update_plot()

def count_spikes(samples, threshold=2250, end_threshold=2065):
    spike_count = 0
    in_spike = False  # Tracks whether we are inside a spike
    spike_positions = []
    spike_heights = []
    spike_colors = []
    max_sample = None
    max_sample_index = None
    spike_start_index = None

    # Lists to hold the max sample index for each spike
    max_sample_indices = []

    for i, sample in enumerate(samples):
        if abs(sample) > threshold and not in_spike:  # Start of a new spike
            in_spike = True
            spike_start_index = i  # Record the start index of the spike
            max_sample = sample
            max_sample_index = i
        elif in_spike:
            if abs(sample) > abs(max_sample):  # Track the highest value within the spike
                max_sample = sample
                max_sample_index = i
            
            if abs(sample) <= end_threshold:  # End of spike when value returns to or below end_threshold
                spike_count += 1  # Increment spike count
                spike_positions.append(spike_start_index)  # Position of the spike
                spike_heights.append(max_sample)  # Maximum height of the spike
                max_sample_indices.append(max_sample_index)  # Append the peak index

                # Assign color based on max_sample value
                if abs(max_sample) < 2100:
                    spike_colors.append('blue')  # Low range
                elif 2100 <= abs(max_sample) < 2300:
                    spike_colors.append('lightblue')  # Soft blue
                elif 2500 <= abs(max_sample) < 3000:
                    spike_colors.append('cyan')  # Light cyan for middle-low values
                elif 3000 <= abs(max_sample) < 3400:
                    spike_colors.append('lightyellow')  # Soft yellow
                elif 3400 <= abs(max_sample) < 3600:
                    spike_colors.append('yellow')  # Mid-range values
                elif 3600 <= abs(max_sample) < 3800:
                    spike_colors.append('orange')  # Higher mid-range values
                elif 3800 <= abs(max_sample) < 4000:
                    spike_colors.append('darkorange')  # Near-high range values
                else:
                    spike_colors.append('red')  # High range

                # Reset tracking variables after spike ends
                in_spike = False
                max_sample = None
                max_sample_index = None
                spike_start_index = None

    return spike_count, spike_positions, spike_heights, spike_colors, max_sample_indices

# Matplotlib Plot Setup
fig, ax = plt.subplots(figsize=(6, 4))
ax.set_xlim(0, CHANNEL_SAMPLES)
ax.set_ylim(1800, 5000)
line_A, = ax.plot([], [], 'b-', label="Channel A")
line_B, = ax.plot([], [], 'g-', label="Channel B")
ax.legend()
ax.set_title('Live ADC Samples')
ax.set_xlabel('Sample Index')
ax.set_ylabel('Sample Value')

# Store the original axis limits
original_xlim = ax.get_xlim()
original_ylim = ax.get_ylim()

# Fix: Proper Continuous Update for FuncAnimation
def update(_, skip=40):
    if continuous_mode:
        with data_lock:
            x_values = np.arange(CHANNEL_SAMPLES)
            line_A.set_data(x_values, latest_A_samples)
            line_B.set_data(x_values, latest_B_samples)
        canvas.draw_idle()

        # Count spikes and get their positions, heights, colors, and max sample indices for continuous data
        spike_count_A, spike_positions_A, spike_heights_A, spike_colors_A, max_sample_indices_A = count_spikes(latest_A_samples)
        #spike_count_B, spike_positions_B, spike_heights_B, spike_colors_B, max_sample_indices_B = count_spikes(latest_B_samples)

        # Format the spike data as a list of tuples (position, height) for Channel A only
        spike_data_A = [(max_sample_indices_A[i], spike_heights_A[i]) for i in range(spike_count_A)]
        #spike_data_B = [(max_sample_indices_B[i], spike_heights_B[i]) for i in range(spike_count_B)]

        # Combine spike data for both channels with the spike count in the desired format
        spike_data_text_A = f"Spikes (A) ({spike_count_A}): {spike_data_A}"
        #spike_data_text_B = f"Spikes (B) ({spike_count_B}): {spike_data_B}"

        # Combine spike data text for both channels
        spike_data_text = f"{spike_data_text_A}"

        # Update the spike count label to include the spike data
        spike_count_label.config(
            text=spike_data_text
        )

        # Clear and replot the data for both channels
        ax.cla()  # Clear the axis
        ax.set_xlim(0, CHANNEL_SAMPLES)
        ax.set_ylim(1800, 5000)

        # Plot the main signal lines for both channels
        ax.plot(x_values, latest_A_samples, 'b-', label="Channel A")
        ax.plot(x_values, latest_B_samples, 'g-', label="Channel B")

        # Plot colored dots for the highest peak of each spike for Channel A only
        for i, (peak_position, peak_height, color) in enumerate(zip(max_sample_indices_A, spike_heights_A, spike_colors_A)):
            ax.scatter(peak_position, peak_height, color=color, zorder=5, label=f"Peak A {i+1}")  # Plot a colored dot at the peak

        canvas.draw_idle()

        return line_A, line_B

# Function to Update Plot
def update_plot(skip=40):
    global selected_start, selected_end, selected_ylim
    
    # Ensure range values are integers
    selected_start, selected_end = int(selected_start), int(selected_end)

    with data_lock:
        x_values = np.arange(selected_start, selected_end)
        line_A.set_data(x_values, latest_A_samples[selected_start:selected_end])
        line_B.set_data(x_values, latest_B_samples[selected_start:selected_end])

    # Count spikes and get their positions, heights, and colors
    spike_count_A, spike_positions_A, spike_heights_A, spike_colors_A, max_sample_indices_A = count_spikes(latest_A_samples)
    #spike_count_B, spike_positions_B, spike_heights_B, spike_colors_B, max_sample_indices_B = count_spikes(latest_B_samples)

    # Format the spike data as a list of tuples (position, height) for Channel A only
    spike_data_A = [(max_sample_indices_A[i], spike_heights_A[i]) for i in range(spike_count_A)]
    #spike_data_B = [(max_sample_indices_B[i], spike_heights_B[i]) for i in range(spike_count_B)]

    # Combine spike data for both channels with the spike count in the desired format
    spike_data_text_A = f"Spikes (A) ({spike_count_A}): {spike_data_A}"
    #spike_data_text_B = f"Spikes (B) ({spike_count_B}): {spike_data_B}"

    # Combine spike data text for both channels
    spike_data_text = f"{spike_data_text_A}"

    # Update the spike count label to include the spike data
    spike_count_label.config(
        text=spike_data_text
    )

    # Clear and replot the data for the selected range
    ax.cla()  # Clear the axis
    ax.set_xlim(selected_start, selected_end)
    ax.set_ylim(selected_ylim)

    # Plot the main signal lines for both channels
    ax.plot(x_values, latest_A_samples[selected_start:selected_end], 'b-', label="Channel A")
    ax.plot(x_values, latest_B_samples[selected_start:selected_end], 'g-', label="Channel B")

    # Plot each spike with its correct color for Channel A
    for i, (position, height, color) in enumerate(zip(spike_positions_A, spike_heights_A, spike_colors_A)):
        peak_position = max_sample_indices_A[i]  # Use the actual peak position from the indices
        peak_height = height  # Use the maximum height of the spike
        ax.scatter(peak_position, peak_height, color=color, zorder=5, label=f"Peak A {i+1}")  # Plot a colored dot at the peak

    # Plot each spike with its correct color for Channel B
    #for i, (position, height, color) in enumerate(zip(spike_positions_B, spike_heights_B, spike_colors_B)):
    #    peak_position = max_sample_indices_B[i]  # Use the actual peak position from the indices
    #    peak_height = height  # Use the maximum height of the spike
    #    ax.scatter(peak_position, peak_height, color=color, zorder=5, label=f"Peak B {i+1}")  # Plot a colored dot at the peak

    # Draw the updated plot
    canvas.draw_idle()

# Set User-Defined X-axis Range
def set_x_range():
    global selected_start, selected_end
    try:
        start_sample = int(start_sample_entry.get())
        end_sample = int(end_sample_entry.get())

        if start_sample < 0 or end_sample > CHANNEL_SAMPLES or start_sample >= end_sample:
            print("Invalid range.")
            return

        selected_start = start_sample
        selected_end = end_sample
        update_plot()
    except ValueError:
        print("Please enter valid numbers.")

# Shift X-axis Range within User-Defined Range
def shift_x_range(direction):
    global selected_start, selected_end
    try:
        shift_value = int(shift_amount_entry.get())  # Get user shift value

        # Apply shift based on direction
        if direction == "left":
            new_start = max(0, selected_start - shift_value)
            new_end = new_start + (selected_end - selected_start)
        elif direction == "right":
            new_end = min(CHANNEL_SAMPLES, selected_end + shift_value)
            new_start = new_end - (selected_end - selected_start)

        if new_start < 0 or new_end > CHANNEL_SAMPLES:
            print("Shift out of range.")
            return

        selected_start, selected_end = new_start, new_end
        update_plot()
    except ValueError:
        print("Please enter a valid shift amount.")

# Function to reset the graph to original size
# Function to reset the graph to original size
def reset_zoom():
    global selected_start, selected_end, selected_ylim

    # Ensure the range is integers
    selected_start, selected_end = int(original_xlim[0]), int(original_xlim[1])
    selected_ylim = list(original_ylim)  # Reset Y-axis range to the original values

    ax.set_xlim(original_xlim)  # Reset X-axis
    ax.set_ylim(original_ylim)  # Reset Y-axis

    update_plot()  # Redraw the plot with updated ranges


# Shift Y-axis Range within User-Defined Range
def shift_y_range(direction):
    global selected_ylim, original_ylim

    try:
        shift_value = int(shift_y_amount_entry.get())  # Get user shift value

        # Apply shift based on direction
        if direction == "up":
            new_ylim = (selected_ylim[0] + shift_value, selected_ylim[1] + shift_value)
        elif direction == "down":
            new_ylim = (selected_ylim[0] - shift_value, selected_ylim[1] - shift_value)

        # Ensure the Y range doesn't exceed original limits
        if new_ylim[0] < original_ylim[0]:
            print("Y range cannot go lower than the original minimum.")
            return
        if new_ylim[1] > original_ylim[1]:
            print("Y range cannot go higher than the original maximum.")
            return

        # Ensure new range is valid (Y-axis min should be less than max)
        if new_ylim[0] >= new_ylim[1]:
            print("Invalid Y range.")
            return

        selected_ylim = new_ylim
        update_plot()

    except ValueError:
        print("Please enter a valid shift amount.")

# Function to set Y-axis range
def set_y_range():
    global selected_ylim
    try:
        start_y = int(start_y_entry.get())
        end_y = int(end_y_entry.get())

        if start_y >= end_y:
            print("Invalid Y-axis range.")
            return

        selected_ylim = [start_y, end_y]
        update_plot()

    except ValueError:
        print("Please enter valid numbers for Y range.")

def on_closing():
    global running
    running = False  # Stop data acquisition
    root.quit()  # Exit main loop
    root.destroy()  # Destroy the window

# GUI Setup
button_frame = tk.Frame(root)
button_frame.pack(pady=5)

tk.Button(button_frame, text="Continuous", command=start_server).grid(row=0, column=0, padx=5, pady=5)
tk.Button(button_frame, text="Trigger Once", command=trigger_once).grid(row=0, column=1, padx=5, pady=5)
tk.Button(button_frame, text="Stop", command=stop_server).grid(row=0, column=2, padx=5, pady=5)

range_frame = tk.Frame(root)
range_frame.pack(pady=5)

# X-axis controls on the same line (X Start, X End, X Shift, Left, Right buttons)
tk.Label(range_frame, text="X Start:").grid(row=0, column=0)
start_sample_entry = tk.Entry(range_frame, width=10)
start_sample_entry.grid(row=0, column=1)

tk.Label(range_frame, text="X End:").grid(row=0, column=2)
end_sample_entry = tk.Entry(range_frame, width=10)
end_sample_entry.grid(row=0, column=3)

tk.Label(range_frame, text="X Shift:").grid(row=0, column=4)
shift_amount_entry = tk.Entry(range_frame, width=10)
shift_amount_entry.grid(row=0, column=5)
shift_amount_entry.insert(0, "100")

tk.Button(range_frame, text="Left", command=lambda: shift_x_range("left")).grid(row=0, column=6)
tk.Button(range_frame, text="Right", command=lambda: shift_x_range("right")).grid(row=0, column=7)

# Y-axis controls on the same line (Y Start, Y End, Y Shift, Up, Down buttons)
tk.Label(range_frame, text="Y Start:").grid(row=1, column=0)
start_y_entry = tk.Entry(range_frame, width=10)
start_y_entry.grid(row=1, column=1)

tk.Label(range_frame, text="Y End:").grid(row=1, column=2)
end_y_entry = tk.Entry(range_frame, width=10)
end_y_entry.grid(row=1, column=3)

tk.Label(range_frame, text="Y Shift:").grid(row=1, column=4)
shift_y_amount_entry = tk.Entry(range_frame, width=10)
shift_y_amount_entry.grid(row=1, column=5)
shift_y_amount_entry.insert(0, "100")

tk.Button(range_frame, text="Up", command=lambda: shift_y_range("up")).grid(row=1, column=6)
tk.Button(range_frame, text="Down", command=lambda: shift_y_range("down")).grid(row=1, column=7)

# Frame for Range Adjustment
range_button_frame = tk.Frame(root)
range_button_frame.pack(pady=5)

tk.Button(range_button_frame, text="Set X Range", command=set_x_range).grid(row=0, column=0, padx=5, pady=5)
tk.Button(range_button_frame, text="Original Size", command=reset_zoom).grid(row=0, column=1, padx=5, pady=5)
tk.Button(range_button_frame, text="Set Y Range", command=set_y_range).grid(row=0, column=2, padx=5, pady=5)

# Spike Count Display
spike_count_label = tk.Label(root, text="Spikes (A): 0   Spikes (B): 0", font=("Helvetica", 12))
spike_count_label.pack(pady=10)

# Matplotlib Canvas
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack(padx=5, pady=5)

root.protocol("WM_DELETE_WINDOW", on_closing)

# Start the GUI loop
root.mainloop()
