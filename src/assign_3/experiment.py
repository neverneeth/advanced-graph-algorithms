import subprocess
import csv
import os
from pathlib import Path

# Paths
base = Path(__file__).resolve().parent.parent.parent
data_dir = base / "datasets" / "snap"
original_graph = data_dir / "google_web_graph.txt"
temp_graph = data_dir / "temp_subgraph.txt"

results_dir = base / "results" / "logs"
results_dir.mkdir(parents=True, exist_ok=True)
csv_file = results_dir / "scc_benchmark_results.csv"

# Binaries
tarjan_bin = base / "src" / "stronglycc" / "tarjan"
kosaraju_bin = base / "src" / "stronglycc" / "kosaraju"

# Benchmark fractions (20%, 40%, 60%, 80%, 100%)
fractions = [0.2, 0.4, 0.6, 0.8, 1.0]
RUNS_PER_SIZE = 3

def generate_subgraph(fraction, total_nodes):
    """Generates an induced subgraph containing a fraction of the total nodes."""
    node_limit = int(total_nodes * fraction)
    print(f"\nGenerating subgraph with nodes 0 to {node_limit - 1} ({int(fraction*100)}% scale)...")
    
    edges = []
    with open(original_graph, 'r') as f:
        f.readline() # Skip header
        for line in f:
            u, v = map(int, line.strip().split())
            if u < node_limit and v < node_limit:
                edges.append((u, v))
                
    with open(temp_graph, 'w') as f:
        f.write(f"{node_limit} {len(edges)}\n")
        for u, v in edges:
            f.write(f"{u} {v}\n")
            
    return node_limit, len(edges)

def run_experiment():
    # 1. Read original graph size
    with open(original_graph, 'r') as f:
        header = f.readline().strip().split()
        total_nodes = int(header[0])
        total_edges = int(header[1])
        
    print(f"Original Graph: {total_nodes} nodes, {total_edges} edges")
    
    with open(csv_file, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Algorithm", "Scale_Pct", "Nodes", "Edges", "SCC_Count", "Max_SCC", "Traversals", "Time_us", "Memory_KB"])
        
        for frac in fractions:
            nodes, edges = generate_subgraph(frac, total_nodes)
            
            for run in range(1, RUNS_PER_SIZE + 1):
                print(f"  Run {run}/{RUNS_PER_SIZE} for {int(frac*100)}% scale...")
                
                for algo, binary in [("Tarjan", tarjan_bin), ("Kosaraju", kosaraju_bin)]:
                    # Use /usr/bin/time -f "%M" to extract peak memory in KB
                    cmd = ["/usr/bin/time", "-f", "%M", str(binary), str(temp_graph)]
                    
                    res = subprocess.run(cmd, capture_output=True, text=True)
                    
                    # Output from C++ is on stdout
                    # Output from time is on stderr
                    if res.stdout.strip() and res.stderr.strip():
                        # C++ Output: Algorithm, V, E, SCC_Count, Max_SCC_Size, Edge_Traversals, Time_us
                        parts = res.stdout.strip().split(',')
                        mem_kb = res.stderr.strip().split('\n')[-1] # The last line of stderr is the memory
                        
                        writer.writerow([
                            parts[0], int(frac*100), parts[1], parts[2], 
                            parts[3], parts[4], parts[5], parts[6], mem_kb
                        ])
                        
    if temp_graph.exists():
        os.remove(temp_graph)
        
    print(f"\nExperiments complete. Results saved to {csv_file}")

if __name__ == "__main__":
    run_experiment()