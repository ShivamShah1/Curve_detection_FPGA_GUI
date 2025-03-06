import socket
import threading
import random
from pypcie import Device
import struct
import sys
import os

TRIGGER_REG = 0x0
BUSY_REG = 0x8

def pcie_init():
    os.system("setpci -s 01:00.0 COMMAND=0x2")
    
    d = Device("0000:01:00.0")
    if not d:
        print("ERROR PCIE : unable to open pcie device")
        sys.exit()
    print("PCIE : Initialized")

    bar0 = d.bar[0]
    bar1 = d.bar[1]
    return [bar1, bar0]

def trigger(bar):
    print("Triggering FPGA...")
    bar.write(TRIGGER_REG, 0x1)
    bar.write(TRIGGER_REG, 0x0)
    print(f"Trigger Completed. Status: {bar.read(TRIGGER_REG)}")

def busy_state(bar):
    return bar.read(BUSY_REG) & 0xFFFFFFFF

def generate_large_data():
    # Generate a large dataset (64K bytes)
    data = bytearray(random.getrandbits(8) for _ in range(64 * 1024))
    return data

def generate_fresh_samples(bars, num_words):
    control_bar = bars[0]
    samples_bar = bars[1]
    
    # Trigger FPGA to collect new samples
    trigger(control_bar)
    while busy_state(control_bar):
        print("Acquisition busy...")
    
    # Flush old data by reinitializing the sample array
    sample_array = bytearray()
    
    for word in range(num_words):
        word_offset = word * 4
        sample = samples_bar.read(word_offset) & 0xFFFFFFFF
        packed_sample = struct.pack('<i', (sample & 0xFFFFFFFF))  # Convert 32-bit sample
        sample_array.extend(packed_sample)
    
    return sample_array

def handle_client(client_socket, bars):
    while True:
        data = client_socket.recv(1024).decode('utf-8')
        if not data:
            break
        
        print("Request received from client.")
        
        # Generate fresh data every time before sending
        fresh_samples = generate_fresh_samples(bars, 16 * 1024)
        print("New Samples Acquired: ", len(fresh_samples) // 2)
        
        client_socket.sendall(fresh_samples)
        
        # Debugging: Print first few samples
        num_samples = len(fresh_samples) // 2  
        int_samples_list = list(struct.unpack(f'{num_samples}H', fresh_samples))
        print("First 20 Samples:", int_samples_list[:20])
    
    client_socket.close()

# Server setup
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('192.168.0.240', 12345))
server.listen(5)
print('[Server] Listening for connections...')

try:
    while True:
        client, addr = server.accept()
        print(f'[Server] Accepted connection from {addr[0]}:{addr[1]}')
        bars = pcie_init()
        client_handler = threading.Thread(target=handle_client, args=(client, bars,))
        client_handler.start()
except KeyboardInterrupt:
    print("\n[Server] Shutting down gracefully.")
    server.close()
    sys.exit(0)
