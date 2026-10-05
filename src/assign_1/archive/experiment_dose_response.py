import csv
import math
import random
import statistics
import subprocess
from collections import defaultdict
from pathlib import Path

import networkx as nx


base = Path(__file__).resolve().parent.parent.parent
data_dir = base / "datasets" / "caida"
src_dir = base / "src" / "maxflow"
results_dir = base / "results" / "logs"
source_graph = data_dir / "caida_bandwidth_graph.txt"
raw_output = results_dir / "maxflow_dose_response_raw.csv"
summary_output = results_dir / "maxflow_dose_response_summary.csv"

QUANTILES = (None, 0.999, 0.99, 0.95)
NUM_PAIRS = 50
RUNS_PER_PAIR = 5
RANDOM_SEED = 20261005


def load_graph():
    graph = nx.Graph()
    with source_graph.open() as infile:
        next(infile)
        for line in infile:
            u, v, capacity = map(int, line.split())
            graph.add_edge(u, v, capacity=capacity)
    return graph


def make_graph(graph, quantile):
    if quantile is None:
        label = "full"
        threshold = max(dict(graph.degree()).values())
        filtered = graph
    else:
        degrees = sorted(dict(graph.degree()).values())
        threshold = degrees[math.ceil(quantile * (len(degrees) - 1))]
        label = f"q{quantile:g}"
        retained = [node for node, degree in graph.degree() if degree <= threshold]
        filtered = graph.subgraph(retained)

    component = max(nx.connected_components(filtered), key=len)
    component_graph = filtered.subgraph(component).copy()
    relabeled = nx.convert_node_labels_to_integers(component_graph, ordering="sorted")
    graph_path = data_dir / f"caida_dose_{label}.txt"
    with graph_path.open("w") as outfile:
        outfile.write(f"{relabeled.number_of_nodes()} {relabeled.number_of_edges()}\n")
        for u, v, data in relabeled.edges(data=True):
            outfile.write(f"{u} {v} {data['capacity']}\n")

    return {
        "label": label,
        "quantile": "full" if quantile is None else quantile,
        "threshold": threshold,
        "nodes": relabeled.number_of_nodes(),
        "edges": relabeled.number_of_edges(),
        "max_degree": max(dict(relabeled.degree()).values()),
        "path": graph_path,
    }


def compile_cpp():
    for algorithm in ("dinic", "pushrelabel"):
        subprocess.run(
            ["g++", "-O3", "-std=c++17", src_dir / f"{algorithm}.cpp", "-o", src_dir / algorithm],
            check=True,
        )


def run_binary(binary, graph_path, source, sink, algorithm):
    result = subprocess.run(
        [str(binary), str(graph_path), str(source), str(sink)],
        capture_output=True,
        text=True,
        check=True,
    )
    values = result.stdout.strip().split(",")
    row = {
        "Algorithm": algorithm,
        "Source": source,
        "Sink": sink,
        "maxflow": int(values[2]),
        "Primary_Ops": int(values[3]),
        "Secondary_Ops": int(values[4]),
        "Time_us": int(values[5]),
        "BFS_Phases": int(values[6]) if algorithm == "Dinic" else "",
        "Total_Pushes": "",
        "Saturating_Pushes": "",
        "Nonsaturating_Pushes": "",
        "Relabel_Edge_Scans": "",
        "High_Degree_Relabel_Scans": "",
        "Global_Relabels": "",
        "Gap_Triggers": "",
        "Excess_Returned_To_Source": "",
    }
    if algorithm == "PushRelabel":
        row.update({
            "Total_Pushes": int(values[6]),
            "Saturating_Pushes": int(values[7]),
            "Nonsaturating_Pushes": int(values[8]),
            "Relabel_Edge_Scans": int(values[9]),
            "High_Degree_Relabel_Scans": int(values[10]),
            "Global_Relabels": int(values[11]),
            "Gap_Triggers": int(values[12]),
            "Excess_Returned_To_Source": int(values[13]),
        })
    return row


def summarize(rows):
    grouped = defaultdict(lambda: defaultdict(list))
    pair_times = defaultdict(lambda: defaultdict(list))
    for row in rows:
        key = row["Threshold_Label"]
        algorithm = row["Algorithm"]
        grouped[key][algorithm].append(row)
        pair_times[(key, row["Source"], row["Sink"])][algorithm].append(row["Time_us"])

    summary = []
    for label in [f"full", "q0.999", "q0.99", "q0.95"]:
        dinic_times = [r["Time_us"] for r in grouped[label]["Dinic"]]
        push_times = [r["Time_us"] for r in grouped[label]["PushRelabel"]]
        dinic_q = statistics.quantiles(dinic_times, n=4, method="inclusive")
        push_q = statistics.quantiles(push_times, n=4, method="inclusive")
        ratios = []
        for (key, source, sink), algorithms in pair_times.items():
            if key == label:
                ratios.append(statistics.mean(algorithms["PushRelabel"]) / statistics.mean(algorithms["Dinic"]))

        dinic = grouped[label]["Dinic"]
        push = grouped[label]["PushRelabel"]
        metadata = dinic[0]
        summary.append({
            "Threshold_Label": label,
            "Degree_Threshold": metadata["Degree_Threshold"],
            "Nodes": metadata["Nodes"],
            "Edges": metadata["Edges"],
            "Max_Degree": metadata["Max_Degree"],
            "Dinic_Median_us": statistics.median(dinic_times),
            "Dinic_IQR_us": dinic_q[2] - dinic_q[0],
            "PushRelabel_Median_us": statistics.median(push_times),
            "PushRelabel_IQR_us": push_q[2] - push_q[0],
            "Paired_PR_Dinic_Ratio_Median": statistics.median(ratios),
            "Dinic_BFS_Phases_Mean": statistics.mean(r["BFS_Phases"] for r in dinic),
            "Push_Total_Pushes_Mean": statistics.mean(r["Total_Pushes"] for r in push),
            "Push_Saturating_Pushes_Mean": statistics.mean(r["Saturating_Pushes"] for r in push),
            "Push_Nonsaturating_Pushes_Mean": statistics.mean(r["Nonsaturating_Pushes"] for r in push),
            "Push_Relabels_Mean": statistics.mean(r["Secondary_Ops"] for r in push),
            "Push_Relabel_Scans_Mean": statistics.mean(r["Relabel_Edge_Scans"] for r in push),
            "Push_High_Degree_Relabel_Scans_Mean": statistics.mean(r["High_Degree_Relabel_Scans"] for r in push),
            "Push_Global_Relabels_Mean": statistics.mean(r["Global_Relabels"] for r in push),
            "Push_Gap_Triggers_Mean": statistics.mean(r["Gap_Triggers"] for r in push),
            "Push_Excess_Returned_Mean": statistics.mean(r["Excess_Returned_To_Source"] for r in push),
        })
    return summary


def run_experiment():
    results_dir.mkdir(parents=True, exist_ok=True)
    graph = load_graph()
    compile_cpp()
    rows = []
    for quantile in QUANTILES:
        metadata = make_graph(graph, quantile)
        generator = random.Random(RANDOM_SEED)
        for pair_id in range(1, NUM_PAIRS + 1):
            source, sink = generator.sample(range(metadata["nodes"]), 2)
            for run_index in range(1, RUNS_PER_PAIR + 1):
                results = {}
                for algorithm, binary_name in (("Dinic", "dinic"), ("PushRelabel", "pushrelabel")):
                    result = run_binary(src_dir / binary_name, metadata["path"], source, sink, algorithm)
                    result.update({
                        "Threshold_Label": metadata["label"],
                        "Degree_Threshold": metadata["threshold"],
                        "Nodes": metadata["nodes"],
                        "Edges": metadata["edges"],
                        "Max_Degree": metadata["max_degree"],
                        "Pair_ID": pair_id,
                        "Run_Index": run_index,
                    })
                    rows.append(result)
                    results[algorithm] = result
                if results["Dinic"]["maxflow"] != results["PushRelabel"]["maxflow"]:
                    raise RuntimeError(f"Flow mismatch at {metadata['label']} pair {pair_id}")

    fieldnames = list(rows[0])
    with raw_output.open("w", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summaries = summarize(rows)
    with summary_output.open("w", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    for summary in summaries:
        print(summary)
    print(f"Raw results saved to {raw_output}")
    print(f"Summary saved to {summary_output}")


if __name__ == "__main__":
    run_experiment()