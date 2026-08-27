import urllib.request
import os
from pathlib import Path

base = Path(__file__).resolve().parent.parent.parent
data_dir = base / "datasets" / "tntp"
data_dir.mkdir(parents=True, exist_ok=True)
output_file = data_dir / "goldcoast_network.txt"

url = "https://raw.githubusercontent.com/bstabler/TransportationNetworks/refs/heads/master/GoldCoast/Goldcoast_network_2016_01.tntp"
raw_file = data_dir / "Goldcoast_network_2016_01.tntp"

def download_dataset():
    if not raw_file.exists():
        print(f"Downloading Gold Coast network from TNTP...")
        urllib.request.urlretrieve(url, raw_file)
        print("Download complete.")

def preprocess_tntp():
    print(f"Parsing {raw_file}...")
    
    edges = []
    max_node = 0
    
    with open(raw_file, 'r') as f:
        in_data_section = False
        for line in f:
            line = line.strip()
            
            if line.startswith("~"):
                in_data_section = True
                continue
            
            if not in_data_section or not line or line.startswith("<"):
                continue
                
            clean_line = line.replace(';', '').strip()
            parts = clean_line.split()
            
            if len(parts) >= 5:
                u = int(parts[0])
                v = int(parts[1])
                cap = float(parts[2])
                cost = float(parts[4]) 
                cap_int = max(1, int(cap))
                cost_int = max(1, int(cost * 100)) 
                
                edges.append((u, v, cap_int, cost_int))
                max_node = max(max_node, u, v)

    num_nodes = max_node
    num_edges = len(edges)
    
    print(f"Writing parsed network: {num_nodes} nodes, {num_edges} edges...")
    with open(output_file, 'w') as f:
        f.write(f"{num_nodes} {num_edges}\n")
        for u, v, cap, cost in edges:
            f.write(f"{u-1} {v-1} {cap} {cost}\n")
            
    print(f"Preprocessing complete. Saved to {output_file}")

if __name__ == "__main__":
    if not output_file.exists():
        download_dataset()
    preprocess_tntp()