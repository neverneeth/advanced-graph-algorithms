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
}

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
            
        }
};