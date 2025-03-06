#!/bin/bash

# Define the files
FILES=(
    "/sys/bus/pci/devices/0000:01:00.0/config"
    "/sys/bus/pci/devices/0000:01:00.0/resource1"
    "/sys/bus/pci/devices/0000:01:00.0/resource0"
)

# Loop through each file and change permissions if it exists
for FILE in "${FILES[@]}"; do
    if [ -e "$FILE" ]; then
        chmod 666 "$FILE"
        echo "Permissions set for $FILE"
    else
        echo "Skipping $FILE (not found)"
    fi
done
