#include <iostream>
#include <vector>
#include <fstream>
#include <chrono>
#include <algorithm>

using namespace std;
using namespace std::chrono;

class Kosaraju {
private:
    int V;
    vector<vector<int>> adj;
    vector<vector<int>> rev_adj;
    vector<bool> visited;
    vector<int> order;

public:
    long long edge_traversals = 0;
    int num_sccs = 0;
    int max_scc_size = 0;

    Kosaraju(int V) : V(V), adj(V), rev_adj(V), visited(V, false) {}

    void addEdge(int u, int v) {
        adj[u].push_back(v);
        rev_adj[v].push_back(u); // Simultaneously build the transpose graph
    }

    // Phase 1: DFS on original graph to record finish times
    void dfs1(int u) {
        visited[u] = true;
        for (int v : adj[u]) {
            edge_traversals++;
            if (!visited[v]) {
                dfs1(v);
            }
        }
        order.push_back(u);
    }

    // Phase 3: DFS on transposed graph to extract SCCs
    int dfs2(int u) {
        visited[u] = true;
        int size = 1;
        for (int v : rev_adj[u]) {
            edge_traversals++;
            if (!visited[v]) {
                size += dfs2(v);
            }
        }
        return size;
    }

    void findSCCs() {
        // Step 1: Record finish times
        for (int i = 0; i < V; ++i) {
            if (!visited[i]) {
                dfs1(i);
            }
        }

        // Step 2: Reset visited array for the second pass
        fill(visited.begin(), visited.end(), false);

        // Step 3: Process nodes in decreasing order of finish time
        for (int i = V - 1; i >= 0; --i) {
            int u = order[i];
            if (!visited[u]) {
                int scc_size = dfs2(u);
                num_sccs++;
                max_scc_size = max(max_scc_size, scc_size);
            }
        }
    }
};

int main(int argc, char* argv[]) {
    if (argc != 2) {
        cerr << "Usage: " << argv[0] << " <graph_file>" << endl;
        return 1;
    }

    ifstream infile(argv[1]);
    if (!infile) {
        cerr << "Error opening graph file: " << argv[1] << endl;
        return 1;
    }

    int V, E;
    if (!(infile >> V >> E)) {
        cerr << "Error reading graph dimensions." << endl;
        return 1;
    }

    Kosaraju kosaraju(V);
    
    int u, v;
    while (infile >> u >> v) {
        kosaraju.addEdge(u, v);
    }
    infile.close();

    auto start = high_resolution_clock::now();
    kosaraju.findSCCs();
    auto end = high_resolution_clock::now();

    auto duration = duration_cast<microseconds>(end - start);
    
    // Output format: Algorithm, V, E, SCC_Count, Max_SCC_Size, Edge_Traversals, Time_us
    cout << "Kosaraju," << V << "," << E << "," 
         << kosaraju.num_sccs << "," << kosaraju.max_scc_size << "," 
         << kosaraju.edge_traversals << "," << duration.count() << endl;

    return 0;
}