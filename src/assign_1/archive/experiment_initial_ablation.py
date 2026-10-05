import csv
import random
import statistics
import subprocess
from collections import defaultdict
from pathlib import Path

from experiment_dose_response import load_graph, make_graph


base = Path(__file__).resolve().parent.parent.parent
src_dir = base / "src" / "maxflow"
results_dir = base / "results" / "logs"
raw_output = results_dir / "maxflow_initial_ablation_raw.csv"
summary_output = results_dir / "maxflow_initial_ablation_summary.csv"

QUANTILES = (None, 0.999)
NUM_PAIRS = 50
RUNS_PER_PAIR = 5
RANDOM_SEED = 20261005

ALGORITHMS = (
    ("Dinic", "dinic"),
    ("PushRelabelNaive", "pushrelabel"),
    ("PushRelabelInitial", "pushrelabel_initial"),
)


def compile_cpp():
    sources = {
        "dinic": "dinic.cpp",
        "pushrelabel": "pushrelabel.cpp",
        "pushrelabel_initial": "pushrelabel_initial.cpp",
    }
    for binary, source in sources.items():
        subprocess.run(
            ["g++", "-O3", "-std=c++17", src_dir / source, "-o", src_dir / binary],
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
        "Global_Relabels": "",
        "Gap_Triggers": "",
        "Stranded": "",
        "Returned_To_Source": "",
    }
    if algorithm == "PushRelabelInitial":
        row.update({
            "Global_Relabels": int(values[10]),
            "Gap_Triggers": int(values[11]),
            "Stranded": int(values[12]),
            "Returned_To_Source": int(values[13]),
        })
    return row


def add_metadata(row, metadata, label, pair_id, run_index):
    row.update({
        "Threshold_Label": label,
        "Degree_Threshold": metadata["threshold"],
        "Nodes": metadata["nodes"],
        "Edges": metadata["edges"],
        "Max_Degree": metadata["max_degree"],
        "Pair_ID": pair_id,
        "Run_Index": run_index,
    })
    return row


def summarize(rows):
    grouped = defaultdict(lambda: defaultdict(list))
    pair_times = defaultdict(lambda: defaultdict(list))
    for row in rows:
        grouped[row["Threshold_Label"]][row["Algorithm"]].append(row)
        pair_times[(row["Threshold_Label"], row["Source"], row["Sink"])][row["Algorithm"]].append(row["Time_us"])

    summaries = []
    for label in ("full", "q0.999"):
        result = {"Threshold_Label": label}
        for algorithm, _ in ALGORITHMS:
            times = [r["Time_us"] for r in grouped[label][algorithm]]
            quartiles = statistics.quantiles(times, n=4, method="inclusive")
            result[f"{algorithm}_Median_us"] = statistics.median(times)
            result[f"{algorithm}_IQR_us"] = quartiles[2] - quartiles[0]
            if algorithm != "Dinic":
                ratios = []
                for (key, source, sink), algorithms in pair_times.items():
                    if key == label:
                        ratios.append(statistics.mean(algorithms[algorithm]) / statistics.mean(algorithms["Dinic"]))
                result[f"{algorithm}_PR_Dinic_Ratio_Median"] = statistics.median(ratios)

        metadata = grouped[label]["Dinic"][0]
        initial = grouped[label]["PushRelabelInitial"]
        result.update({
            "Degree_Threshold": metadata["Degree_Threshold"],
            "Nodes": metadata["Nodes"],
            "Edges": metadata["Edges"],
            "Max_Degree": metadata["Max_Degree"],
            "Initial_Global_Relabels_Mean": statistics.mean(r["Global_Relabels"] for r in initial),
            "Initial_Gap_Triggers_Mean": statistics.mean(r["Gap_Triggers"] for r in initial),
            "Initial_Stranded_Mean": statistics.mean(r["Stranded"] for r in initial),
            "Initial_Returned_To_Source_Mean": statistics.mean(r["Returned_To_Source"] for r in initial),
        })
        summaries.append(result)
    return summaries


def run_experiment():
    results_dir.mkdir(parents=True, exist_ok=True)
    graph = load_graph()
    compile_cpp()
    rows = []

    for quantile in QUANTILES:
        metadata = make_graph(graph, quantile)
        label = metadata["label"]
        generator = random.Random(RANDOM_SEED)
        for pair_id in range(1, NUM_PAIRS + 1):
            source, sink = generator.sample(range(metadata["nodes"]), 2)
            flows = {}
            for run_index in range(1, RUNS_PER_PAIR + 1):
                for algorithm, binary_name in ALGORITHMS:
                    result = run_binary(src_dir / binary_name, metadata["path"], source, sink, algorithm)
                    rows.append(add_metadata(result, metadata, label, pair_id, run_index))
                    flows[algorithm] = result["maxflow"]
                if len(set(flows.values())) != 1:
                    raise RuntimeError(f"Flow mismatch at {label} pair {pair_id}")

    with raw_output.open("w", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=list(rows[0]))
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