import subprocess
import random
import csv
from pathlib import Path

# Paths
base = Path(__file__).resolve().parent.parent.parent
data_dir = base / "datasets" / "caida"
src_dir = base / "src" / "maxflow"
results_dir = base / "results" / "logs"

graph_file = data_dir / "caida_bandwidth_graph.txt"
csv_output = results_dir / "maxflow_benchmark_results.csv"

# Ensure directories exist
results_dir.mkdir(parents=True, exist_ok=True)

# Configuration
NUM_PAIRS = 50       # Number of different Source-Sink pairs to test
RUNS_PER_PAIR = 5    # How many times to test each pair to average out CPU noise
V_COUNT = 0          # Will be read from the graph file

def compile_cpp():
    print("Compiling C++ binaries with -O3 optimizations...")
    # Compile Dinic
    subprocess.run(["g++", "-O3", "-std=c++17", src_dir / "dinic.cpp", "-o", src_dir / "dinic"], check=True)
    # Compile Push-Relabel
    subprocess.run(["g++", "-O3", "-std=c++17", src_dir / "pushrelabel.cpp", "-o", src_dir / "pushrelabel"], check=True)
    print("Compilation successful.")

def get_node_count():
    with open(graph_file, 'r') as f:
        first_line = f.readline().strip().split()
        return int(first_line[0])

def run_binary(binary_path, source, sink):
    result = subprocess.run(
        [str(binary_path), str(graph_file), str(source), str(sink)],
        capture_output=True, text=True, check=True
    )
    # Parse the CSV output from C++ stdout
    parts = result.stdout.strip().split(',')
    return {
        "maxflow": int(parts[2]),
        "ops_1": int(parts[3]), # BFS for Dinic, Push for PR
        "ops_2": int(parts[4]), # DFS for Dinic, Relabel for PR
        "time_us": int(parts[5])
    }

def run_experiments():
    compile_cpp()
    
    global V_COUNT
    V_COUNT = get_node_count()
    print(f"Graph loaded with {V_COUNT} nodes. Starting experiments...")

    # Open CSV for logging
    with open(csv_output, 'w', newline='') as csvfile:
        fieldnames = ['Algorithm', 'Source', 'Sink', 'Run_Index', 'maxflow', 'Primary_Ops', 'Secondary_Ops', 'Time_us']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for pair_idx in range(1, NUM_PAIRS + 1):
            # Select random distinct source and sink
            source = random.randint(0, V_COUNT - 1)
            sink = random.randint(0, V_COUNT - 1)
            while sink == source:
                sink = random.randint(0, V_COUNT - 1)

            print(f"Testing Pair {pair_idx}/{NUM_PAIRS} [Source: {source}, Sink: {sink}]")

            for run_idx in range(1, RUNS_PER_PAIR + 1):
                # Run Dinic
                dinic_res = run_binary(src_dir / "dinic", source, sink)
                writer.writerow({
                    'Algorithm': 'Dinic', 'Source': source, 'Sink': sink, 
                    'Run_Index': run_idx, 'maxflow': dinic_res["maxflow"],
                    'Primary_Ops': dinic_res["ops_1"], 'Secondary_Ops': dinic_res["ops_2"],
                    'Time_us': dinic_res["time_us"]
                })

                # Run Push-Relabel
                pr_res = run_binary(src_dir / "pushrelabel", source, sink)
                writer.writerow({
                    'Algorithm': 'PushRelabel', 'Source': source, 'Sink': sink, 
                    'Run_Index': run_idx, 'maxflow': pr_res["maxflow"],
                    'Primary_Ops': pr_res["ops_1"], 'Secondary_Ops': pr_res["ops_2"],
                    'Time_us': pr_res["time_us"]
                })

                # Verification check to ensure correctness across all runs
                if dinic_res["maxflow"] != pr_res["maxflow"]:
                    print(f"WARNING: Max flow mismatch at S:{source} T:{sink}! Dinic: {dinic_res['maxflow']}, PR: {pr_res['maxflow']}")

    print(f"Experiments complete. Results saved to {csv_output}")

if __name__ == "__main__":
    run_experiments()