#include <algorithm>
#include <chrono>
#include <climits>
#include <fstream>
#include <functional>
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

class SuccessiveShortestPath {
private:
    int V;
    vector<vector<Edge>> adj;
    vector<long long> dist;
    vector<long long> potential;
    vector<int> parent_node;
    vector<int> parent_edge;

public:
    long long augmentations = 0;
    long long searches = 0;
    long long relaxation_checks = 0;

    explicit SuccessiveShortestPath(int vertices)
        : V(vertices), adj(vertices), dist(vertices), potential(vertices, 0),
          parent_node(vertices), parent_edge(vertices) {}

    void addEdge(int from, int to, long long capacity, long long cost) {
        adj[from].push_back({to, capacity, 0, cost, static_cast<int>(adj[to].size()), true});
        adj[to].push_back({from, 0, 0, -cost, static_cast<int>(adj[from].size()) - 1, false});
    }

    long long minCostFlow(int source, int sink, long long target_flow) {
        long long current_flow = 0;
        while (current_flow < target_flow) {
            ++searches;
            fill(dist.begin(), dist.end(), LLONG_MAX);
            fill(parent_node.begin(), parent_node.end(), -1);
            fill(parent_edge.begin(), parent_edge.end(), -1);
            priority_queue<pair<long long, int>, vector<pair<long long, int>>, greater<>> pq;
            dist[source] = 0;
            pq.push({0, source});

            while (!pq.empty()) {
                auto [distance, u] = pq.top();
                pq.pop();
                if (distance != dist[u]) continue;
                for (size_t i = 0; i < adj[u].size(); ++i) {
                    ++relaxation_checks;
                    Edge& e = adj[u][i];
                    if (e.cap - e.flow <= 0) continue;
                    long long reduced_cost = e.cost + potential[u] - potential[e.to];
                    if (dist[e.to] > dist[u] + reduced_cost) {
                        dist[e.to] = dist[u] + reduced_cost;
                        parent_node[e.to] = u;
                        parent_edge[e.to] = i;
                        pq.push({dist[e.to], e.to});
                    }
                }
            }

            if (dist[sink] == LLONG_MAX) return -1;
            for (int i = 0; i < V; ++i)
                if (dist[i] != LLONG_MAX) potential[i] += dist[i];

            long long amount = target_flow - current_flow;
            for (int v = sink; v != source; v = parent_node[v]) {
                int u = parent_node[v];
                if (u < 0) return -1;
                amount = min(amount, adj[u][parent_edge[v]].cap - adj[u][parent_edge[v]].flow);
            }
            for (int v = sink; v != source; v = parent_node[v]) {
                int u = parent_node[v];
                int i = parent_edge[v];
                adj[u][i].flow += amount;
                adj[v][adj[u][i].rev].flow -= amount;
            }
            current_flow += amount;
            ++augmentations;
        }

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

    SuccessiveShortestPath algorithm(V);
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
         << algorithm.augmentations << ","
         << duration_cast<microseconds>(end - start).count() << ","
         << algorithm.searches << "," << algorithm.relaxation_checks << endl;
}