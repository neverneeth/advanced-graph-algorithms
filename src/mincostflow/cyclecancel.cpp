#include <iostream>
#include <vector>
#include <queue>
#include <fstream>
#include <chrono>
#include <climits>

using namespace std;
using namespace std::chrono;

struct Edge {
    int to;
    long long cap;
    long long flow;
    long long cost;
    int rev;
};

class CycleCanceling {
private:
    int V;
    vector<vector<Edge>> adj;

    vector<long long> dist;
    vector<int> parent_node;
    vector<int> parent_edge;
    vector<int> count;
    vector<bool> in_queue;

public:
    long long cycles_canceled = 0;

    CycleCanceling(int V) : V(V), adj(V), dist(V), parent_node(V), parent_edge(V), count(V), in_queue(V) {}

    void addEdge(int from, int to, long long cap, long long cost) {
        adj[from].push_back({to, cap, 0, cost, (int)adj[to].size()});
        adj[to].push_back({from, 0, 0, -cost, (int)adj[from].size() - 1});
    }

    bool establish_initial_flow(int s, int t, long long target_flow) {
        long long current_flow = 0;
        
        while (current_flow < target_flow) {
            vector<int> p_node(V, -1);
            vector<int> p_edge(V, -1);
            queue<int> q;
            q.push(s);

            while (!q.empty() && p_node[t] == -1) {
                int u = q.front();
                q.pop();

                for (int i = 0; i < adj[u].size(); ++i) {
                    auto& e = adj[u][i];
                    if (p_node[e.to] == -1 && e.to != s && e.cap - e.flow > 0) {
                        p_node[e.to] = u;
                        p_edge[e.to] = i;
                        q.push(e.to);
                    }
                }
            }

            if (p_node[t] == -1) break; 
            long long push = target_flow - current_flow;
            int curr = t;
            while (curr != s) {
                int p = p_node[curr];
                int idx = p_edge[curr];
                push = min(push, adj[p][idx].cap - adj[p][idx].flow);
                curr = p;
            }

            curr = t;
            while (curr != s) {
                int p = p_node[curr];
                int idx = p_edge[curr];
                adj[p][idx].flow += push;
                adj[curr][adj[p][idx].rev].flow -= push;
                curr = p;
            }
            current_flow += push;
        }
        return current_flow == target_flow;
    }

    bool cancel_negative_cycle() {
        fill(dist.begin(), dist.end(), 0); 
        fill(parent_node.begin(), parent_node.end(), -1);
        fill(parent_edge.begin(), parent_edge.end(), -1);
        fill(count.begin(), count.end(), 0);
        fill(in_queue.begin(), in_queue.end(), true);
        
        queue<int> q;
        for (int i = 0; i < V; ++i) q.push(i);

        int cycle_start = -1;

        while (!q.empty()) {
            int u = q.front();
            q.pop();
            in_queue[u] = false;

            for (int i = 0; i < adj[u].size(); ++i) {
                auto& e = adj[u][i];
                if (e.cap - e.flow > 0 && dist[e.to] > dist[u] + e.cost) {
                    dist[e.to] = dist[u] + e.cost;
                    parent_node[e.to] = u;
                    parent_edge[e.to] = i;

                    if (!in_queue[e.to]) {
                        q.push(e.to);
                        in_queue[e.to] = true;
                        if (++count[e.to] >= V) {
                            cycle_start = e.to;
                            break;
                        }
                    }
                }
            }
            if (cycle_start != -1) break;
        }

        if (cycle_start == -1) return false;

        int v = cycle_start;
        for (int i = 0; i < V; ++i) v = parent_node[v];

        long long bottleneck = LLONG_MAX;
        int curr = v;
        do {
            int p = parent_node[curr];
            int e_idx = parent_edge[curr];
            bottleneck = min(bottleneck, adj[p][e_idx].cap - adj[p][e_idx].flow);
            curr = p;
        } while (curr != v);

        curr = v;
        do {
            int p = parent_node[curr];
            int e_idx = parent_edge[curr];
            adj[p][e_idx].flow += bottleneck;
            adj[curr][adj[p][e_idx].rev].flow -= bottleneck;
            curr = p;
        } while (curr != v);

        cycles_canceled++;
        return true;
    }

    long long minCostFlow(int s, int t, long long target_flow) {
        if (!establish_initial_flow(s, t, target_flow)) return -1; // Infeasible
        while (cancel_negative_cycle());
        
        long long total_cost = 0;
        for (int u = 0; u < V; ++u) {
            for (const auto& e : adj[u]) {
                if (e.flow > 0 && e.cap > 0) { // Only count forward edges
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
    int source = stoi(argv[2]);
    int sink = stoi(argv[3]);
    long long required_flow = stoll(argv[4]);

    int V, E;
    infile >> V >> E;

    CycleCanceling cc(V);
    for (int i = 0; i < E; ++i) {
        int u, v;
        long long cap, cost;
        infile >> u >> v >> cap >> cost;
        cc.addEdge(u, v, cap, cost);
    }
    infile.close();

    auto start = high_resolution_clock::now();
    long long min_cost = cc.minCostFlow(source, sink, required_flow);
    auto end = high_resolution_clock::now();

    auto duration = duration_cast<microseconds>(end - start);
    
    cout << source << "," << sink << "," << required_flow << "," << min_cost << "," 
         << cc.cycles_canceled << "," << duration.count() << endl;

    return 0;
}