#include <iostream>
#include <vector>
#include <queue>
#include <fstream>
#include <chrono>
#include <algorithm>

using namespace std;
using namespace std::chrono;

struct Edge {
    int to;
    long long cap;
    long long flow;
    int rev;
};

class PushRelabelOptimized {
private:
    int V;
    vector<vector<Edge>> adj;
    vector<long long> excess;
    vector<int> height;
    vector<int> current; 
    vector<int> count;
    
    vector<vector<int>> buckets;
    int max_height = 0;

    long long edge_scans = 0; 

    void add_to_bucket(int u) {
        if (excess[u] > 0 && height[u] < V) {
            buckets[height[u]].push_back(u);
            max_height = max(max_height, height[u]);
        }
    }

    int get_highest_active_vertex() {
        while (max_height >= 0 && buckets[max_height].empty()) {
            max_height--;
        }
        if (max_height < 0) return -1;
        int u = buckets[max_height].back();
        buckets[max_height].pop_back();
        return u;
    }

    void global_relabel(int sink) {
        fill(height.begin(), height.end(), 2 * V);
        fill(count.begin(), count.end(), 0);
        for (auto& b : buckets) b.clear();
        max_height = 0;

        queue<int> q;
        q.push(sink);
        height[sink] = 0;
        count[0] = 1;

        while (!q.empty()) {
            int v = q.front();
            q.pop();
            for (auto& e : adj[v]) {
                edge_scans++;
                int rev_node = e.to;
                auto& rev_edge = adj[rev_node][e.rev];
                if (rev_edge.cap - rev_edge.flow > 0 && height[rev_node] > height[v] + 1) {
                    height[rev_node] = height[v] + 1;
                    count[height[rev_node]]++;
                    q.push(rev_node);
                }
            }
        }

        for (int i = 0; i < V; ++i) {
            if (height[i] < 2 * V) {
                add_to_bucket(i);
            } else {
                height[i] = V; 
            }
        }
    }

    void push(int u, Edge& e, int source, int sink) {
        long long d = min(excess[u], e.cap - e.flow);
        e.flow += d;
        adj[e.to][e.rev].flow -= d;
        excess[u] -= d;
        excess[e.to] += d;
        if (excess[e.to] > 0 && e.to != source && e.to != sink) {
            add_to_bucket(e.to);
        }
    }

    void relabel(int u) {
        relabel_operations++;
        int min_h = 2 * V;
        for (const Edge& e : adj[u]) {
            edge_scans++;
            if (e.cap - e.flow > 0) {
                min_h = min(min_h, height[e.to]);
            }
        }

        int old_h = height[u];
        if (--count[old_h] == 0 && old_h < V) {
            for (int i = 0; i < V; ++i) {
                if (height[i] > old_h && height[i] < V) {
                    count[height[i]]--;
                    height[i] = V + 1;
                    count[height[i]]++;
                }
            }
        }

        height[u] = min_h + 1;
        count[height[u]]++;
        add_to_bucket(u);
    }

public:
    long long relabel_operations = 0;

    PushRelabelOptimized(int V) : V(V), adj(V), excess(V, 0), height(V, 0), current(V, 0), count(2 * V + 2, 0), buckets(2 * V + 2) {}

    void addEdge(int from, int to, long long cap) {
        adj[from].push_back({to, cap, 0, (int)adj[to].size()});
        adj[to].push_back({from, 0, 0, (int)adj[from].size() - 1}); 

        adj[to].push_back({from, cap, 0, (int)adj[from].size()});
        adj[from].push_back({to, 0, 0, (int)adj[to].size() - 1});  
    }

    long long maxFlow(int source, int sink) {
        height[source] = V;
        count[V] = 1;
        count[0] = V - 1;
        height[sink] = 0;
        excess[source] = 1e18;
        for (auto& e : adj[source]) {
            if (e.cap - e.flow > 0) {
                push(source, e, source, sink);
            }
        }

        long long ops_since_global = 0;
        long long global_interval = V;

        int u;
        while ((u = get_highest_active_vertex()) != -1) {
            while (excess[u] > 0) {
                if (current[u] == adj[u].size()) {
                    relabel(u);
                    current[u] = 0;
                    ops_since_global += adj[u].size();
                    break;
                }

                edge_scans++;
                Edge& e = adj[u][current[u]];
                if (e.cap - e.flow > 0 && height[u] == height[e.to] + 1) {
                    push(u, e, source, sink);
                    if (excess[u] == 0) break;
                } else {
                    current[u]++;
                }
            }

            if (ops_since_global > global_interval * V) {
                global_relabel(sink);
                ops_since_global = 0;
            }
        }

        return excess[sink];
    }

    long long get_edge_scans() const { return edge_scans; }
};

int main(int argc, char* argv[]) {
    if (argc != 4) {
        cerr << "Usage: " << argv[0] << " <graph_file> <source> <target>" << endl;
        return 1;
    }

    const char* filename = argv[1];
    int source = stoi(argv[2]);
    int sink = stoi(argv[3]);

    ifstream infile(filename);
    if (!infile) {
        cerr << "Error opening graph file: " << filename << endl;
        return 1;
    }

    int V, E;
    infile >> V >> E;

    if (source < 0 || source >= V || sink < 0 || sink >= V) {
        cerr << "Error: source or target vertex is out of range." << endl;
        return 1;
    }

    PushRelabelOptimized pr(V);

    for (int i = 0; i < E; ++i) {
        int u, v;
        long long cap;
        infile >> u >> v >> cap;
        pr.addEdge(u, v, cap);
    }

    infile.close();

    auto start = high_resolution_clock::now();
    long long max_flow = pr.maxFlow(source, sink);
    auto end = high_resolution_clock::now();

    auto duration = duration_cast<microseconds>(end - start);
    
    cout << source << "," << sink << "," << max_flow << "," << pr.get_edge_scans() << "," << pr.relabel_operations << "," << duration.count() << endl;

    return 0;
}