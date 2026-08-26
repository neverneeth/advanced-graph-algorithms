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

class PushRelabel {
private:
    int V;
    vector<vector<Edge>> adj;
    vector<long long> excess;
    vector<int> height;
    vector<int> count; 
    queue<int> active;
    vector<bool> in_queue;

    void enqueue(int v) {
        if (!in_queue[v] && excess[v] > 0) {
            active.push(v);
            in_queue[v] = true;
        }
    }

    void push(int u, Edge& e) {
        push_operations++;
        long long d = min(excess[u], e.cap - e.flow);
        e.flow += d;
        adj[e.to][e.rev].flow -= d;
        excess[u] -= d;
        excess[e.to] += d;
    }

    void relabel(int u) {
        relabel_operations++;
        int min_height = 2 * V;
        for (const Edge& e : adj[u]) {
            if (e.cap - e.flow > 0) {
                min_height = min(min_height, height[e.to]);
            }
        }

        if (--count[height[u]] == 0 && height[u] < V) {
            for (int i = 0; i < V; ++i) {
                if (height[i] > height[u] && height[i] < V) {
                    --count[height[i]];
                    height[i] = V + 1;
                    ++count[height[i]];
                }
            }
        }
        
        height[u] = min_height + 1;
        ++count[height[u]];
    }

    void discharge(int u, int source, int sink) {
        while (excess[u] > 0) {
            bool pushed = false;
            for (Edge& e : adj[u]) {
                if (e.cap - e.flow > 0 && height[u] == height[e.to] + 1) {
                    push(u, e);
                    if (e.to != source && e.to != sink) {
                        enqueue(e.to);
                    }
                    if (excess[u] == 0) {
                        pushed = true;
                        break;
                    }
                }
            }
            if (!pushed) {
                relabel(u);
            }
        }
    }

public:
    long long push_operations = 0;
    long long relabel_operations = 0;

    PushRelabel(int V) : V(V), adj(V), excess(V, 0), height(V, 0), count(2 * V + 1, 0), in_queue(V, false) {}

    void addEdge(int from, int to, long long cap) {
        Edge a = {cap, 0, to, (int)adj[to].size()};
        Edge b = {0, 0, from, (int)adj[from].size()};
        adj[from].push_back(a);
        adj[to].push_back(b);
    }

    long long maxFlow(int source, int sink) {
        height[source] = V;
        count[0] = V - 1;
        count[V] = 1;

        for (Edge& e : adj[source]) {
            if (e.cap > 0) {
                excess[source] += e.cap;
                push(source, e);
                if (e.to != sink) {
                    enqueue(e.to);
                }
            }
        }

        while (!active.empty()) {
            int u = active.front();
            active.pop();
            in_queue[u] = false;
            discharge(u, source, sink);
        }

        return excess[sink];
    }
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

    PushRelabel pr(V);

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
    
    cout << source << "," << sink << "," << max_flow << "," << pr.push_operations << "," << pr.relabel_operations << "," << duration.count() << endl;

    return 0;
}