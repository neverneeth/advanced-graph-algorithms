import urllib.request
import gzip
from pathlib import Path

# Paths
base = Path(__file__).resolve().parent.parent.parent
data_dir = base / "datasets" / "snap"
data_dir.mkdir(parents=True, exist_ok=True)

gz_file = data_dir / "web-Google.txt.gz"
output_file = data_dir / "google_web_graph.txt"
url = "https://snap.stanford.edu/data/web-Google.txt.gz"

def download_dataset():
    if not gz_file.exists():
        print("Downloading SNAP Google Web Graph (this may take a minute)...")
        urllib.request.urlretrieve(url, gz_file)
        print("Download complete.")
    else:
        print("Dataset already downloaded.")

def preprocess_graph():
    print("Parsing and mapping Node IDs to contiguous index space...")
    
    node_map = {}
    edges = []
    current_id = 0
    
    # Read the gzipped file directly
    with gzip.open(gz_file, 'rt') as f:
        for line in f:
            # Skip comments
            if line.startswith('#'):
                continue
                
            parts = line.strip().split()
            if len(parts) >= 2:
                u_raw, v_raw = int(parts[0]), int(parts[1])
                
                # Map to contiguous IDs
                if u_raw not in node_map:
                    node_map[u_raw] = current_id
                    current_id += 1
                if v_raw not in node_map:
                    node_map[v_raw] = current_id
                    current_id += 1
                    
                u = node_map[u_raw]
                v = node_map[v_raw]
                
                edges.append((u, v))
                
    num_nodes = current_id
    num_edges = len(edges)
    
    print(f"Graph mapped! Nodes: {num_nodes}, Edges: {num_edges}")
    print(f"Writing optimized graph to {output_file}...")
    
    with open(output_file, 'w') as f:
        # Header for C++ parsing: V E
        f.write(f"{num_nodes} {num_edges}\n")
        for u, v in edges:
            f.write(f"{u} {v}\n")
            
    print("Preprocessing complete!")

if __name__ == "__main__":
    download_dataset()
    preprocess_graph()