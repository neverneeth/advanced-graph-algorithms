import subprocess
import random
import csv
from pathlib import Path
import networkx as nx

base = Path(__file__).resolve().parent.parent.parent
data_dir = base / "datasets" / "tntp"
graph_file = data_dir / "goldcoast_network.txt"
results_dir = base / "results" / "logs"
results_dir.mkdir(parents=True, exist_ok=True)
csv_file = results_dir / "mcf_benchmark_results.csv"

# Binaries
cc_bin = base / "src" / "mincostflow" / "cyclecancel"
cs_bin = base / "src" / "mincostflow" / "capacity_scaling"

NUM_PAIRS = 50
RUNS_PER_PAIR = 5

def load_valid_nodes():
    """Loads the graph and returns nodes that are in the largest connected component."""
    G = nx.Graph()
    with open(graph_file, 'r') as f:
        header = f.readline().strip().split()
        if not header: return []
        
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 4:
                u, v = int(parts[0]), int(parts[1])
                G.add_edge(u, v)
                
    largest_cc = max(nx.connected_components(G), key=len)
    return list(largest_cc)

def run_experiment():
    print("Loading Gold Coast network to find connected components...")
    valid_nodes = load_valid_nodes()
    
    if len(valid_nodes) < 2:
        print("Error: Graph does not have enough connected nodes.")
        return

    print(f"Network loaded. Largest component has {len(valid_nodes)} nodes.")
    print("Starting Minimum Cost Flow benchmarks...")
    
    with open(csv_file, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Pair_ID", "Source", "Sink", "Target_Flow", "Algorithm", "Run", "Min_Cost", "Primary_Ops", "Time_us"])
        
        for pair_id in range(1, NUM_PAIRS + 1):
            source, sink = random.sample(valid_nodes, 2)
            # Random logistics demand between 100 and 1000 units
            target_flow = random.randint(100, 1000) 
            
            print(f"Testing Pair {pair_id}/{NUM_PAIRS} [Source: {source}, Sink: {sink}, Demand: {target_flow}]")
            
            for run in range(1, RUNS_PER_PAIR + 1):
                # Run Cycle-Canceling
                cc_res = subprocess.run(
                    [str(cc_bin), str(graph_file), str(source), str(sink), str(target_flow)],
                    capture_output=True, text=True
                )
                if cc_res.stdout.strip():
                    # Output: Source, Sink, Flow, Cost, Cycles_Canceled, Time
                    parts = cc_res.stdout.strip().split(',')
                    if len(parts) == 6 and parts[3] != "-1":
                        writer.writerow([pair_id, parts[0], parts[1], parts[2], "CycleCanceling", run, parts[3], parts[4], parts[5]])
                
                # Run Capacity Scaling
                cs_res = subprocess.run(
                    [str(cs_bin), str(graph_file), str(source), str(sink), str(target_flow)],
                    capture_output=True, text=True
                )
                if cs_res.stdout.strip():
                    # Output: Source, Sink, Flow, Cost, Augmentations, Time
                    parts = cs_res.stdout.strip().split(',')
                    if len(parts) == 6 and parts[3] != "-1":
                        writer.writerow([pair_id, parts[0], parts[1], parts[2], "CapacityScaling", run, parts[3], parts[4], parts[5]])
                        
    print(f"Experiments complete. Results saved to {csv_file}")

if __name__ == "__main__":
    run_experiment()