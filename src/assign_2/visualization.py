import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path

# Paths
base = Path(__file__).resolve().parent.parent.parent
# Adjust if your script is in a different depth
results_dir = base / "results"
log_file = results_dir / "logs" / "mcf_benchmark_results.csv"
plot_dir = results_dir / "plots"
plot_dir.mkdir(parents=True, exist_ok=True)

def generate_plots():
    print(f"Loading data from {log_file}...")
    df = pd.read_csv(log_file)
    
    # Convert microseconds to milliseconds for readability
    df['Time_ms'] = df['Time_us'] / 1000.0
    
    # Set IEEE publication style parameters
    plt.rcParams.update({
        'font.size': 12,
        'font.family': 'serif',
        'axes.labelsize': 12,
        'axes.titlesize': 14,
        'legend.fontsize': 11,
        'xtick.labelsize': 11,
        'ytick.labelsize': 11,
        'figure.figsize': (8, 5)
    })

    # --- Plot 1: Execution Time Boxplot (Log Scale) ---
    print("Generating Execution Time Boxplot...")
    fig1, ax1 = plt.subplots()
    sns.boxplot(x='Algorithm', y='Time_ms', data=df, ax=ax1, palette='Set2')
    ax1.set_yscale('log')
    ax1.set_title('Minimum Cost Flow Execution Time Distribution')
    ax1.set_ylabel('Execution Time (ms) [Log Scale]')
    ax1.set_xlabel('Algorithm')
    plt.tight_layout()
    fig1.savefig(plot_dir / "mcf_execution_time_boxplot.pdf", format='pdf', dpi=300)
    
    # --- Plot 2: Scalability Scatter Plot (Log Scale) ---
    print("Generating Scalability Scatter Plot...")
    # Average the 5 runs per pair to reduce noise
    avg_df = df.groupby(['Pair_ID', 'Target_Flow', 'Algorithm'])['Time_ms'].mean().reset_index()
    
    fig2, ax2 = plt.subplots()
    sns.scatterplot(x='Target_Flow', y='Time_ms', hue='Algorithm', style='Algorithm', 
                    data=avg_df, s=60, alpha=0.8, ax=ax2, palette='Set2')
    ax2.set_yscale('log')
    ax2.set_title('Algorithm Scalability: Execution Time vs. Target Flow')
    ax2.set_ylabel('Mean Execution Time (ms) [Log Scale]')
    ax2.set_xlabel('Target Logistics Flow (Units)')
    ax2.grid(True, which="both", ls="--", alpha=0.3)
    plt.tight_layout()
    fig2.savefig(plot_dir / "mcf_scalability_scatter.pdf", format='pdf', dpi=300)

    # --- Statistical Summary for LaTeX ---
    print("\n--- Statistical Summary (for IEEE Report Table) ---")
    summary = df.groupby('Algorithm').agg(
        Mean_Time_ms=('Time_ms', 'mean'),
        Std_Dev_ms=('Time_ms', 'std'),
        Mean_Primary_Ops=('Primary_Ops', 'mean'),
        Count=('Time_ms', 'count')
    ).reset_index()

    # Calculate 95% Confidence Intervals
    # CI = 1.96 * (std / sqrt(n))
    summary['95%_CI_Lower'] = summary['Mean_Time_ms'] - (1.96 * (summary['Std_Dev_ms'] / np.sqrt(summary['Count'])))
    summary['95%_CI_Upper'] = summary['Mean_Time_ms'] + (1.96 * (summary['Std_Dev_ms'] / np.sqrt(summary['Count'])))
    
    # Drop the Count column before displaying
    summary = summary.drop(columns=['Count'])
    print(summary.to_string(index=False))
    
    print(f"\nPlots saved to: {plot_dir}")

if __name__ == "__main__":
    generate_plots()