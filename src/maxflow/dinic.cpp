#include <iostream>
#include <vector>
#include <queue>
#include <fstream>
#include <chrono>

using namespace std;
using namespace std::chrono;

struct Edge {
    long long cap;
    long long flow;
    int to;
    int rev;
};

class Dinic {
    private:
        int V; // Number of vertices
        vector<vector<Edge>> adj; // Adjacency list representation of the graph
        vector<int> level; // For Level graph representation
        vector<int> ptr; // For DFS optimization
    public:
        long long bfs_operations = 0;
        long long dfs_operations = 0;
        Dinic(int V) : V(V), adj(V), level(V), ptr(V) {}
        
        void addEdge(int from, int to, long long cap) {
            Edge a = {cap, 0, to, (int)adj[to].size()};
            Edge b = {0, 0, from, (int)adj[from].size()};
            adj[from].push_back(a);
            adj[to].push_back(b);
        }

        bool bfs(int s, int t)
        {
            fill(level.begin(), level.end(), -1);
            level[s] = 0;
            queue<int> q;
            q.push(s);
            while (!q.empty()) {
                int v = q.front();
                q.pop();
                for (const Edge &e : adj[v]) {
                    bfs_operations++;
                    if (level[e.to] < 0 && e.flow < e.cap) {
                        level[e.to] = level[v] + 1;
                        q.push(e.to);
                    }
                }
            }
            return level[t] >= 0;
        }

        long long dfs(int v, int t, long long pushed)
        {
            if(pushed == 0 || v == t) return pushed;
            for(int &cid = ptr[v]; cid < (int)adj[v].size(); ++cid) {
                dfs_operations++;
                Edge &e = adj[v][cid]; 
                int tr = edge.to;
                if(level[v] + 1 != level[tr] || edge.cap - edge.flow == 0) continue;
                long long push = dfs(tr, t, min(pushed, edge.cap - edge.flow));
                if (push == 0) continue;
                edge.flow += push;
                adj[tr][edge.rev].flow -= push;
                return push;
            }
            return 0;
        }
        long long maxFlow(int s, int t) {
            long long flow = 0;
            while (bfs(s, t)) {
                fill(ptr.begin(), ptr.end(), 0);
                while (long long pushed = dfs(s, t, LLONG_MAX)) {
                    flow += pushed;
                }
            }
            return flow;
        }
};

int main() {
    ifstream infile("caida_bandwidth_graph.txt");
    if (!infile) {
        cerr << "Error opening graph file." << endl;
        return 1;
    }
    int V, E;
    infile >> V >> E;
    Dinic dinic(V);
    for (int i = 0; i < E; ++i) {
        int u, v;
        long long cap;
        infile >> u >> v >> cap;
        dinic.addEdge(u, v, cap);
    }
    infile.close();
    int source = 0; // Assuming source is vertex 0
    int sink = V - 1; // Assuming sink is the last vertex
    auto start = high_resolution_clock::now();
    long long max_flow = dinic.maxFlow(source, sink);
    auto end = high_resolution_clock::now();
    auto duration = duration_cast<milliseconds>(end - start);
    cout << "Maximum Flow: " << max_flow << endl;
    cout << "BFS Operations: " << dinic.bfs_operations << endl;
    cout << "DFS Operations: " << dinic.dfs_operations << endl;
    cout << "Time taken: " << duration.count() << " milliseconds" << endl;
    return 0;
}