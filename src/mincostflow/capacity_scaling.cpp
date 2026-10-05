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

// Capacity scaling (Ahuja, Magnanti & Orlin): source starts with excess
// target_flow and sink with the matching deficit. Each Delta-phase first
// saturates residual arcs >= Delta with negative reduced cost (Delta-optimality),
// then augments from excess to deficit nodes along shortest paths in G(Delta).
class CapacityScaling {
private:
    int V;
    vector<vector<Edge>> adj;
    vector<long long> dist;
    vector<long long> pi;
    vector<long long> excess;
    vector<int> parent_node;
    vector<int> parent_edge;

    void push_flow(int u, Edge& e, long long amount) {
        e.flow += amount;
        adj[e.to][e.rev].flow -= amount;
        excess[u] -= amount;
        excess[e.to] += amount;
    }

    // Dijkstra from k over arcs with residual >= delta, stopping at the first
    // node with deficit <= -delta. Returns that node, or -1 if none is reachable.
    int shortest_path(int k, long long delta) {
        searches++;
        fill(dist.begin(), dist.end(), LLONG_MAX);
        fill(parent_node.begin(), parent_node.end(), -1);
        fill(parent_edge.begin(), parent_edge.end(), -1);
        priority_queue<pair<long long, int>, vector<pair<long long, int>>, greater<pair<long long, int>>> pq;
        dist[k] = 0;
        pq.push({0, k});
        int target = -1;

        while (!pq.empty()) {
            auto [d, u] = pq.top();
            pq.pop();
            if (d > dist[u]) continue;
            if (excess[u] <= -delta) {
                target = u;
                break;
            }
            for (size_t i = 0; i < adj[u].size(); ++i) {
                relaxation_checks++;
                auto& e = adj[u][i];
                if (e.cap - e.flow < delta) continue;
                long long reduced_cost = e.cost + pi[u] - pi[e.to];
                if (dist[e.to] > d + reduced_cost) {
                    dist[e.to] = d + reduced_cost;
                    parent_node[e.to] = u;
                    parent_edge[e.to] = i;
                    pq.push({dist[e.to], e.to});
                }
            }
        }
        if (target == -1) return -1;

        // pi += min(dist, dist[target]) keeps every G(delta) reduced cost >= 0,
        // including arcs into nodes the search never reached.
        long long limit = dist[target];
        for (int i = 0; i < V; ++i) pi[i] += min(dist[i], limit);
        return target;
    }

public:
    long long augmentations = 0;
    long long scaling_phases = 0;
    long long searches = 0;
    long long relaxation_checks = 0;
    long long saturated_arcs = 0;

    CapacityScaling(int V)
        : V(V), adj(V), dist(V), pi(V, 0), excess(V, 0), parent_node(V), parent_edge(V) {}

    void addEdge(int from, int to, long long cap, long long cost) {
        adj[from].push_back({to, cap, 0, cost, (int)adj[to].size(), true});
        adj[to].push_back({from, 0, 0, -cost, (int)adj[from].size() - 1, false});
    }

    long long minCostFlow(int s, int t, long long target_flow) {
        if (target_flow == 0) return 0;
        excess[s] = target_flow;
        excess[t] = -target_flow;

        long long max_cap = target_flow;
        for (int u = 0; u < V; ++u)
            for (const auto& e : adj[u]) max_cap = max(max_cap, e.cap);

        long long delta = 1;
        while (delta <= max_cap / 2) delta *= 2;

        for (; delta >= 1; delta /= 2) {
            scaling_phases++;

            for (int u = 0; u < V; ++u) {
                for (auto& e : adj[u]) {
                    long long residual = e.cap - e.flow;
                    if (residual >= delta && e.cost + pi[u] - pi[e.to] < 0) {
                        push_flow(u, e, residual);
                        saturated_arcs++;
                    }
                }
            }

            // Excess nodes that cannot reach a deficit node in G(delta) are
            // skipped for the rest of this phase.
            vector<char> stuck(V, 0);
            while (true) {
                int k = -1;
                for (int i = 0; i < V; ++i) {
                    if (excess[i] >= delta && !stuck[i]) {
                        k = i;
                        break;
                    }
                }
                if (k == -1) break;

                int l = shortest_path(k, delta);
                if (l == -1) {
                    stuck[k] = 1;
                    continue;
                }

                long long push = min(excess[k], -excess[l]);
                for (int v = l; v != k; v = parent_node[v]) {
                    auto& e = adj[parent_node[v]][parent_edge[v]];
                    push = min(push, e.cap - e.flow);
                }
                for (int v = l; v != k; v = parent_node[v]) {
                    int u = parent_node[v];
                    push_flow(u, adj[u][parent_edge[v]], push);
                }
                // push_flow moved excess through every intermediate node and
                // back out again, so only the endpoints change net.
                augmentations++;
            }
        }

        for (int i = 0; i < V; ++i)
            if (excess[i] != 0) return -1;

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
         << cs.augmentations << "," << duration.count() << ","
         << cs.searches << "," << cs.relaxation_checks << ","
         << cs.scaling_phases << "," << cs.saturated_arcs << endl;

    return 0;
}