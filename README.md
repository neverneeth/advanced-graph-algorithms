# advanced-graph-algorithms
Coding assignments and experiments performed as part of elective course PECST595 ADVANCED GRAPH ALGORITHMS 

# Max Flow

[Original Data](https://publicdata.caida.org/datasets/topology/ark/ipv4/as-links/team-1/2020/cycle-aslinks.l7.t1.c008040.20200101.txt.gz) - Taken from the CAIDA AS Links dataset. The original dataset contains AS links in the form of pairs of AS numbers.

IPv4 Routed /24 Autonomous System (AS) Links Dataset
https://www.caida.org/catalog/datasets/ipv4_routed_topology_aslinks_dataset/

Converted to a Network Flow graph with bandwidths assigned to each edge. Download the dataset from the above link and unzip into the `datasets/caida/` directory. Use the `/srs/preprocess/caida_2_flow.py` script to convert the dataset. The bandwidths are generated based on the degree of the nodes, with some random noise added to simulate real-world variability.

Final Data can be found in the `datasets/caida/caida_bandwidth_graph.txt` file. Each line in this file represents an edge in the graph, formatted as: `source_node target_node bandwidth`. The first line `number_of_nodes number_of_edges` represents the total number of nodes and edges in the graph.

