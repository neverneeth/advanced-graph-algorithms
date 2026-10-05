import networkx as nx
from pathlib import Path

# Setup paths
base = Path(__file__).resolve().parent.parent.parent
data = base / "datasets" / "tntp"
input_file = data / "goldcoast_network.txt"

# Road networks are directed (one-way streets, asymmetric flow)
G = nx.DiGraph()

print(f"Reading {input_file}...")
with open(input_file, "r") as f:
    count = 0
    for line in f:
        # Skip the first line which contains "num_nodes num_edges"
        if count == 0:
            count = 1
            continue
            
        parts = line.strip().split()
        if len(parts) == 4:
            u = int(parts[0])
            v = int(parts[1])
            cap = int(parts[2])
            cost = int(parts[3])
            
            # Add edge with both capacity and cost attributes for Gephi
            G.add_edge(u, v, capacity=cap, cost=cost)
            
        count += 1
        if count % 2000 == 0:
            print(f"Processed {count} edges...")

print(f"Graph built with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")

# Option 1: Export the FULL graph (Recommended for Gold Coast)
# 4,800 nodes is very small for Gephi, and filtering a road network 
# by degree will severely fragment the map visualization.
full_output_file = data / "goldcoast_full_network.graphml"
print(f"Exporting full graph to {full_output_file}...")
nx.write_graphml(G, full_output_file)

# Option 2: Export the Top 500 nodes (To match your CAIDA script)
degree_dict = dict(G.degree()) # In a DiGraph, this is in_degree + out_degree
top_nodes = sorted(degree_dict, key=degree_dict.get, reverse=True)[:500]
top_subgraph = G.subgraph(top_nodes)

top_output_file = data / "goldcoast_top_500_nodes_subgraph.graphml"
print(f"Exporting top 500 nodes subgraph to {top_output_file}...")
nx.write_graphml(top_subgraph, top_output_file)

print("Done!")