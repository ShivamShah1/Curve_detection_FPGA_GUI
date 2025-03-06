file_path = '/sys/bus/pci/devices/0000:01:00.0/config'

try:
    file = open(file_path, 'r')  # 'r' for reading, 'w' for writing, 'a' for appending
    # Perform operations on the file (e.g., read or write)
    file_content = file.read()
    print(file_content)
except FileNotFoundError:
    print(f"Error: File not found at {file_path}")
finally:
    if 'file' in locals():
        file.close()