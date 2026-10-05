#include <chrono>
#include <climits>
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
    long long cost;
    int rev;
    bool original;
};

class CycleCancelingOptimized {
private:
    int V;
    vector<vector<Edge>> adj;
    vector<long long> dist;
    vector<int> parent_node;
    vector<int> parent_edge;

    // Any cycle in the parent-pointer graph has negative cost, so we can stop
    // as soon as one appears instead of finishing all V Bellman-Ford passes.
    int find_parent_cycle() {
        vector<int> state(V, 0);  // 0 new, 1 on current walk, 2 done
        for (int s = 0; s < V; ++s) {
            if (state[s]) continue;
            int v = s;
            while (v != -1 && state[v] == 0) {
                state[v] = 1;
                v = parent_node[v];
            }
            if (v != -1 && state[v] == 1) return v;
            for (int u = s; u != -1 && state[u] == 1; u = parent_node[u]) state[u] = 2;
        }
        return -1;
    }

    bool cancel_negative_cycle() {
        ++searches;
        fill(dist.begin(), dist.end(), 0);
        fill(parent_node.begin(), parent_node.end(), -1);
        fill(parent_edge.begin(), parent_edge.end(), -1);
        int v = -1;

        for (int iter = 0; iter < V && v == -1; ++iter) {
            ++passes;
            bool changed = false;
            for (int u = 0; u < V; ++u) {
                for (size_t i = 0; i < adj[u].size(); ++i) {
                    ++relaxation_checks;
                    Edge& e = adj[u][i];
                    if (e.cap - e.flow > 0 && dist[e.to] > dist[u] + e.cost) {
                        dist[e.to] = dist[u] + e.cost;
                        parent_node[e.to] = u;
                        parent_edge[e.to] = i;
                        changed = true;
                    }
                }
            }
            if (!changed) return false;
            v = find_parent_cycle();
        }
        if (v == -1) return false;

        long long bottleneck = LLONG_MAX;
        int current = v;
        do {
            int parent = parent_node[current];
            int index = parent_edge[current];
            bottleneck = min(bottleneck, adj[parent][index].cap - adj[parent][index].flow);
            current = parent;
        } while (current != v);

        current = v;
        do {
            int parent = parent_node[current];
            int index = parent_edge[current];
            adj[parent][index].flow += bottleneck;
            adj[current][adj[parent][index].rev].flow -= bottleneck;
            current = parent;
        } while (current != v);
        ++cycles_canceled;
        return true;
    }

public:
    long long cycles_canceled = 0;
    long long searches = 0;
    long long relaxation_checks = 0;
    long long passes = 0;

    explicit CycleCancelingOptimized(int vertices)
        : V(vertices), adj(vertices), dist(vertices), parent_node(vertices), parent_edge(vertices) {}

    void addEdge(int from, int to, long long capacity, long long cost) {
        adj[from].push_back({to, capacity, 0, cost, static_cast<int>(adj[to].size()), true});
        adj[to].push_back({from, 0, 0, -cost, static_cast<int>(adj[from].size()) - 1, false});
    }

    bool establish_initial_flow(int source, int sink, long long target_flow) {
        long long current_flow = 0;
        while (current_flow < target_flow) {
            vector<int> parent(V, -1), parent_index(V, -1);
            queue<int> q;
            q.push(source);
            while (!q.empty() && parent[sink] == -1) {
                int u = q.front();
                q.pop();
                for (size_t i = 0; i < adj[u].size(); ++i) {
                    Edge& e = adj[u][i];
                    if (parent[e.to] == -1 && e.to != source && e.cap - e.flow > 0) {
                        parent[e.to] = u;
                        parent_index[e.to] = i;
                        q.push(e.to);
                    }
                }
            }
            if (parent[sink] == -1) return false;
            long long amount = target_flow - current_flow;
            for (int v = sink; v != source; v = parent[v]) {
                int u = parent[v];
                amount = min(amount, adj[u][parent_index[v]].cap - adj[u][parent_index[v]].flow);
            }
            for (int v = sink; v != source; v = parent[v]) {
                int u = parent[v];
                int i = parent_index[v];
                adj[u][i].flow += amount;
                adj[v][adj[u][i].rev].flow -= amount;
            }
            current_flow += amount;
        }
        return true;
    }

    long long minCostFlow(int source, int sink, long long target_flow) {
        if (!establish_initial_flow(source, sink, target_flow)) return -1;
        while (cancel_negative_cycle()) {}
        long long total_cost = 0;
        for (int u = 0; u < V; ++u)
            for (const Edge& e : adj[u])
                if (e.original && e.flow > 0) total_cost += e.flow * e.cost;
        return total_cost;
    }
};

int main(int argc, char* argv[]) {
    if (argc != 5) return 1;
    ifstream infile(argv[1]);
    if (!infile) return 1;
    int source = stoi(argv[2]);
    int sink = stoi(argv[3]);
    long long target_flow = stoll(argv[4]);
    int V, E;
    infile >> V >> E;
    if (source < 0 || source >= V || sink < 0 || sink >= V || target_flow < 0) return 1;

    CycleCancelingOptimized algorithm(V);
    for (int i = 0; i < E; ++i) {
        int u, v;
        long long capacity, cost;
        infile >> u >> v >> capacity >> cost;
        algorithm.addEdge(u, v, capacity, cost);
    }
    auto start = high_resolution_clock::now();
    long long cost = algorithm.minCostFlow(source, sink, target_flow);
    auto end = high_resolution_clock::now();
    cout << source << "," << sink << "," << target_flow << "," << cost << ","
         << algorithm.cycles_canceled << ","
         << duration_cast<microseconds>(end - start).count() << ","
         << algorithm.searches << "," << algorithm.relaxation_checks << ","
         << algorithm.passes << endl;
}