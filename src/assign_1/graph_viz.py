import networkx as nx
from pathlib import Path
from pyvis.network import Network
import matplotlib.pyplot as plt

base = Path(__file__).resolve().parent.parent.parent
data = base / "datasets" / "caida"
G = nx.Graph()
with open(data / "caida_bandwidth_graph.txt", "r") as f:
    count = 0
    for line in f:
        if count == 0:
            count = 1
            continue
        u, v, weight = map(int, line.strip().split())
        G.add_edge(u, v, weight=weight)
        count += 1
        if count % 1000 == 0:
            print(f"Processed {count} edges...")

degree_dict = dict(G.degree())
top_nodes = sorted(degree_dict, key=degree_dict.get, reverse=True)[:100]

top_subgraph = G.subgraph(top_nodes)

nx.draw(top_subgraph, with_labels=True, node_size=50, font_size=8, font_color="white", node_color="blue", edge_color="gray")
plt.savefig(data / "top_100_nodes_graph.png", dpi=300)
