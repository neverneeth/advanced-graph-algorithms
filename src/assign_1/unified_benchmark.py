import csv
import math
import os
import platform
import random
import statistics
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import networkx as nx


BASE = Path(__file__).resolve().parent.parent.parent
CAIDA = BASE / "datasets" / "caida"
DERIVED = CAIDA / "derived"
TNTP = BASE / "datasets" / "tntp"
BIN = BASE / "src"
RESULTS = BASE / "results" / "logs"
CAIDA_GRAPH = CAIDA / "caida_bandwidth_graph.txt"
GOLDCOAST_GRAPH = TNTP / "goldcoast_network.txt"
RAW_OUTPUT = RESULTS / "unified_benchmark_raw.csv"
SUMMARY_OUTPUT = RESULTS / "unified_benchmark_summary.csv"
COUNTERS_OUTPUT = RESULTS / "unified_benchmark_counters.csv"
METADATA_OUTPUT = RESULTS / "unified_benchmark_metadata.txt"

PAIRS = int(os.environ.get("BENCH_PAIRS", 50))
RUNS = int(os.environ.get("BENCH_RUNS", 5))
TIMEOUT_SECONDS = 60
SEED = 20261005
BOOTSTRAP_SAMPLES = 10000
# None is the full largest component; the others drop nodes above that degree quantile.
DEGREE_QUANTILES = (None, 0.999, 0.99, 0.95)

MAXFLOW_ALGORITHMS = (
    ("Dinic", BIN / "maxflow/dinic"),
    ("DinicOptimized", BIN / "maxflow/dinic_optimized"),
    ("PushRelabelNaive", BIN / "maxflow/pushrelabel"),
    ("PushRelabelInitial", BIN / "maxflow/pushrelabel_initial"),
    ("PushRelabelTuned", BIN / "maxflow/pushrelabel_heuristic"),
)
MCF_ALGORITHMS = (
    ("CycleCanceling", BIN / "mincostflow/cyclecancel"),
    ("CycleCancelingEarlyDetect", BIN / "mincostflow/cyclecancel_optimized"),
    ("SSP", BIN / "mincostflow/ssp"),
    ("CapacityScaling", BIN / "mincostflow/capacity_scaling"),
)
BASELINES = {"MaxFlow": "DinicOptimized", "MCF": "SSP"}

# Max-flow binaries print source,sink,flow,<op_a>,<op_b>,time_us[,extra...];
# MCF binaries print source,sink,target,cost,<ops>,time_us[,extra...].
# Each tuple names fields 3, 4 and the extras; None skips a field (the MCF cost).
COUNTER_NAMES = {
    "Dinic": ("BFS_Ops", "DFS_Ops", "BFS_Phases"),
    "DinicOptimized": ("BFS_Ops", "DFS_Ops", "BFS_Phases"),
    "PushRelabelNaive": (
        "Edge_Scans", "Relabels", "Pushes", "Saturating_Pushes", "Nonsaturating_Pushes",
        "Relabel_Scans", "High_Degree_Relabel_Scans", "Global_Relabels", "Gap_Triggers",
        "Returned_To_Source",
    ),
    "PushRelabelInitial": (
        "Edge_Scans", "Relabels", "Pushes", "Saturating_Pushes", "Nonsaturating_Pushes",
        "Relabel_Scans", "Global_Relabels", "Gap_Triggers", "Stranded", "Returned_To_Source",
    ),
    "PushRelabelTuned": (
        "Edge_Scans", "Relabels", "Pushes", "Saturating_Pushes", "Nonsaturating_Pushes",
        "Relabel_Scans", "High_Degree_Relabel_Scans", "Global_Relabels", "Gap_Triggers",
        "Stranded",
    ),
    "CycleCanceling": (None, "Cycles_Canceled", "Searches", "Relaxation_Checks", "BF_Passes"),
    "CycleCancelingEarlyDetect": (None, "Cycles_Canceled", "Searches", "Relaxation_Checks", "BF_Passes"),
    "SSP": (None, "Augmentations", "Searches", "Relaxation_Checks"),
    "CapacityScaling": (
        None, "Augmentations", "Searches", "Relaxation_Checks", "Scaling_Phases", "Saturated_Arcs",
    ),
}


def pin_process():
    # Core 0 usually services most interrupts, so prefer the highest allowed core.
    allowed = sorted(os.sched_getaffinity(0))
    if not allowed:
        return "unavailable"
    core = allowed[-1]
    os.sched_setaffinity(0, {core})
    return core


def write_metadata(core):
    def command_output(command):
        try:
            return subprocess.run(command, capture_output=True, text=True, check=False).stdout.strip()
        except OSError:
            return "unavailable"

    cpu = "unknown"
    try:
        with open("/proc/cpuinfo") as infile:
            for line in infile:
                if line.startswith("model name"):
                    cpu = line.split(":", 1)[1].strip()
                    break
    except OSError:
        pass

    lines = [
        f"timestamp: {datetime.now().isoformat(timespec='seconds')}",
        f"cpu: {cpu}",
        f"logical_cpus: {os.cpu_count()}",
        f"pinned_core: {core}",
        f"platform: {platform.platform()}",
        f"python: {sys.version.split()[0]}",
        f"compiler: {command_output(['g++', '--version']).splitlines()[0]}",
        "compile_flags: -O3 -std=c++17",
        f"seed: {SEED}",
        f"pairs: {PAIRS}",
        f"runs_per_pair: {RUNS}",
        f"timeout_s: {TIMEOUT_SECONDS}",
        f"bootstrap_samples: {BOOTSTRAP_SAMPLES}",
    ]
    METADATA_OUTPUT.write_text("\n".join(lines) + "\n")


def compile_binaries():
    for _, binary in (*MAXFLOW_ALGORITHMS, *MCF_ALGORITHMS):
        subprocess.run(
            ["g++", "-O3", "-std=c++17", binary.with_suffix(".cpp"), "-o", binary],
            check=True,
        )


def load_caida():
    graph = nx.Graph()
    with CAIDA_GRAPH.open() as infile:
        next(infile)
        for line in infile:
            u, v, capacity = map(int, line.split())
            graph.add_edge(u, v, capacity=capacity)
    return graph


def make_caida_graph(graph, quantile):
    if quantile is None:
        label = "full"
        threshold = max(dict(graph.degree()).values())
        filtered = graph
    else:
        degrees = sorted(dict(graph.degree()).values())
        threshold = degrees[math.ceil(quantile * (len(degrees) - 1))]
        label = f"q{quantile:g}"
        filtered = graph.subgraph([node for node, degree in graph.degree() if degree <= threshold])

    component = max(nx.connected_components(filtered), key=len)
    relabeled = nx.convert_node_labels_to_integers(filtered.subgraph(component).copy(), ordering="sorted")
    DERIVED.mkdir(parents=True, exist_ok=True)
    path = DERIVED / f"caida_{label}.txt"
    with path.open("w") as outfile:
        outfile.write(f"{relabeled.number_of_nodes()} {relabeled.number_of_edges()}\n")
        for u, v, data in relabeled.edges(data=True):
            outfile.write(f"{u} {v} {data['capacity']}\n")

    return {
        "Graph": f"CAIDA_{label}",
        "Degree_Threshold": threshold,
        "Nodes": relabeled.number_of_nodes(),
        "Edges": relabeled.number_of_edges(),
        "Max_Degree": max(dict(relabeled.degree()).values()),
        "path": path,
    }


def run_binary(binary, args, algorithm):
    row = {"Algorithm": algorithm}
    try:
        result = subprocess.run(
            [str(binary), *map(str, args)],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        row["Status"] = "timeout"
        return row
    if result.returncode != 0 or not result.stdout.strip():
        row["Status"] = "failure"
        row["Stderr"] = result.stderr.strip()[:200]
        return row

    values = [int(value) for value in result.stdout.strip().split(",")]
    names = COUNTER_NAMES[algorithm]
    if len(values) != len(names) + 4:
        raise RuntimeError(f"{algorithm} printed {len(values)} fields, expected {len(names) + 4}")
    is_mcf = algorithm in dict(MCF_ALGORITHMS)
    row["Result"] = values[3] if is_mcf else values[2]
    row["Time_us"] = values[5]
    counters = list(zip(names[:2], values[3:5])) + list(zip(names[2:], values[6:]))
    row.update({name: value for name, value in counters if name})
    # MCF binaries print cost -1 when the target flow exceeds the s-t max flow.
    row["Status"] = "infeasible" if is_mcf and row["Result"] == -1 else "ok"
    return row


def run_part(part, graph_meta, pairs, algorithms, order_rng, rows):
    for pair_id, (source, sink, *target) in enumerate(pairs, 1):
        args = (graph_meta["path"], source, sink, *target)
        for run in range(1, RUNS + 1):
            order = list(algorithms)
            order_rng.shuffle(order)
            results = {}
            for position, (algorithm, binary) in enumerate(order, 1):
                result = run_binary(binary, args, algorithm)
                result.update({
                    "Part": part,
                    "Graph": graph_meta["Graph"],
                    "Pair_ID": pair_id,
                    "Run": run,
                    "Order_Position": position,
                    "Source": source,
                    "Sink": sink,
                    "Target_Flow": target[0] if target else "",
                })
                rows.append(result)
                results[algorithm] = result

            completed = {a: r for a, r in results.items() if r["Status"] in ("ok", "infeasible")}
            answers = {a: r["Result"] for a, r in completed.items()}
            if len(set(answers.values())) > 1:
                raise RuntimeError(f"{part} result mismatch on {graph_meta['Graph']} pair {pair_id}: {answers}")
        print(f"  {graph_meta['Graph']} pair {pair_id}/{len(pairs)} done", flush=True)


def bootstrap_median_interval(values, seed):
    generator = random.Random(seed)
    medians = sorted(
        statistics.median(generator.choices(values, k=len(values))) for _ in range(BOOTSTRAP_SAMPLES)
    )
    low = medians[int(0.025 * BOOTSTRAP_SAMPLES)]
    high = medians[int(0.975 * BOOTSTRAP_SAMPLES) - 1]
    return statistics.median(values), low, high


def summarize(rows, graph_info):
    summaries = []
    counter_rows = []
    groups = defaultdict(list)
    for row in rows:
        groups[(row["Part"], row["Graph"])].append(row)

    for (part, graph_name), part_rows in groups.items():
        algorithms = [name for name, _ in (MAXFLOW_ALGORITHMS if part == "MaxFlow" else MCF_ALGORITHMS)]
        baseline = BASELINES[part]
        statuses = defaultdict(lambda: defaultdict(set))
        times = defaultdict(lambda: defaultdict(list))
        for row in part_rows:
            statuses[row["Pair_ID"]][row["Algorithm"]].add(row["Status"])
            if row["Status"] == "ok":
                times[row["Pair_ID"]][row["Algorithm"]].append(row["Time_us"])

        # A pair enters the paired comparison only if every algorithm solved it
        # in every run; infeasible and timed-out pairs are counted, not timed.
        all_pairs = sorted(statuses)
        infeasible_pairs = [p for p in all_pairs if any("infeasible" in s for s in statuses[p].values())]
        valid_pairs = [
            p for p in all_pairs
            if all(statuses[p][a] == {"ok"} and len(times[p][a]) == RUNS for a in algorithms)
        ]

        for algorithm in algorithms:
            algorithm_rows = [row for row in part_rows if row["Algorithm"] == algorithm]
            pair_medians = {p: statistics.median(times[p][algorithm]) for p in valid_pairs}
            if algorithm == baseline:
                ratios = [1.0] * len(valid_pairs)
            else:
                ratios = [
                    pair_medians[p] / max(statistics.median(times[p][baseline]), 1)
                    for p in valid_pairs
                ]
            if ratios:
                median_ratio, ci_low, ci_high = bootstrap_median_interval(ratios, SEED + len(summaries))
            else:
                median_ratio = ci_low = ci_high = ""
            summaries.append({
                "Part": part,
                "Graph": graph_name,
                **graph_info.get(graph_name, {}),
                "Algorithm": algorithm,
                "Baseline": baseline,
                "Pairs_Total": len(all_pairs),
                "Pairs_Infeasible": len(infeasible_pairs),
                "Pairs_Compared": len(valid_pairs),
                "Timeouts": sum(row["Status"] == "timeout" for row in algorithm_rows),
                "Failures": sum(row["Status"] == "failure" for row in algorithm_rows),
                "Median_Time_us": statistics.median(pair_medians.values()) if pair_medians else "",
                "Median_Ratio_To_Baseline": median_ratio,
                "Bootstrap_95_Low": ci_low,
                "Bootstrap_95_High": ci_high,
            })

            ok_rows = [
                row for row in algorithm_rows
                if row["Status"] == "ok" and row["Pair_ID"] in set(valid_pairs)
            ]
            for name in COUNTER_NAMES[algorithm]:
                if not name:
                    continue
                values = [row[name] for row in ok_rows]
                if values:
                    counter_rows.append({
                        "Part": part, "Graph": graph_name, "Algorithm": algorithm, "Counter": name,
                        "Median": statistics.median(values), "Mean": statistics.mean(values),
                        "Min": min(values), "Max": max(values),
                    })
            if algorithm.startswith("CycleCanceling") and ok_rows:
                per_search = [row["BF_Passes"] / max(row["Searches"], 1) for row in ok_rows]
                counter_rows.append({
                    "Part": part, "Graph": graph_name, "Algorithm": algorithm, "Counter": "Passes_Per_Search",
                    "Median": statistics.median(per_search), "Mean": statistics.mean(per_search),
                    "Min": min(per_search), "Max": max(per_search),
                })
    return summaries, counter_rows


def write_csv(path, rows):
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    core = pin_process()
    write_metadata(core)
    compile_binaries()
    order_rng = random.Random(SEED + 1)
    rows = []
    graph_info = {}

    caida = load_caida()
    for quantile in DEGREE_QUANTILES:
        meta = make_caida_graph(caida, quantile)
        graph_info[meta["Graph"]] = {k: v for k, v in meta.items() if k not in ("Graph", "path")}
        print(f"MaxFlow on {meta['Graph']}: {meta['Nodes']} nodes, {meta['Edges']} edges", flush=True)
        generator = random.Random(SEED)
        pairs = [tuple(generator.sample(range(meta["Nodes"]), 2)) for _ in range(PAIRS)]
        run_part("MaxFlow", meta, pairs, MAXFLOW_ALGORITHMS, order_rng, rows)

    road = nx.Graph()
    with GOLDCOAST_GRAPH.open() as infile:
        nodes, edges = map(int, next(infile).split())
        for line in infile:
            parts = line.split()
            if len(parts) >= 4:
                road.add_edge(int(parts[0]), int(parts[1]))
    goldcoast = {"Graph": "GoldCoast", "path": GOLDCOAST_GRAPH}
    graph_info["GoldCoast"] = {"Nodes": nodes, "Edges": edges}
    valid_nodes = sorted(max(nx.connected_components(road), key=len))
    generator = random.Random(SEED)
    pairs = [(*generator.sample(valid_nodes, 2), generator.randint(100, 1000)) for _ in range(PAIRS)]
    print("MCF on GoldCoast", flush=True)
    run_part("MCF", goldcoast, pairs, MCF_ALGORITHMS, order_rng, rows)

    write_csv(RAW_OUTPUT, rows)
    summaries, counter_rows = summarize(rows, graph_info)
    write_csv(SUMMARY_OUTPUT, summaries)
    write_csv(COUNTERS_OUTPUT, counter_rows)

    print(f"Pinned core: {core}")
    for path in (RAW_OUTPUT, SUMMARY_OUTPUT, COUNTERS_OUTPUT, METADATA_OUTPUT):
        print(f"Wrote {path}")
    for summary in summaries:
        print(
            f"{summary['Part']:7} {summary['Graph']:13} {summary['Algorithm']:26} "
            f"pairs={summary['Pairs_Compared']}/{summary['Pairs_Total']} "
            f"infeasible={summary['Pairs_Infeasible']} "
            f"median={summary['Median_Time_us']}us ratio={summary['Median_Ratio_To_Baseline']} "
            f"[{summary['Bootstrap_95_Low']}, {summary['Bootstrap_95_High']}]"
        )


if __name__ == "__main__":
    main()
