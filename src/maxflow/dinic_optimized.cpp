#include <climits>
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

class DinicOptimized {
private:
    int V;
    vector<vector<Edge>> adj;
    vector<int> level;
    vector<int> ptr;

    bool bfs(int source, int sink) {
        fill(level.begin(), level.end(), -1);
        level[source] = 0;
        queue<int> q;
        q.push(source);
        while (!q.empty()) {
            int v = q.front();
            q.pop();
            for (const Edge& e : adj[v]) {
                ++bfs_operations;
                if (level[e.to] < 0 && e.flow < e.cap) {
                    level[e.to] = level[v] + 1;
                    if (e.to == sink) return true;
                    q.push(e.to);
                }
            }
        }
        return false;
    }

    long long dfs(int v, int sink, long long pushed) {
        if (pushed == 0 || v == sink) return pushed;
        for (int& cid = ptr[v]; cid < static_cast<int>(adj[v].size()); ++cid) {
            ++dfs_operations;
            Edge& e = adj[v][cid];
            if (level[e.to] != level[v] + 1 || e.cap - e.flow == 0) continue;
            long long amount = dfs(e.to, sink, min(pushed, e.cap - e.flow));
            if (amount == 0) continue;
            e.flow += amount;
            adj[e.to][e.rev].flow -= amount;
            return amount;
        }
        return 0;
    }

public:
    long long bfs_operations = 0;
    long long dfs_operations = 0;
    long long bfs_phases = 0;

    explicit DinicOptimized(int vertices)
        : V(vertices), adj(vertices), level(vertices), ptr(vertices) {}

    void addEdge(int from, int to, long long capacity) {
        adj[from].push_back({to, capacity, 0, static_cast<int>(adj[to].size())});
        adj[to].push_back({from, 0, 0, static_cast<int>(adj[from].size()) - 1});
        adj[to].push_back({from, capacity, 0, static_cast<int>(adj[from].size())});
        adj[from].push_back({to, 0, 0, static_cast<int>(adj[to].size()) - 1});
    }

    long long maxFlow(int source, int sink) {
        long long flow = 0;
        while (bfs(source, sink)) {
            ++bfs_phases;
            fill(ptr.begin(), ptr.end(), 0);
            while (long long pushed = dfs(source, sink, LLONG_MAX)) flow += pushed;
        }
        return flow;
    }
};

int main(int argc, char* argv[]) {
    if (argc != 4) return 1;
    ifstream infile(argv[1]);
    if (!infile) return 1;
    int source = stoi(argv[2]);
    int sink = stoi(argv[3]);
    int V, E;
    infile >> V >> E;
    if (source < 0 || source >= V || sink < 0 || sink >= V || source == sink) return 1;

    DinicOptimized dinic(V);
    for (int i = 0; i < E; ++i) {
        int u, v;
        long long capacity;
        infile >> u >> v >> capacity;
        dinic.addEdge(u, v, capacity);
    }

    auto start = high_resolution_clock::now();
    long long max_flow = dinic.maxFlow(source, sink);
    auto end = high_resolution_clock::now();
    auto duration = duration_cast<microseconds>(end - start);
    cout << source << "," << sink << "," << max_flow << ","
         << dinic.bfs_operations << "," << dinic.dfs_operations << ","
         << duration.count() << "," << dinic.bfs_phases << endl;
}