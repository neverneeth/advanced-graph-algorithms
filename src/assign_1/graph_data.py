import networkx as nx
import numpy as np
from pathlib import Path

# Paths
base = Path(__file__).resolve().parent.parent.parent
data_dir = base / "datasets" / "caida"
graph_file = data_dir / "caida_bandwidth_graph.txt"

def analyze_graph():
    print(f"Loading graph from {graph_file}...")
    
    G = nx.Graph()
    capacities = []
    
    with open(graph_file, 'r') as f:
        # Read header (V E)
        header = f.readline().strip().split()
        expected_nodes = int(header[0])
        expected_edges = int(header[1])
        
        # Parse edges
        for line in f:
            u, v, cap = map(int, line.strip().split())
            G.add_edge(u, v, capacity=cap)
            capacities.append(cap)
            
    # --- Calculate Metrics ---
    num_nodes = G.number_of_nodes()
    num_edges = G.number_of_edges()
    
    # Degrees
    degrees = [deg for node, deg in G.degree()]
    avg_degree = np.mean(degrees)
    max_degree = np.max(degrees)
    
    # Topology
    density = nx.density(G)
    num_components = nx.number_connected_components(G)
    largest_cc_size = len(max(nx.connected_components(G), key=len))
    
    # Capacities
    avg_cap = np.mean(capacities)
    max_cap = np.max(capacities)
    
    print("\n=========================================")
    print("      GRAPH TOPOLOGY INSIGHTS            ")
    print("=========================================")
    print(f"Total Nodes (V)      : {num_nodes}")
    print(f"Total Edges (E)      : {num_edges}")
    print(f"Graph Density        : {density:.6f}")
    print(f"Connected Components : {num_components}")
    print(f"Largest Component    : {largest_cc_size} nodes ({largest_cc_size/num_nodes*100:.2f}%)")
    print("-----------------------------------------")
    print(f"Average Degree       : {avg_degree:.2f}")
    print(f"Max Degree (Hub)     : {max_degree}")
    print("-----------------------------------------")
    print(f"Average Capacity     : {avg_cap:.2f}")
    print(f"Max Capacity         : {max_cap}")
    print("=========================================\n")

if __name__ == "__main__":
    analyze_graph()