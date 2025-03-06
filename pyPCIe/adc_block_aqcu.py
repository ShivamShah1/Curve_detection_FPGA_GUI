from pypcie import Device
import struct
import sys

#get samples / block 

num_words = 16
num_words = int(sys.argv[1])

# Bind to PCI device at "0000:01:00.0"
d = Device("0000:01:00.0")
# Access BAR 0
bar0 = d.bar[0]
bar1 = d.bar[1]

bar = bar0



for word in range(num_words):
    word_offset = word*4
    #bar.write(word_offset, word*8)

    # read BAR 0, offset 0x1004
    word_value = bar.read(word_offset) & 0xFFFFFFFF

samples_32bit = []

# Convert 64-bit samples to 32-bit samples
for word in range(num_words):
    word_offset = word*4
    #bar.write(word_offset, word*8)

    # read BAR 0, offset 0x1004
    sample = bar.read(word_offset) & 0xFFFFFFFF
    print(hex(sample))
    # Extract the lower 32 bits (word1)
    word1 = sample & 0xFFFF
    # Extract the upper 32 bits (word2)
    word2 = (sample >> 16) & 0xFFFF

    # Append word1 and word2 to the list
    samples_32bit.extend([hex(word1), hex(word2)])

# Now samples_32bit contains all the 32-bit samples
print(samples_32bit)


    
    #print("Word at Offset: ", f"{word_offset:04x}  ", ('_'.join([f"{word_value:08x}"[i:i+4] for i in range(0, 8, 4)])))
    #print(('_'.join([f"{word_value:08x}"[i:i+4] for i in range(0, 8, 4)])))
