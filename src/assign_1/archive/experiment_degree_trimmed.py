import csv
import math
import random
import subprocess
from pathlib import Path

import networkx as nx


base = Path(__file__).resolve().parent.parent.parent
data_dir = base / "datasets" / "caida"
src_dir = base / "src" / "maxflow"
results_dir = base / "results" / "logs"

source_graph = data_dir / "caida_bandwidth_graph.txt"
trimmed_graph = data_dir / "caida_degree_trimmed_99_graph.txt"
csv_output = results_dir / "maxflow_benchmark_degree_trimmed_99.csv"

NUM_PAIRS = 50
RUNS_PER_PAIR = 5
RANDOM_SEED = 20261005


def build_trimmed_graph():
    graph = nx.Graph()
    with source_graph.open() as infile:
        next(infile)
        for line in infile:
            u, v, capacity = map(int, line.split())
            graph.add_edge(u, v, capacity=capacity)

    degrees = sorted(dict(graph.degree()).values())
    threshold = degrees[math.ceil(0.99 * (len(degrees) - 1))]
    retained = [node for node, degree in graph.degree() if degree <= threshold]
    trimmed = graph.subgraph(retained).copy()
    component = max(nx.connected_components(trimmed), key=len)
    trimmed = trimmed.subgraph(component).copy()
    trimmed = nx.convert_node_labels_to_integers(trimmed, ordering="sorted")

    with trimmed_graph.open("w") as outfile:
        outfile.write(f"{trimmed.number_of_nodes()} {trimmed.number_of_edges()}\n")
        for u, v, data in trimmed.edges(data=True):
            outfile.write(f"{u} {v} {data['capacity']}\n")

    print(
        f"Trimmed graph: {trimmed.number_of_nodes()} nodes, "
        f"{trimmed.number_of_edges()} edges, "
        f"max degree {max(dict(trimmed.degree()).values())}, "
        f"threshold {threshold}"
    )
    return trimmed.number_of_nodes()


def compile_cpp():
    for algorithm in ("dinic", "pushrelabel"):
        subprocess.run(
            ["g++", "-O3", "-std=c++17", src_dir / f"{algorithm}.cpp", "-o", src_dir / algorithm],
            check=True,
        )


def run_binary(binary_path, source, sink):
    result = subprocess.run(
        [str(binary_path), str(trimmed_graph), str(source), str(sink)],
        capture_output=True,
        text=True,
        check=True,
    )
    parts = result.stdout.strip().split(",")
    return {
        "maxflow": int(parts[2]),
        "ops_1": int(parts[3]),
        "ops_2": int(parts[4]),
        "time_us": int(parts[5]),
    }


def run_experiment():
    results_dir.mkdir(parents=True, exist_ok=True)
    node_count = build_trimmed_graph()
    compile_cpp()
    random_generator = random.Random(RANDOM_SEED)

    with csv_output.open("w", newline="") as csvfile:
        fieldnames = [
            "Algorithm", "Source", "Sink", "Run_Index", "maxflow",
            "Primary_Ops", "Secondary_Ops", "Time_us",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for pair_index in range(1, NUM_PAIRS + 1):
            source, sink = random_generator.sample(range(node_count), 2)
            print(f"Testing pair {pair_index}/{NUM_PAIRS}: {source} -> {sink}")

            for run_index in range(1, RUNS_PER_PAIR + 1):
                results = {}
                for algorithm in ("Dinic", "PushRelabel"):
                    binary = src_dir / ("dinic" if algorithm == "Dinic" else "pushrelabel")
                    result = run_binary(binary, source, sink)
                    results[algorithm] = result
                    writer.writerow({
                        "Algorithm": algorithm,
                        "Source": source,
                        "Sink": sink,
                        "Run_Index": run_index,
                        "maxflow": result["maxflow"],
                        "Primary_Ops": result["ops_1"],
                        "Secondary_Ops": result["ops_2"],
                        "Time_us": result["time_us"],
                    })

                if results["Dinic"]["maxflow"] != results["PushRelabel"]["maxflow"]:
                    print(f"WARNING: max-flow mismatch for {source} -> {sink}")

    print(f"Results saved to {csv_output}")


if __name__ == "__main__":
    run_experiment()