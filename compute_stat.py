import os
import pandas as pd
import argparse
import numpy as np
import matplotlib.pyplot as plt

# Set argument parser
parser = argparse.ArgumentParser(description='compute_statistics')
parser.add_argument('--input_file', type=str, nargs='+', default="my.log")
parser.add_argument('--output_dir', type=str, nargs='+', default=".")
parser.add_argument('--output_filename', type=str, default="test.csv")

args = parser.parse_args()
input_file = args.input_file
if len(input_file) != 1:
    input_file = " ".join(input_file)
else:
    input_file = input_file[0]
output_dir = args.output_dir
if len(output_dir) != 1:
    output_dir = " ".join(output_dir)
else:
    output_dir = output_dir[0]
output_filename = args.output_filename

output_filepath = os.path.join(output_dir, output_filename)

# load data using Python JSON module
with open(input_file, 'r') as f:
    data = f.readlines()

processing_name = ["Georeferencing", "DEM", "Rectify", "Write", "Total"]
processing_time = np.empty(shape=(len(data), 5))
for i in range(len(data)):
    line = data[i].split(" ")
    processing_time[i, 0] = float(line[3])  # Georeferencing
    processing_time[i, 1] = float(line[4])  # DEM
    processing_time[i, 2] = float(line[5])  # Rectify
    processing_time[i, 3] = float(line[6])  # Write
    processing_time[i, 4] = float(line[7])  # Total

min_time = np.min(processing_time, axis=0)
max_time = np.max(processing_time, axis=0)
average_time = np.average(processing_time, axis=0)
std_time = np.std(processing_time, axis=0)
stat_time = np.stack((min_time, max_time, average_time, std_time), axis=0)

# Plot the graph
fig = plt.figure()
plt.plot(processing_name, average_time, label='Average')
plt.title('Average processing time')
plt.legend(loc='best')
plt.show()

df = pd.DataFrame(stat_time, index=["Min", "Max", "Ave.", "Std."], columns=processing_name)
print(df)

# Saving to CSV format
df.to_csv(output_filepath, index=False)