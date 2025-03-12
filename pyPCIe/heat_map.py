import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import time

# Load the CSV data
filename = "pcie_samples.csv"
df = pd.read_csv(filename)

# Extract Channel A and Channel B data
channel_a = df["Channel A"].values
channel_b = df["Channel B"].values

# Number of samples per second (16KB of data per second)
samples_per_second = 16 * 1024  # 16KB = 16 * 1024 samples

# Ensure the data length matches the expected number of samples (4 seconds of data, 16KB per second)
expected_length = 4 * samples_per_second  # 4 seconds of data, 16KB per second

# Trim data to match the expected length (if there's extra data)
channel_a = channel_a[:expected_length]
channel_b = channel_b[:expected_length]

# Reshape the data into 4 seconds, each containing 16KB of data (16KB samples)
channel_a = channel_a.reshape(4, samples_per_second)
channel_b = channel_b.reshape(4, samples_per_second)

# Function to normalize data and clip values outside the range [2000, 4100]
def normalize_and_clip_data(data, min_val=2000, max_val=4100):
    # Clip values outside the range and normalize
    clipped_data = np.clip(data, min_val, max_val)
    normalized_data = (clipped_data - min_val) / (max_val - min_val)
    return normalized_data

# Normalize and clip data for Channel A and Channel B
channel_a_normalized = normalize_and_clip_data(channel_a)
channel_b_normalized = normalize_and_clip_data(channel_b)

# Create time values for 4 seconds (0, 1, 2, 3)
time_values = np.arange(4)

# Plotting Channel A and Channel B gradually

for i in range(4):  # Loop over each second (4 time slices)
    # Plotting Heatmap for Channel A
    plt.figure(figsize=(12, 8))  # Increase figure size for clarity
    sns.heatmap(channel_a_normalized[:i+1], cmap="coolwarm", cbar=True,
                xticklabels=5, yticklabels=100, cbar_kws={'label': 'Normalized Value'})
    plt.title(f"Channel A - Heatmap of Samples Over Time (First {i+1} Seconds)")
    plt.xlabel("Sample Index (0 - 16KB)")
    plt.ylabel("Time (Seconds)")
    plt.tight_layout()
    plt.show()  # Display plot

    # Add delay of 0.5 seconds before showing the next heatmap
    time.sleep(0.5)

    # Plotting Heatmap for Channel B
    plt.figure(figsize=(12, 8))  # Increase figure size for clarity
    sns.heatmap(channel_b_normalized[:i+1], cmap="coolwarm", cbar=True,
                xticklabels=5, yticklabels=100, cbar_kws={'label': 'Normalized Value'})
    plt.title(f"Channel B - Heatmap of Samples Over Time (First {i+1} Seconds)")
    plt.xlabel("Sample Index (0 - 16KB)")
    plt.ylabel("Time (Seconds)")
    plt.tight_layout()
    plt.show()  # Display plot

    # Add delay of 0.5 seconds before showing the next heatmap
    time.sleep(0.5)
