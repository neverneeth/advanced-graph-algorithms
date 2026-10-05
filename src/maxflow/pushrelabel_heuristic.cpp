#include <algorithm>
#include <chrono>
#include <fstream>
#include <iostream>
#include <queue>
#include <vector>

using namespace std;
using namespace std::chrono;

struct Edge {
    int to;
    long long cap;
    long long flow;
    int rev;
};

class PushRelabelHeuristic {
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
    long long total_pushes = 0;
    long long saturating_pushes = 0;
    long long nonsaturating_pushes = 0;
    long long relabel_edge_scans = 0;
    long long relabel_scans_high_degree = 0;
    long long global_relabels = 0;
    long long gap_triggers = 0;
    long long stranded = 0;

    void add_to_bucket(int u) {
        if (excess[u] > 0 && height[u] < V) {
            buckets[height[u]].push_back(u);
            max_height = max(max_height, height[u]);
        }
    }

    int get_highest_active_vertex() {
        while (max_height >= 0) {
            while (!buckets[max_height].empty()) {
                int u = buckets[max_height].back();
                buckets[max_height].pop_back();
                if (excess[u] > 0 && height[u] == max_height) return u;
            }
            --max_height;
        }
        return -1;
    }

    void global_relabel(int source, int sink) {
        ++global_relabels;
        fill(height.begin(), height.end(), 2 * V);
        fill(count.begin(), count.end(), 0);
        fill(current.begin(), current.end(), 0);
        for (auto& bucket : buckets) bucket.clear();
        max_height = 0;

        queue<int> q;
        height[sink] = 0;
        count[0] = 1;
        q.push(sink);

        while (!q.empty()) {
            int v = q.front();
            q.pop();
            for (const Edge& e : adj[v]) {
                ++edge_scans;
                int w = e.to;
                if (w == source) continue;
                const Edge& back = adj[w][e.rev];
                if (back.cap - back.flow > 0 && height[w] == 2 * V) {
                    height[w] = height[v] + 1;
                    ++count[height[w]];
                    q.push(w);
                }
            }
        }

        height[source] = V;
        ++count[V];
        for (int i = 0; i < V; ++i) {
            if (i == source || i == sink) continue;
            if (height[i] == 2 * V) {
                height[i] = V;
                ++count[V];
            } else {
                add_to_bucket(i);
            }
        }
    }

    void push(int u, Edge& e, int source, int sink) {
        long long residual = e.cap - e.flow;
        long long amount = min(excess[u], residual);
        bool was_inactive = excess[e.to] == 0;

        ++total_pushes;
        if (amount == residual) ++saturating_pushes;
        else ++nonsaturating_pushes;

        e.flow += amount;
        adj[e.to][e.rev].flow -= amount;
        excess[u] -= amount;
        excess[e.to] += amount;

        if (was_inactive && e.to != source && e.to != sink) {
            add_to_bucket(e.to);
        }
    }

    void relabel(int u) {
        ++relabel_operations;
        long long arc_count = adj[u].size();
        relabel_edge_scans += arc_count;
        if (arc_count > 80) relabel_scans_high_degree += arc_count;

        int min_height = 2 * V;
        for (const Edge& e : adj[u]) {
            ++edge_scans;
            if (e.cap - e.flow > 0) {
                min_height = min(min_height, height[e.to]);
            }
        }

        int old_height = height[u];
        bool gap = false;
        if (--count[old_height] == 0 && old_height < V) {
            gap = true;
            ++gap_triggers;
            for (int i = 0; i < V; ++i) {
                if (height[i] > old_height && height[i] < V) {
                    --count[height[i]];
                    height[i] = V + 1;
                    ++count[height[i]];
                }
            }
        }
        height[u] = gap ? V + 1 : min_height + 1;
        ++count[height[u]];
        add_to_bucket(u);
    }

public:
    long long relabel_operations = 0;

    explicit PushRelabelHeuristic(int vertices)
        : V(vertices), adj(vertices), excess(vertices, 0), height(vertices, 0),
          current(vertices, 0), count(2 * vertices + 2, 0),
          buckets(2 * vertices + 2) {}

    void addEdge(int from, int to, long long capacity) {
        adj[from].push_back({to, capacity, 0, static_cast<int>(adj[to].size())});
        adj[to].push_back({from, 0, 0, static_cast<int>(adj[from].size()) - 1});
        adj[to].push_back({from, capacity, 0, static_cast<int>(adj[from].size())});
        adj[from].push_back({to, 0, 0, static_cast<int>(adj[to].size()) - 1});
    }

    long long maxFlow(int source, int sink) {
        height[source] = V;
        count[V] = 1;
        count[0] = V - 1;
        height[sink] = 0;
        excess[source] = 1e18;

        long long source_capacity = 0;
        for (auto& e : adj[source]) {
            if (e.cap - e.flow > 0) {
                source_capacity += e.cap - e.flow;
                push(source, e, source, sink);
            }
        }

        long long total_arcs = 0;
        for (const auto& edges : adj) total_arcs += edges.size();
        const long long threshold = 6LL * V + total_arcs;

        global_relabel(source, sink);
        long long work = 0;

        int u;
        while ((u = get_highest_active_vertex()) != -1) {
            while (excess[u] > 0) {
                if (current[u] == static_cast<int>(adj[u].size())) {
                    relabel(u);
                    current[u] = 0;
                    work += adj[u].size();
                    break;
                }

                ++edge_scans;
                ++work;
                Edge& e = adj[u][current[u]];
                if (e.cap - e.flow > 0 && height[u] == height[e.to] + 1) {
                    push(u, e, source, sink);
                } else {
                    ++current[u];
                }
            }

            if (work > threshold) {
                global_relabel(source, sink);
                work = 0;
            }
        }

        stranded = 0;
        for (int v = 0; v < V; ++v) {
            if (v != source && v != sink) stranded += excess[v];
        }
        if (source_capacity != excess[sink] + stranded) {
            cerr << "Error: flow conservation check failed." << endl;
            return -1;
        }
        return excess[sink];
    }

    long long get_edge_scans() const { return edge_scans; }
    long long get_total_pushes() const { return total_pushes; }
    long long get_saturating_pushes() const { return saturating_pushes; }
    long long get_nonsaturating_pushes() const { return nonsaturating_pushes; }
    long long get_relabel_edge_scans() const { return relabel_edge_scans; }
    long long get_relabel_scans_high_degree() const { return relabel_scans_high_degree; }
    long long get_global_relabels() const { return global_relabels; }
    long long get_gap_triggers() const { return gap_triggers; }
    long long get_stranded() const { return stranded; }
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
    if (source < 0 || source >= V || sink < 0 || sink >= V || source == sink) {
        cerr << "Error: source or target vertex is invalid." << endl;
        return 1;
    }

    PushRelabelHeuristic pr(V);
    for (int i = 0; i < E; ++i) {
        int u, v;
        long long capacity;
        infile >> u >> v >> capacity;
        pr.addEdge(u, v, capacity);
    }

    auto start = high_resolution_clock::now();
    long long max_flow = pr.maxFlow(source, sink);
    auto end = high_resolution_clock::now();
    auto duration = duration_cast<microseconds>(end - start);

    cout << source << "," << sink << "," << max_flow << ","
         << pr.get_edge_scans() << "," << pr.relabel_operations << ","
         << duration.count() << "," << pr.get_total_pushes() << ","
         << pr.get_saturating_pushes() << "," << pr.get_nonsaturating_pushes()
         << "," << pr.get_relabel_edge_scans() << ","
         << pr.get_relabel_scans_high_degree() << ","
         << pr.get_global_relabels() << "," << pr.get_gap_triggers() << ","
         << pr.get_stranded() << endl;
    return max_flow < 0 ? 1 : 0;
}