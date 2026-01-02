import json
import statistics
from datetime import datetime
from glob import glob

add_latencies = []
remove_latencies = []

for file in glob("artifacts/processed/*.json"):
    with open(file, "rb") as f:
        data = json.load(f)
    add_latencies.append(float(data["elapsed_write_time"].split(":")[-1]) * 1000)
    remove_latencies.append(float(data["elapsed_remove_time"].split(":")[-1]) * 1000)
    
print("\n# WRITE TIME")
print(f"Avg: {statistics.mean(add_latencies)} ms")
print(f"P99: {sorted(add_latencies)[int(len(add_latencies)*0.99)]} ms")

print("\n# REMOVE TIME")
print(f"Avg: {statistics.mean(remove_latencies)} ms")
print(f"P99: {sorted(remove_latencies)[int(len(remove_latencies)*0.99)]} ms")
