import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

base = Path(__file__).resolve().parent.parent.parent
results_dir = base / "results"
log_file = base / "datasets" / "snap" / "dynamic_benchmark.csv"
plot_dir = results_dir / "plots"
plot_dir.mkdir(parents=True, exist_ok=True)

def generate_plots():
    print(f"Loading dynamic benchmark data from {log_file}...")
    df = pd.read_csv(log_file)
    
    # IEEE publication style parameters
    plt.rcParams.update({
        'font.size': 12, 'font.family': 'serif',
        'axes.labelsize': 12, 'axes.titlesize': 14,
        'figure.figsize': (8, 5)
    })

    # Apply a rolling average to smooth out CPU microsecond noise
    df['Smooth_Update_us'] = df['UpdateTime_us'].rolling(window=10, min_periods=1).mean()
    df['Smooth_Query_us'] = df['ConnectivityQuery_us'].rolling(window=10, min_periods=1).mean()

    # --- Plot 1: Microsecond Performance of Updates vs Queries ---
    print("Generating Performance Plot...")
    fig1, ax1 = plt.subplots()
    
    # Plot updates and queries on the same graph for comparison
    sns.lineplot(x='UpdateID', y='Smooth_Update_us', data=df, label='Edge Update (O(1))', color='blue', alpha=0.8, ax=ax1)
    sns.lineplot(x='UpdateID', y='Smooth_Query_us', data=df, label='Connectivity Query (BFS)', color='red', alpha=0.8, ax=ax1)
    
    ax1.set_yscale('log') # Use log scale because BFS queries are vastly slower than O(1) updates
    ax1.set_title('Dynamic Routing: Update vs. Query Time Scalability')
    ax1.set_ylabel('Execution Time (us) [Log Scale]')
    ax1.set_xlabel('Timeline (Update ID)')
    ax1.grid(True, linestyle='--', alpha=0.6)
    ax1.legend()
    plt.tight_layout()
    fig1.savefig(plot_dir / "dynamic_performance.pdf", format='pdf', dpi=300)
    
    # --- Print Summary Stats for the IEEE Table ---
    print("\n--- Statistical Summary (for IEEE Report Table) ---")
    print(f"Average Update Time:  {df['UpdateTime_us'].mean():.2f} us")
    print(f"Average Query Time:   {df['ConnectivityQuery_us'].mean():.2f} us")
    
    eulerian_states = df['EulerianPossible'].value_counts()
    print(f"\nEulerian Path Checks:")
    print(eulerian_states)
    
    print(f"\nPlots successfully saved to: {plot_dir}")

if __name__ == "__main__":
    generate_plots()