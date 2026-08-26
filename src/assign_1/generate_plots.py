import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from pathlib import Path

# --- Configuration & Paths ---
base = Path(__file__).resolve().parent.parent.parent
results_dir = base / "results" / "logs"
figures_dir = base / "results" / "figures"
figures_dir.mkdir(parents=True, exist_ok=True)

csv_file = results_dir / "maxflow_benchmark_results.csv"

# --- IEEE Plot Styling ---
plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 12,
    'axes.labelsize': 14,
    'axes.titlesize': 14,
    'legend.fontsize': 12,
    'xtick.labelsize': 11,
    'ytick.labelsize': 11,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight'
})

def calculate_confidence_interval(data, confidence=0.95):
    n = len(data)
    m = np.mean(data)
    std_err = stats.sem(data)
    h = std_err * stats.t.ppf((1 + confidence) / 2., n - 1)
    return m, m - h, m + h

def analyze_and_plot():
    print(f"Loading data from {csv_file}...")
    df = pd.read_csv(csv_file)

    # Convert microseconds to milliseconds for easier reading
    df['Time_ms'] = df['Time_us'] / 1000.0

    # 1. Statistical Summary Table (Aggregating the multiple runs)
    print("\n--- Statistical Summary ---")
    summary = df.groupby('Algorithm').agg(
        Mean_Time_ms=('Time_ms', 'mean'),
        Std_Dev_ms=('Time_ms', 'std'),
        Mean_Primary_Ops=('Primary_Ops', 'mean')
    ).reset_index()

    # Calculate 95% CI for execution time
    ci_lower = []
    ci_upper = []
    for algo in summary['Algorithm']:
        data = df[df['Algorithm'] == algo]['Time_ms']
        _, lower, upper = calculate_confidence_interval(data)
        ci_lower.append(lower)
        ci_upper.append(upper)
    
    summary['95%_CI_Lower'] = ci_lower
    summary['95%_CI_Upper'] = ci_upper

    print(summary.to_string(index=False))
    
    # Save table for LaTeX report
    summary.to_csv(results_dir / "statistical_summary.csv", index=False)

    # 2. Figure 1: Execution Time Distribution (Boxplot)
    plt.figure(figsize=(8, 6))
    sns.boxplot(x='Algorithm', y='Time_ms', data=df, width=0.5, palette=['#1f77b4', '#ff7f0e'])
    plt.yscale('log') # Log scale because Push-Relabel might be orders of magnitude slower
    plt.title('Execution Time Distribution across 50 Source-Sink Pairs')
    plt.ylabel('Execution Time (ms) [Log Scale]')
    plt.xlabel('Algorithm')
    plt.grid(True, which="both", ls="--", alpha=0.5)
    
    fig1_path = figures_dir / "fig1_execution_time_boxplot.pdf"
    plt.savefig(fig1_path)
    print(f"\nSaved {fig1_path}")
    plt.close()

    # 3. Figure 2: Execution Time vs. Maximum Flow Value
    # Averages runs per pair first to plot a clean scatter
    avg_df = df.groupby(['Algorithm', 'Source', 'Sink', 'maxflow'])['Time_ms'].mean().reset_index()

    plt.figure(figsize=(8, 6))
    sns.scatterplot(data=avg_df, x='maxflow', y='Time_ms', hue='Algorithm', 
                    style='Algorithm', s=80, alpha=0.7, palette=['#1f77b4', '#ff7f0e'])
    
    plt.title('Algorithm Scalability: Execution Time vs. Flow Volume')
    plt.xlabel('Maximum Flow Computed')
    plt.ylabel('Average Execution Time (ms)')
    plt.xscale('log') # Flows can range from 10s to 100000s
    plt.yscale('log')
    plt.grid(True, which="both", ls="--", alpha=0.5)
    
    fig2_path = figures_dir / "fig2_scalability_scatter.pdf"
    plt.savefig(fig2_path)
    print(f"Saved {fig2_path}")
    plt.close()

if __name__ == "__main__":
    analyze_and_plot()