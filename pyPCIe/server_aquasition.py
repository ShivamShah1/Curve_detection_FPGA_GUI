import socket
import threading
import random

from pypcie import Device
import struct
import sys
import signal
import struct
import os

TRIGGER_REG = 0x0
BUSY_REG    = 0x8
DACVALUE_REG = 0x10

def pcie_init():
    # Bind to PCI device at "0000:01:00.0"
    # this commnad will initialize fpga pci channel
    os.system("setpci -s 01:00.0 COMMAND=0x2")
    
    
    d = Device("0000:01:00.0")
    if not d:
        print("ERROR PCIE : unable to open pcie device")
        os.exit()
    print("PCIE : Initialized")

    # Access BAR 0
    bar0 = d.bar[0]
    bar1 = d.bar[1]

    #bar = bar0
    #bar0 for regiters
    #bar1 for sample
    return [bar1,bar0]

def trigger(bar):
    print("Trigger Initial.....")
    bar.write(DACVALUE_REG, 0x64)
    bar.write(TRIGGER_REG, 0x1)
    bar.write(TRIGGER_REG, 0x0)
    #bar.write(TRIGGER_REG, 0x1)
    print(f"Trigger Done1..... {bar.read(TRIGGER_REG)}")


def busy_state(bar):
    return bar.read(BUSY_REG) & 0xFFFFFFFF

def generate_large_data():
    # Generate a large dataset (64K bytes)
    data = bytearray(random.getrandbits(8) for _ in range(64 * 1024))
    return data

# Function to generate a list of hex samples received though PCI interface
def generate_hex_samples(bars, num_words):

    # Convert 32-bit samples to 16-bit samples
    samples_32bit = []
    sample_array = bytearray()

    control_bar = bars[0]
    print(f'control - {control_bar}')
    samples_bar = bars[1]
    print(f'sample - {samples_bar}')

    #this will trigger fpga bram to store adc samples
    trigger(control_bar)
    while(busy_state(control_bar)):
        print("Aquazition busy !!!")

    for word in range(num_words):
        word_offsetA = word*4
        word_offsetB = word*1
        #bar.write(word_offset, word*8)
        
        # read BAR 0, offset 0x1004
        sampleA = samples_bar.read(word_offsetA) & 0xFFFFFFFF
        packed_sample_chA = struct.pack('<i', (sampleA & 0xFFFFFFFF))
        
        #sample = bar.read(word_offsetB) & 0xFFFFFFFF
        #packed_sample_chB = struct.pack('<i', sample)
       
        sample_array.extend(packed_sample_chA)

        """
        #print(hex(sample))
        # Extract the lower 32 bits (word1)
        word1 = sample & 0xFFFF
        # Extract the upper 32 bits (word2)
        word2 = (sample >> 16) & 0xFFFF

        # Append word1 and word2 to the list
        samples_32bit.extend( [word1, word2])

        # Now samples_32bit contains all the 32-bit samples
        """
    #print(samples_32bit)
    #return (samples_32bit)
    return (sample_array)

# Function to handle the client connection
def handle_client(client_socket,bars):
    while True:
        data = client_socket.recv(1*1024).decode('utf-8')
        print(data)
        if not data:
            break

        if data == 's':
            #hex_samples = generate_hex_samples(bar,256)
            packed_samples = generate_hex_samples(bars, 16 * 1024)
            #print(hex_samples)
            print("Samples Acquared from PCIE: ", len(packed_samples) // 2)
            #response = ','.join(hex_samples)
            #client_socket.send(response.encode('utf-8'))

            client_socket.sendall(packed_samples)


    client_socket.close()

# Signal handler for Ctrl+C
def signal_handler(sig, frame):
    print("\n[Signal] Shutting down gracefully.")
    sys._exit(0)

# Main server code
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('192.168.0.240', 22222))
#server.bind(('192.168.0.46', 12345))
#server.bind(('127.0.0.1', 12345))
server.listen(5)

print('[Server] Listening for connections...')

#signal.signal(signal.SIGINT, signal_handler)

try:
    while True:

        client, addr = server.accept()
        print(f'[Server] Accepted connection from {addr[0]}:{addr[1]}')
        bars = pcie_init()
        
        client_handler = threading.Thread(target=handle_client, args=(client,bars,))
        client_handler.start()

except KeyboardInterrupt:
    print("\n[Server] Shutting down gracefully.")
    server.close()
    sys.exit(0)