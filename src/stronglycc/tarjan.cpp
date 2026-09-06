#include <iostream>
#include <vector>
#include <stack>
#include <fstream>
#include <chrono>
#include <algorithm>

using namespace std;
using namespace std::chrono;

class TarjanSCC {
private:
    int V;
    vector<vector<int>> adj;
    vector<int> disc;
    vector<int> low;
    vector<bool> in_stack;
    stack<int> st;
    int timer;

public:
    long long edge_traversals = 0;
    int num_sccs = 0;
    int max_scc_size = 0;

    TarjanSCC(int V) : V(V), adj(V), disc(V, -1), low(V, -1), in_stack(V, false), timer(0) {}

    void addEdge(int u, int v) {
        adj[u].push_back(v);
    }

    void dfs(int u) {
        disc[u] = low[u] = ++timer;
        st.push(u);
        in_stack[u] = true;

        for (int v : adj[u]) {
            edge_traversals++;
            if (disc[v] == -1) {
                dfs(v);
                low[u] = min(low[u], low[v]);
            } else if (in_stack[v]) {
                low[u] = min(low[u], disc[v]);
            }
        }

        // Root of an SCC found
        if (low[u] == disc[u]) {
            int current_scc_size = 0;
            while (true) {
                int node = st.top();
                st.pop();
                in_stack[node] = false;
                current_scc_size++;
                if (node == u) break;
            }
            num_sccs++;
            max_scc_size = max(max_scc_size, current_scc_size);
        }
    }

    void findSCCs() {
        for (int i = 0; i < V; ++i) {
            if (disc[i] == -1) {
                dfs(i);
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

    TarjanSCC tarjan(V);
    int u, v;
    while (infile >> u >> v) {
        tarjan.addEdge(u, v);
    }
    infile.close();

    auto start = high_resolution_clock::now();
    tarjan.findSCCs();
    auto end = high_resolution_clock::now();

    auto duration = duration_cast<microseconds>(end - start);

    // Format matches Kosaraju: Algorithm, V, E, SCC_Count, Max_SCC_Size, Edge_Traversals, Time_us
    cout << "Tarjan," << V << "," << E << "," 
         << tarjan.num_sccs << "," << tarjan.max_scc_size << "," 
         << tarjan.edge_traversals << "," << duration.count() << endl;

    return 0;
}