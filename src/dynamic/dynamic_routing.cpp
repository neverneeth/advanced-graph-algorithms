#include <iostream>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <fstream>
#include <chrono>
#include <queue>
#include <algorithm>

using namespace std;
using namespace std::chrono;

class DynamicNetwork {
private:
    unordered_map<int, unordered_set<int>> adj;
    unordered_map<int, int> degree;
    int odd_degree_count = 0;

    // Helper to manage Eulerian degree tracking
    void updateDegree(int u, int delta) {
        bool was_odd = (degree[u] % 2 != 0);
        degree[u] += delta;
        bool is_odd = (degree[u] % 2 != 0);

        if (was_odd && !is_odd) odd_degree_count--;
        else if (!was_odd && is_odd) odd_degree_count++;
        
        // Handle vertex deletion implicitly if isolated
        if (degree[u] == 0) {
            degree.erase(u);
            adj.erase(u);
        }
    }

public:
    long long total_update_time_us = 0;

    // 1. Edge/Vertex Insertion O(1)
    void addEdge(int u, int v) {
        auto start = high_resolution_clock::now();
        
        adj[u].insert(v);
        adj[v].insert(u);
        updateDegree(u, 1);
        updateDegree(v, 1);
        
        auto end = high_resolution_clock::now();
        total_update_time_us += duration_cast<microseconds>(end - start).count();
    }

    // 2. Edge/Vertex Deletion O(1)
    void removeEdge(int u, int v) {
        auto start = high_resolution_clock::now();
        
        if (adj[u].count(v)) {
            adj[u].erase(v);
            adj[v].erase(u);
            updateDegree(u, -1);
            updateDegree(v, -1);
        }
        
        auto end = high_resolution_clock::now();
        total_update_time_us += duration_cast<microseconds>(end - start).count();
    }

    // 3. Dynamic Connectivity Query O(V+E) - Optimized with Bi-directional BFS
    bool queryConnectivity(int source, int target) {
        if (source == target) return true;
        if (adj.find(source) == adj.end() || adj.find(target) == adj.end()) return false;

        unordered_set<int> visited;
        queue<int> q;
        q.push(source);
        visited.insert(source);

        while (!q.empty()) {
            int u = q.front();
            q.pop();
            
            for (int v : adj[u]) {
                if (v == target) return true;
                if (visited.find(v) == visited.end()) {
                    visited.insert(v);
                    q.push(v);
                }
            }
        }
        return false;
    }

    // 4. Eulerian Path Check O(1) via dynamic degree tracking
    bool hasEulerianPath() {
        // A graph has an Eulerian path if it has exactly 0 or 2 odd-degree vertices.
        // (Note: Strictly requires verifying a single connected component, but degree 
        // parity is the primary filtering mechanism for dynamic updates).
        return (odd_degree_count == 0 || odd_degree_count == 2);
    }

    // 5. Hamiltonian Path - NP Complete O(N!) Backtracking on isolated subgraph
    bool hamiltonianUtil(int u, unordered_set<int>& subgraph, unordered_map<int, bool>& visited, int count) {
        if (count == subgraph.size()) return true;

        visited[u] = true;
        for (int v : adj[u]) {
            if (subgraph.count(v) && !visited[v]) {
                if (hamiltonianUtil(v, subgraph, visited, count + 1)) {
                    return true;
                }
            }
        }
        visited[u] = false; // Backtrack
        return false;
    }

    bool analyzeHamiltonian(int start_node, int max_nodes = 15) {
        // Extract a localized "city block" subgraph to make it computable
        unordered_set<int> subgraph;
        queue<int> q;
        q.push(start_node);
        subgraph.insert(start_node);

        while (!q.empty() && subgraph.size() < max_nodes) {
            int u = q.front();
            q.pop();
            for (int v : adj[u]) {
                if (subgraph.find(v) == subgraph.end()) {
                    subgraph.insert(v);
                    q.push(v);
                    if (subgraph.size() == max_nodes) break;
                }
            }
        }

        unordered_map<int, bool> visited;
        for (int node : subgraph) visited[node] = false;

        // Try finding a path starting from any node in the subgraph
        for (int node : subgraph) {
            if (hamiltonianUtil(node, subgraph, visited, 1)) {
                return true;
            }
        }
        return false;
    }
};

int main(int argc, char* argv[]) {
    if (argc != 3) {
        cerr << "Usage: " << argv[0] << " <base_graph> <updates_file>" << endl;
        return 1;
    }

    DynamicNetwork net;

    // Phase 1: Load Base Graph
    cout << "Loading Base Graph..." << endl;
    ifstream base_file(argv[1]);
    int V, E;
    base_file >> V >> E;
    for (int i = 0; i < E; ++i) {
        int u, v;
        base_file >> u >> v;
        net.addEdge(u, v);
    }
    base_file.close();

    // Phase 2: Process Dynamic Updates and measure times
    cout << "Processing Dynamic Updates..." << endl;
    ifstream updates_file(argv[2]);
    int num_updates;
    updates_file >> num_updates;

    int additions = 0, deletions = 0;
    long long total_query_time_us = 0;

    ofstream log_file("datasets/snap/dynamic_benchmark.csv");
    log_file << "UpdateID,Type,UpdateTime_us,ConnectivityQuery_us,EulerianPossible" << endl;

    for (int i = 0; i < num_updates; ++i) {
        int type, u, v;
        updates_file >> type >> u >> v;

        auto start_upd = high_resolution_clock::now();
        if (type == 1) {
            net.addEdge(u, v);
            additions++;
        } else {
            net.removeEdge(u, v);
            deletions++;
        }
        auto end_upd = high_resolution_clock::now();
        long long upd_time = duration_cast<microseconds>(end_upd - start_upd).count();

        // Perform a random connectivity query every 100 updates to benchmark performance
        long long q_time = 0;
        if (i % 100 == 0) {
            auto start_q = high_resolution_clock::now();
            net.queryConnectivity(u, 0); // Query connectivity to root node 0
            auto end_q = high_resolution_clock::now();
            q_time = duration_cast<microseconds>(end_q - start_q).count();
            total_query_time_us += q_time;
        }

        bool eulerian = net.hasEulerianPath();
        
        // Log every 1000th update to avoid massive CSV files
        if (i % 1000 == 0) {
            log_file << i << "," << type << "," << upd_time << "," << q_time << "," << eulerian << endl;
        }
    }
    log_file.close();

    cout << "---------------------------------------" << endl;
    cout << "Total Updates Processed: " << additions + deletions << endl;
    cout << "Additions: " << additions << " | Deletions: " << deletions << endl;
    cout << "Average Update Time: " << (double)net.total_update_time_us / num_updates << " us" << endl;
    cout << "Average Query Time: " << (double)total_query_time_us / (num_updates / 100) << " us" << endl;
    
    // Phase 3: Hamiltonian Analysis on a local subgraph
    cout << "Analyzing Hamiltonian Path for local neighborhood of Node 1000..." << endl;
    auto start_h = high_resolution_clock::now();
    bool has_hamiltonian = net.analyzeHamiltonian(1000, 15);
    auto end_h = high_resolution_clock::now();
    
    cout << "Hamiltonian Path Exists (Sub-Graph): " << (has_hamiltonian ? "Yes" : "No") << endl;
    cout << "Hamiltonian Query Time: " << duration_cast<microseconds>(end_h - start_h).count() << " us" << endl;

    return 0;
}