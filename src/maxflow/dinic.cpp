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
        adj[from].push_back({to, cap, 0, (int)adj[to].size()});
        adj[to].push_back({from, 0, 0, (int)adj[from].size() - 1}); // Residual for forward

        adj[to].push_back({from, cap, 0, (int)adj[from].size()});
        adj[from].push_back({to, 0, 0, (int)adj[to].size() - 1});   // Residual for backward
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
                int tr = e.to;
                if(level[v] + 1 != level[tr] || e.cap - e.flow == 0) continue;
                long long push = dfs(tr, t, min(pushed, e.cap - e.flow));
                if (push == 0) continue;
                e.flow += push;
                adj[tr][e.rev].flow -= push;
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

int main(int argc, char* argv[]) {
    if (argc != 4) {
        cerr << "Usage: " << argv[0]
             << " <graph_file> <source> <target>" << endl;
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

    Dinic dinic(V);

    for (int i = 0; i < E; ++i) {
        int u, v;
        long long cap;
        infile >> u >> v >> cap;
        dinic.addEdge(u, v, cap);
    }

    infile.close();

    auto start = high_resolution_clock::now();

    long long max_flow = dinic.maxFlow(source, sink);

    auto end = high_resolution_clock::now();

    auto duration = duration_cast<microseconds>(end - start);
    // Machine readable output
    cout << source << "," << sink << "," << max_flow << "," << dinic.bfs_operations << "," << dinic.dfs_operations << "," << duration.count() << endl;

    return 0;
}
