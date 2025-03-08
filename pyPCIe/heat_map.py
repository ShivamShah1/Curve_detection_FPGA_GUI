import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Load the CSV data
filename = "pcie_samples.csv"
df = pd.read_csv(filename)

# Verify if the CSV is loaded correctly
print(df.head())  # This should print the first few rows of the CSV to check the data

# Extract Channel A and Channel B data
channel_a = df["Channel A"].values
channel_b = df["Channel B"].values

# Check the length of the data
print(f"Length of Channel A data: {len(channel_a)}")
print(f"Length of Channel B data: {len(channel_b)}")

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

# Create time values for 4 seconds (0, 1, 2, 3)
time_values = np.arange(4)

# Function to normalize data and clip values outside the range [2000, 4100]
def normalize_and_clip_data(data, min_val=2000, max_val=4100):
    # Clip values outside the range and normalize
    clipped_data = np.clip(data, min_val, max_val)
    normalized_data = (clipped_data - min_val) / (max_val - min_val)
    return normalized_data

# Normalize and clip data for Channel A and Channel B
channel_a_normalized = normalize_and_clip_data(channel_a)
channel_b_normalized = normalize_and_clip_data(channel_b)

# Plotting Heatmap for Channel A
plt.figure(figsize=(12, 6))
sns.heatmap(channel_a_normalized, cmap="coolwarm", cbar=True, xticklabels=np.arange(1, 5), yticklabels=np.arange(1, samples_per_second + 1))
plt.title("Channel A - Heatmap of Samples Over Time")
plt.xlabel("Time (seconds)")
plt.ylabel("Sample Index (0 - 16KB)")
plt.tight_layout()
plt.show()

# Plotting Heatmap for Channel B
plt.figure(figsize=(12, 6))
sns.heatmap(channel_b_normalized, cmap="coolwarm", cbar=True, xticklabels=np.arange(1, 5), yticklabels=np.arange(1, samples_per_second + 1))
plt.title("Channel B - Heatmap of Samples Over Time")
plt.xlabel("Time (seconds)")
plt.ylabel("Sample Index (0 - 16KB)")
plt.tight_layout()
plt.show()
