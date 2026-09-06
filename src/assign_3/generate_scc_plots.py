import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path

# Paths
base = Path(__file__).resolve().parent.parent.parent
results_dir = base / "results"
log_file = results_dir / "logs" / "scc_benchmark_results.csv"
plot_dir = results_dir / "plots"
plot_dir.mkdir(parents=True, exist_ok=True)

def generate_plots():
    print(f"Loading data from {log_file}...")
    df = pd.read_csv(log_file)
    
    # Convert units for better readability in plots
    df['Time_ms'] = df['Time_us'] / 1000.0
    df['Memory_MB'] = df['Memory_KB'] / 1024.0
    
    # Aggregate data (mean of the runs for each scale and algorithm)
    avg_df = df.groupby(['Algorithm', 'Scale_Pct', 'Nodes', 'Edges']).agg({
        'Time_ms': 'mean',
        'Memory_MB': 'mean'
    }).reset_index()

    # IEEE publication style parameters
    plt.rcParams.update({
        'font.size': 12,
        'font.family': 'serif',
        'axes.labelsize': 12,
        'axes.titlesize': 14,
        'legend.fontsize': 11,
        'xtick.labelsize': 11,
        'ytick.labelsize': 11,
        'figure.figsize': (7, 5)
    })

    # --- Plot 1: Execution Time Scalability ---
    print("Generating Execution Time Scalability Plot...")
    fig1, ax1 = plt.subplots()
    sns.lineplot(x='Scale_Pct', y='Time_ms', hue='Algorithm', style='Algorithm', 
                 markers=True, dashes=False, data=avg_df, linewidth=2, markersize=8, ax=ax1, palette='Set1')
    ax1.set_title('Execution Time Scalability on Web Graph')
    ax1.set_ylabel('Mean Execution Time (ms)')
    ax1.set_xlabel('Graph Scale (% of Google Web Graph)')
    ax1.grid(True, linestyle='--', alpha=0.6)
    ax1.set_xticks(avg_df['Scale_Pct'].unique())
    plt.tight_layout()
    fig1.savefig(plot_dir / "scc_time_scalability.pdf", format='pdf', dpi=300)
    
    # --- Plot 2: Peak Memory Usage ---
    print("Generating Memory Usage Plot...")
    fig2, ax2 = plt.subplots()
    sns.barplot(x='Scale_Pct', y='Memory_MB', hue='Algorithm', data=avg_df, ax=ax2, palette='Set1', alpha=0.8)
    ax2.set_title('Peak Memory Consumption Comparison')
    ax2.set_ylabel('Peak Memory Usage (MB)')
    ax2.set_xlabel('Graph Scale (% of Google Web Graph)')
    ax2.grid(axis='y', linestyle='--', alpha=0.6)
    plt.tight_layout()
    fig2.savefig(plot_dir / "scc_memory_usage.pdf", format='pdf', dpi=300)

    # --- Statistical Summary for LaTeX ---
    print("\n--- 100% Scale Statistical Summary (for IEEE Report Table) ---")
    full_scale = df[df['Scale_Pct'] == 100].groupby('Algorithm').agg(
        Mean_Time_ms=('Time_ms', 'mean'),
        Std_Dev_Time=('Time_ms', 'std'),
        Mean_Memory_MB=('Memory_MB', 'mean'),
        Traversals=('Traversals', 'mean')
    ).reset_index()
    
    print(full_scale.to_string(index=False, float_format="%.2f"))
    print(f"\nPlots successfully saved to: {plot_dir}")

if __name__ == "__main__":
    generate_plots()