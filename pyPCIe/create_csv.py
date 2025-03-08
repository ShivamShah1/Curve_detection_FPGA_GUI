import struct
import os
import csv
import time

TRIGGER_REG = 0x0
BUSY_REG = 0x8
DACVALUE_REG = 0x10

def pcie_init():
    """ Initialize PCIe communication with the FPGA. """
    os.system("setpci -s 01:00.0 COMMAND=0x2")

    from pypcie import Device
    d = Device("0000:01:00.0")
    if not d:
        print("ERROR PCIE: Unable to open PCIe device")
        os.exit()
    print("PCIE: Initialized")

    return [d.bar[1], d.bar[0]]  # bar1 for samples, bar0 for control

def trigger(bar):
    """ Trigger FPGA to start data acquisition. """
    print("Trigger Initializing...")
    bar.write(DACVALUE_REG, 0x14)
    bar.write(TRIGGER_REG, 0x1)
    bar.write(TRIGGER_REG, 0x0)
    print(f"Trigger Done: {bar.read(TRIGGER_REG)}")

def busy_state(bar):
    """ Check if FPGA is still busy acquiring data. """
    return bar.read(BUSY_REG) & 0xFFFFFFFF

def generate_samples(bars, num_words):
    """ Acquire raw data samples from PCIe and split into Channel A & B. """
    samples_bar = bars[1]
    control_bar = bars[0]

    trigger(control_bar)
    while busy_state(control_bar):
        print("Acquisition busy...")

    raw_samples = []
    for word in range(num_words):
        word_offset = word * 4
        sample = samples_bar.read(word_offset) & 0xFFFFFFFF
        raw_samples.append(sample)

    # Convert 32-bit words into 16-bit Channel A & B
    channel_a = []
    channel_b = []

    for sample in raw_samples:
        word1 = sample & 0xFFFF        # Lower 16 bits (Channel A)
        word2 = (sample >> 16) & 0xFFFF  # Upper 16 bits (Channel B)
        channel_a.append(word1)
        channel_b.append(word2)

    return channel_a, channel_b

def save_to_csv(channel_a, channel_b, filename="pcie_samples.csv"):
    """ Save Channel A and Channel B data into a CSV file. """
    with open(filename, mode="a", newline="") as file:  # Append mode
        writer = csv.writer(file)
        for a, b in zip(channel_a, channel_b):
            writer.writerow([a, b])

    print(f"Data saved to {filename}")

# Main execution
if __name__ == "__main__":
    bars = pcie_init()
    num_samples = 16 * 1024  

    # Open CSV file and write headers only once
    with open("pcie_samples.csv", mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Channel A", "Channel B"])

    try:
        while True:
            # Collect and save new samples
            channel_a, channel_b = generate_samples(bars, num_samples)
            save_to_csv(channel_a, channel_b)

            # Delay between sample collection (optional)
            time.sleep(1)  # Adjust as necessary

    except KeyboardInterrupt:
        print("\n[INFO] Sampling stopped. Exiting...")
