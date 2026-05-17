import 'package:flutter/material.dart';
import 'package:graphview/GraphView.dart';
import '../services/storage.dart';

class GoalsScreen extends StatefulWidget {
  const GoalsScreen({super.key});
  @override
  State<GoalsScreen> createState() => _GoalsScreenState();
}

class _GoalsScreenState extends State<GoalsScreen> {
  List<Map<String, dynamic>> _graphs = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final g = await Storage.listGoalGraphs();
    setState(() => _graphs = g);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Goals')),
      body: _graphs.isEmpty
          ? const Center(child: Text('No goals yet. Mention one in chat to get started.'))
          : ListView.builder(
              itemCount: _graphs.length,
              itemBuilder: (_, i) => _GraphCard(graph: _graphs[i]),
            ),
    );
  }
}

class _GraphCard extends StatelessWidget {
  final Map<String, dynamic> graph;
  const _GraphCard({required this.graph});

  @override
  Widget build(BuildContext context) {
    final g = Graph();
    final nodeMap = <String, Node>{};
    for (final n in (graph['nodes'] as List)) {
      final node = Node.Id(n['id']);
      nodeMap[n['id']] = node;
      g.addNode(node);
    }
    for (final e in (graph['edges'] as List)) {
      final from = nodeMap[e[0]];
      final to = nodeMap[e[1]];
      if (from != null && to != null) g.addEdge(from, to);
    }

    final builder = BuchheimWalkerConfiguration()
      ..siblingSeparation = 24
      ..levelSeparation = 36
      ..subtreeSeparation = 24
      ..orientation = BuchheimWalkerConfiguration.ORIENTATION_TOP_BOTTOM;

    return Card(
      margin: const EdgeInsets.all(12),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(graph['goal'] as String,
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
          Text('${graph['horizon_days']} days', style: const TextStyle(color: Colors.grey)),
          const SizedBox(height: 8),
          SizedBox(
            height: 300,
            child: InteractiveViewer(
              constrained: false,
              boundaryMargin: const EdgeInsets.all(40),
              minScale: 0.4,
              maxScale: 2.4,
              child: GraphView(
                graph: g,
                algorithm: BuchheimWalkerAlgorithm(builder, TreeEdgeRenderer(builder)),
                builder: (node) {
                  final n = (graph['nodes'] as List)
                      .firstWhere((x) => x['id'] == node.key!.value);
                  return Container(
                    padding: const EdgeInsets.all(8),
                    constraints: const BoxConstraints(maxWidth: 140),
                    decoration: BoxDecoration(
                      color: Colors.blue.shade50,
                      border: Border.all(color: Colors.blue.shade200),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(n['task'] as String,
                          style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 12)),
                      const SizedBox(height: 4),
                      Text('${n['duration_days']}d',
                          style: const TextStyle(color: Colors.grey, fontSize: 11)),
                    ]),
                  );
                },
              ),
            ),
          ),
        ]),
      ),
    );
  }
}
