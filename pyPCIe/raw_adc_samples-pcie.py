from pypcie import Device
import struct


# Bind to PCI device at "0000:01:00.0"
d = Device("0000:01:00.0")
# Access BAR 0
bar0 = d.bar[0]
bar1 = d.bar[1]

bar = bar0

num_words = 16

for word in range(num_words):
    word_offset = word*4
    #bar0.write(word_offset, word*8)

    # read BAR 0, offset 0x1004
    word_value = bar.read(word_offset) & 0xFFFFFFFF
    print(hex(word_value))
    
    #print("Word at Offset: ", f"{word_offset:04x}  ", ('_'.join([f"{word_value:08x}"[i:i+4] for i in range(0, 8, 4)])))




"""
for word in range(num_words):
    word_offset = word*4
    #bar1.write(word_offset, word*8)

    # read BAR 0, offset 0x1004
    word_value = bar1.read(word_offset)

    
    print(f"Word {word} at offset {word_offset}: {hex(word_value)}")
""" 
