import urllib.request
import gzip
import random
from pathlib import Path

# Paths
base = Path(__file__).resolve().parent.parent
data_dir = base / "datasets" / "snap"
data_dir.mkdir(parents=True, exist_ok=True)

gz_file = data_dir / "roadNet-PA.txt.gz"
base_graph_file = data_dir / "pa_base_graph.txt"
update_stream_file = data_dir / "pa_updates.txt"
url = "https://snap.stanford.edu/data/roadNet-PA.txt.gz"

def download_dataset():
    if not gz_file.exists():
        print("Downloading SNAP PA Road Network...")
        urllib.request.urlretrieve(url, gz_file)
        print("Download complete.")

def generate_dynamic_environment():
    print("Parsing network and generating dynamic updates...")
    
    edges = set()
    max_node = 0
    
    with gzip.open(gz_file, 'rt') as f:
        for line in f:
            if line.startswith('#'): continue
            parts = line.strip().split()
            if len(parts) >= 2:
                u, v = int(parts[0]), int(parts[1])
                # Ensure undirected representation (u < v)
                if u > v: u, v = v, u
                edges.add((u, v))
                max_node = max(max_node, u, v)

    edges = list(edges)
    total_edges = len(edges)
    
    # We will treat 90% of the edges as the "Base Graph"
    # and use the remaining 10% to simulate dynamic insertions/deletions
    random.shuffle(edges)
    split_idx = int(total_edges * 0.90)
    
    base_edges = edges[:split_idx]
    dynamic_pool = edges[split_idx:]
    
    # Write Base Graph
    print(f"Writing Base Graph: {max_node + 1} nodes, {len(base_edges)} edges...")
    with open(base_graph_file, 'w') as f:
        f.write(f"{max_node + 1} {len(base_edges)}\n")
        for u, v in base_edges:
            f.write(f"{u} {v}\n")
            
    # Generate Update Stream (Simulating time)
    # Format: [TYPE] [U] [V] 
    # TYPE: 1 = Add Edge, 0 = Delete Edge
    print(f"Generating Update Stream with 50,000 events...")
    
    with open(update_stream_file, 'w') as f:
        f.write("50000\n") # Number of update queries
        
        active_dynamic_edges = set()
        
        for _ in range(50000):
            if not active_dynamic_edges or random.random() > 0.3:
                # 70% chance to construct a "new" road from the pool
                if dynamic_pool:
                    e = dynamic_pool.pop()
                    active_dynamic_edges.add(e)
                    f.write(f"1 {e[0]} {e[1]}\n")
            else:
                # 30% chance a road is closed (deleted)
                e = random.choice(list(active_dynamic_edges))
                active_dynamic_edges.remove(e)
                f.write(f"0 {e[0]} {e[1]}\n")

    print("Dynamic environment ready!")

if __name__ == "__main__":
    download_dataset()
    generate_dynamic_environment()