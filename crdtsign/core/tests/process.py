import json
import os
from datetime import datetime
from glob import glob
from pathlib import Path

import click

json_files = list(Path('./artifacts/').glob('*.json'))

scale = len(json_files) - 1

# Initialize variables
write_start_time = None
remove_start_time = None
write_times = []
remove_times = []
valid_count = 0

# Process all JSON files
for json_file in json_files:
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)

        # Check if this is a writer node
        if data.get('node_type') == 'writer':
            write_start_timestamp = data.get('write_start_time')
            remove_start_timestamp = data.get('remove_start_time')

            # Parse datetime strings
            if write_start_timestamp:
                write_start_time = datetime.fromisoformat(write_start_timestamp)
            if remove_start_timestamp:
                remove_start_time = datetime.fromisoformat(remove_start_timestamp)

        # Check if this is a reader node
        elif data.get('node_type') == 'reader':
            # Count valid validation outcomes
            if data.get('validation_outcome') == 'valid':
                valid_count += 1

            # Collect write and remove times for elapsed time calculation
            if 'write_time' in data:
                write_times.append(datetime.fromisoformat(data['write_time']))
            if 'remove_time' in data:
                remove_times.append(datetime.fromisoformat(data['remove_time']))

    except (json.JSONDecodeError, IOError) as e:
        print(f"Error processing {json_file}: {e}")
        continue
    
# Calculate elapsed times
elapsed_write_time = None
elapsed_remove_time = None

if write_start_time and write_times:
    elapsed_write_time = str(max(write_times) - write_start_time)

if remove_start_time and remove_times:
    elapsed_remove_time = str(max(remove_times) - remove_start_time)

# Create output data
output_data = {
    'scale': scale,
    'elapsed_write_time': elapsed_write_time,
    'elapsed_remove_time': elapsed_remove_time,
    'valid_count': valid_count
}


print(f"Scale: {scale}")
print(f"Elapsed write time: {elapsed_write_time}")
print(f"Elapsed remove time: {elapsed_remove_time}")
print(f"Valid count: {valid_count}")

for fname in glob("artifacts/user_*.json"):
    os.unlink(fname)

if click.confirm("Save to file?"):
    output_filename = f"{write_start_time}.json"

    # Save to JSON file
    with open(f"./artifacts/processed/{output_filename}", 'w') as f:
        json.dump(output_data, indent=2, fp=f)

    print(f"Results saved to {output_filename}")