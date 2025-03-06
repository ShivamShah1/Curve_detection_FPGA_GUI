from pypcie import Device
import struct

TRIGGER_REG = 0x0
BUSY_REG = 0x8

# Bind to PCI device at "0000:01:00.0"
d = Device("0000:01:00.0")
# Access BAR 0
bar0 = d.bar[0]
bar1 = d.bar[1]

bar = bar1
num_words = 16

# word_value = bar.write(0x00000000, 0xDEADBEEF)


def trigger():
    bar.write(TRIGGER_REG, 0x0)
    bar.write(TRIGGER_REG, 0xFFFFFFFF)
    bar.write(TRIGGER_REG, 0x0)


def busy_state():
    return bar.read(BUSY_REG) & 0xFFFFFFFF


print('REG 0x0 : ',bar.read(TRIGGER_REG))
print('REG 0x8 : ',bar.read(BUSY_REG))

# trigger()

import time
print('REG 0x8 : ',bar.read(BUSY_REG))
print('REG 0x8 : ',bar.read(BUSY_REG))
print('REG 0x8 : ',bar.read(BUSY_REG))
# bar.write(TRIGGER_REG, 0x1)

busy = 1

while(1):
    time.sleep(2)
    busy = 1
    bar.write(TRIGGER_REG, 0x1) # 1
    bar.write(TRIGGER_REG, 0x0) 
    
    while(busy):
        busy = bar.read(BUSY_REG)
        print('REG 0x8 Busy state now: ',busy)
    
        #time.sleep(5)
    
        #print('REG 0x0 Trigger: ',bar.read(TRIGGER_REG))

        #print('REG 0x8 after : ',bar.read(BUSY_REG))





# while(1):
#     input('------ press any key to trigger -------')
    
#     print('---- Trigger ---')
#     trigger()
    
#     while(busy_state()):
#         print(' ---- Acquiring ----')





# for word in range(num_words):
#     word_offset = word*4
#     #bar0.write(word_offset, word*8)

#     word_value = bar.write(word_offset, word+1)
#     # read BAR 0, offset 0x1004
#     word_value = bar.read(word_offset) & 0xFFFFFFFF
    
    
#     print(hex(word_value))
    
#     #print("Word at Offset: ", f"{word_offset:04x}  ", ('_'.join([f"{word_value:08x}"[i:i+4] for i in range(0, 8, 4)])))




# """
# for word in range(num_words):
#     word_offset = word*4
#     #bar1.write(word_offset, word*8)

#     # read BAR 0, offset 0x1004
#     word_value = bar1.read(word_offset)

    
#     print(f"Word {word} at offset {word_offset}: {hex(word_value)}")
# """ 
