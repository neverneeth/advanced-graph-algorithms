import gzip
import random
from collections import defaultdict
import os
from pathlib import Path

base = Path(__file__).resolve().parent.parent.parent
data = base / "datasets" / "caida"

def preprocess_caida_data(input_filepath, output_filepath):
    edges = set()
    degrees = defaultdict(int)
    
    print(f"Reading dataset from: {input_filepath}")
    
    open_func = gzip.open if input_filepath.name.endswith('.gz') else open
    mode = 'rt' if input_filepath.name.endswith('.gz') else 'r'
    
    with open_func(input_filepath, mode) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            if not line or line.startswith('#'):
                continue
                
            parts = line.split('\t')
            
            if parts[0] == 'D' and len(parts) >= 3:
                u_str = parts[1]
                v_str = parts[2]
                
                if '_' in u_str or ',' in u_str or '_' in v_str or ',' in v_str:
                    continue
                
                if u_str == "UNKNOWN" or v_str == "UNKNOWN":
                    continue
                    
                u = int(u_str)
                v = int(v_str)
                
                if u == v:
                    continue
                
                edge = (min(u, v), max(u, v))
                if edge not in edges:
                    edges.add(edge)
                    degrees[u] += 1
                    degrees[v] += 1
                    
            if line_num % 500000 == 0:
                print(f"Parsed {line_num} lines...")
    

    num_nodes = len(degrees)
    num_edges = len(edges)
    print(f"Topology built: {num_nodes} unique nodes, {num_edges} unique edges.")
    print("Assigning bandwidths with noise and writing to file...")
    node_to_dense = {
        node: dense_id
        for dense_id, node in enumerate(sorted(degrees))
    }

    with open(output_filepath, 'w') as f:
        f.write(f"{num_nodes} {num_edges}\n")
        
        for u, v in edges:
            deg_u = degrees[u]
            deg_v = degrees[v]
            
            base_capacity = (deg_u + deg_v) * 10
            
            noise_multiplier = random.uniform(0.80, 1.20)
            
            final_capacity = max(1, int(base_capacity * noise_multiplier))
            dense_u = node_to_dense[u]
            dense_v = node_to_dense[v]
            f.write(f"{dense_u} {dense_v} {final_capacity}\n")
            
    print(f"Success! Output saved to {output_filepath}")

if __name__ == "__main__":
    input_file = data / 'cycle-aslinks.l7.t1.c008040.20200101.txt'
    output_file = data / 'caida_bandwidth_graph.txt'
    
    if input_file.exists():
        preprocess_caida_data(input_file, output_file)
    else:
        print(f"Error: {input_file} not found in the directory.")
