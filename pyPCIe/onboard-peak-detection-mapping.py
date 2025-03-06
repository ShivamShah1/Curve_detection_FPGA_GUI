#!/usr/bin/python

import socket
import threading
import random
import wavelength_table
import numpy as np
from scipy.signal import find_peaks

from pypcie import Device
import struct
import sys
import signal
import struct
import os,time

TRIGGER_REG = 0x0
BUSY_REG    = 0x8

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
    return [bar1,bar0]

def trigger(bar):
    #bar.write(TRIGGER_REG, 0x0)
    bar.write(TRIGGER_REG, 0x1)
    bar.write(TRIGGER_REG, 0x0)
    print("Trigger Done..... ")


def busy_state(bar):
    return bar.read(BUSY_REG) & 0xFFFFFFFF


def est(tt1, tt2, cc):
    sig = tt1[:4000]
    sqw = tt2[:4000]
    
    #print("Signal  :", sig[:10])
    #print("Trigger :", sqw[:10])

    df = np.diff(sqw)
    edg = np.where(df > 400)[0]
    e_loc1 = edg[0]

    val_loc1 = e_loc1 + 650
    val_loc2 = e_loc1 + 1250

    # reset start index,  based on sqw pos edge
    #this will make wavelength matching correct
    sig_rebase = tt1[e_loc1-1:]
    sqw_rebase = tt2[e_loc1-1:]    

    df = np.diff(sqw_rebase)
    edg = np.where(df > 400)[0]
    e_loc1_rebase = edg[0]
    
    print("Edge locs rebased: ",e_loc1_rebase,edg)
    print("Edge locs orignal: ",e_loc1)

    val_loc1_rebase = e_loc1_rebase + 650
    val_loc2_rebase = e_loc1_rebase + 1250

    pks_locs, peaks = find_peaks(sig, height=2200)
    pks_locs_rebase, peaks_rebase = find_peaks(sig_rebase, height=2200)

    # Accessing the 'peak_heights' array from the peak_hiegts dictionary
    peak_heights = peaks['peak_heights']


    
    #print("e_loc1",e_loc1)
    #print("val_loc1",val_loc1)
    #print("val_loc2",val_loc2)
    idx1 = np.where((pks_locs > val_loc1) & (pks_locs < val_loc2))[0]
    print("peak _heights[idx1]",idx1, peak_heights[idx1])


    idx1_rebase = np.where((pks_locs_rebase > val_loc1_rebase) & (pks_locs_rebase < val_loc2_rebase))[0]
    print("peak _heights[idx1]",idx1, peak_heights[idx1_rebase])

    #print("pks_val",pks_val,idx1,e_loc1)
    wave_loc1 = pks_locs[idx1][0]
    wave_loc2 = pks_locs[idx1][1]
    print("Wave locs: ", wave_loc1,wave_loc2)


    wave_loc1_rebase = pks_locs_rebase[idx1_rebase][0]
    wave_loc2_rebase = pks_locs_rebase[idx1_rebase][1]
    print("Wave locs: ", wave_loc1_rebase,wave_loc2_rebase)


    if wave_loc2_rebase < 1600: 
        print("---------- Detected on First  Trigger Window -----")
        wv_val = [cc[wave_loc1_rebase], cc[wave_loc2_rebase]]
        print(" Detected Wave_lengths : ",wv_val)
    else:
        print("---------- Detected on Second Trigger Window -----")
        wv_val = [0, 0]
        print(" Detected Wave_lengths : ",wv_val)


    edg_window = [val_loc1, val_loc2]
    
    return wv_val, pks_locs[idx1], peak_heights[idx1], edg_window



# Function to generate a list of hex samples received though PCI interface
def acqire_adc_samples(bars, num_words):

    # Convert 32-bit samples to 16-bit samples
    sample_32bit  = []
    samples_signal = []
    samples_triger = []

    control_bar = bars[0]
    samples_bar = bars[1]

    #this will trigger fpga bram to store adc samples
    trigger(control_bar)

    #wait if fpga busy
    while(busy_state(control_bar)):
        print("FPGA Acquazition busy !!!")

    for word in range(num_words):
        word_offsetA = word*4
        
        # read BAR 0, offset 0x1004
        sample_32bit = samples_bar.read(word_offsetA) & 0xFFFFFFFF

        
        # Extract two 16-bit values from the 32-bit sample
        sample_signal = (sample_32bit >> 16) & 0xFFFF
        sample_triger = sample_32bit & 0xFFFF
        
        # Append to respective lists
        samples_signal.append(sample_signal)
        samples_triger.append(sample_triger)
            
    return (samples_signal,samples_triger)

# Function to handle the client connection
def handle_client(bars):
    while True:
        #hex_samples = acqire_adc_samples(bar,256)
        [samples_signal,samples_triger] = acqire_adc_samples(bars, 1 * 1024)
        #print("----------------------------------------------")
        #print('Signal   :',samples_signal[:1000])



        for sample in samples_signal[:10]:
            plot_char_count = int(sample)  # Use the sample value directly
            plot_chars = '.' * round(plot_char_count / 100)  # Character representing the plot
                                
            print(plot_chars)


        print("----------------------------------------------")


        #print("----------------------------------------------")
        #print('Trigger  :',samples_triger[:100])

        #wv_val, pk_indexes, peak_hiegts, sqw_locs = est(samples_signal, samples_triger, wavelength_table.cc)

        #print("Samples Acquired from PCIE: ", len(samples_signal) // 2)
        time.sleep(1)


# Signal handler for Ctrl+C
def signal_handler(sig, frame):
    print("\n[Signal] Shutting down gracefully.")
    sys.exit(0)

# Main server code
#server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#server.bind(('192.168.0.240', 12345))
#server.bind(('127.0.0.1', 12345))
#server.listen(5)

#print('[Server] Listening for connections...')

signal.signal(signal.SIGINT, signal_handler)







while True:
    try:
        #client, addr = server.accept()
        #print(f'[Server] Accepted connection from {addr[0]}:{addr[1]}')

        bars = pcie_init()

        input("Press key to acquire and peak detect")
        
        client_handler = threading.Thread(target=handle_client, args=(bars,))
        client_handler.start()

    except KeyboardInterrupt:
        print("\n[Server] Shutting down gracefully.")
        #server.close()
        sys.exit(0)
         
