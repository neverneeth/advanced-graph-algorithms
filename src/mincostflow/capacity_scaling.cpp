#include <iostream>
#include <vector>
#include <queue>
#include <fstream>
#include <chrono>
#include <climits>
#include <algorithm>
#include <stdexcept>

using namespace std;
using namespace std::chrono;

struct Edge {
    int to;
    long long cap;
    long long flow;
    long long cost;
    int rev;
    bool original; 
};

class CapacityScaling {
private:
    int V;
    vector<vector<Edge>> adj;
    vector<long long> dist;
    vector<long long> pi;
    vector<int> parent_node;
    vector<int> parent_edge;

public:
    long long augmentations = 0;
    long long scaling_phases = 0;

    CapacityScaling(int V) : V(V), adj(V), dist(V), pi(V, 0), parent_node(V), parent_edge(V) {}

    void addEdge(int from, int to, long long cap, long long cost) {
        adj[from].push_back({to, cap, 0, cost, (int)adj[to].size(), true});
        adj[to].push_back({from, 0, 0, -cost, (int)adj[from].size() - 1, false});
    }

    long long minCostFlow(int s, int t, long long target_flow) {
        long long max_cap = 0;
        for (int u = 0; u < V; ++u) {
            for (const auto& e : adj[u]) {
                max_cap = max(max_cap, e.cap);
            }
        }

        long long delta = 1;
        while (delta <= max_cap) delta *= 2;
        delta /= 2;
        if (delta == 0) delta = 1;

        long long current_flow = 0;
        
        while (delta >= 1 && current_flow < target_flow) {
            scaling_phases++;
            bool path_found = true;
            
            while (path_found && current_flow < target_flow) {
                fill(dist.begin(), dist.end(), LLONG_MAX);
                fill(parent_node.begin(), parent_node.end(), -1);
                fill(parent_edge.begin(), parent_edge.end(), -1);
                
                priority_queue<pair<long long, int>, vector<pair<long long, int>>, greater<pair<long long, int>>> pq;
                
                dist[s] = 0;
                pq.push({0, s});
                
                while (!pq.empty()) {
                    auto [d, u] = pq.top();
                    pq.pop();
                    
                    if (d > dist[u]) continue; 
                    
                    for (size_t i = 0; i < adj[u].size(); ++i) {
                        auto& e = adj[u][i];
                        
                        if (e.cap - e.flow >= delta) {
                            long long reduced_cost = e.cost + pi[u] - pi[e.to];
                            
                            if (reduced_cost < 0) reduced_cost = 0; 

                            if (dist[e.to] > dist[u] + reduced_cost) {
                                dist[e.to] = dist[u] + reduced_cost;
                                parent_node[e.to] = u;
                                parent_edge[e.to] = i;
                                pq.push({dist[e.to], e.to});
                            }
                        }
                    }
                }
                
                if (dist[t] == LLONG_MAX) {
                    path_found = false; 
                } else {
                    for (int i = 0; i < V; ++i) {
                        if (dist[i] != LLONG_MAX) {
                            pi[i] += dist[i];
                        }
                    }
                    
                    long long push = target_flow - current_flow;
                    int curr = t;
                    while (curr != s) {
                        int p = parent_node[curr];
                        int idx = parent_edge[curr];
                        push = min(push, adj[p][idx].cap - adj[p][idx].flow);
                        curr = p;
                    }
                    
                    curr = t;
                    while (curr != s) {
                        int p = parent_node[curr];
                        int idx = parent_edge[curr];
                        adj[p][idx].flow += push;
                        adj[curr][adj[p][idx].rev].flow -= push;
                        curr = p;
                    }
                    
                    current_flow += push;
                    augmentations++;
                }
            }
            delta /= 2; 
                }
        
        if (current_flow < target_flow) return -1; 
        long long total_cost = 0;
        for (int u = 0; u < V; ++u) {
            for (const auto& e : adj[u]) {
                if (e.original && e.flow > 0) {
                    total_cost += e.flow * e.cost;
                }
            }
        }
        return total_cost;
    }
};

int main(int argc, char* argv[]) {
    if (argc != 5) {
        cerr << "Usage: " << argv[0] << " <graph_file> <source> <target> <required_flow>" << endl;
        return 1;
    }

    ifstream infile(argv[1]);
    if (!infile) {
        cerr << "Error opening graph file: " << argv[1] << endl;
        return 1;
    }

    int source, sink;
    long long required_flow;

    try {
        source = stoi(argv[2]);
        sink = stoi(argv[3]);
        required_flow = stoll(argv[4]);
    } catch (const invalid_argument& e) {
        cerr << "Error: Invalid numeric arguments provided." << endl;
        return 1;
    }

    int V, E;
    if (!(infile >> V >> E)) {
        cerr << "Error reading graph dimensions." << endl;
        return 1;
    }

    if (source < 0 || source >= V || sink < 0 || sink >= V || required_flow < 0) {
        cerr << "Error: Out of bounds or negative flow requested." << endl;
        return 1;
    }

    CapacityScaling cs(V);
    for (int i = 0; i < E; ++i) {
        int u, v;
        long long cap, cost;
        infile >> u >> v >> cap >> cost;
        cs.addEdge(u, v, cap, cost);
    }
    infile.close();

    auto start = high_resolution_clock::now();
    long long min_cost = cs.minCostFlow(source, sink, required_flow);
    auto end = high_resolution_clock::now();

    auto duration = duration_cast<microseconds>(end - start);
    
    cout << source << "," << sink << "," << required_flow << "," << min_cost << "," 
         << cs.augmentations << "," << duration.count() << endl;

    return 0;
}