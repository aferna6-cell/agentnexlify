#!/usr/bin/env bash
# Merge graphify semantic results + AST, build graph, generate outputs.
# Run this AFTER all 8 semantic agents have written .graphify_result_N.json files.
set -euo pipefail
cd /home/aidan/agentnexlify

PYTHON=$(cat .graphify_python)

# Step 1: Merge semantic chunks
$PYTHON -c "
import json
from pathlib import Path

sem_nodes, sem_edges, sem_hyperedges = [], [], []
valid, invalid = 0, 0

for i in range(8):
    f = Path(f'.graphify_result_{i}.json')
    if f.exists():
        try:
            d = json.loads(f.read_text())
            if 'nodes' in d and 'edges' in d:
                # Fix invalid file_types
                for n in d['nodes']:
                    if n.get('file_type') not in {'code','document','image','paper'}:
                        n['file_type'] = 'document'
                # Filter edges missing source/target
                good_edges = [e for e in d['edges'] if 'source' in e and 'target' in e]
                sem_nodes.extend(d['nodes'])
                sem_edges.extend(good_edges)
                sem_hyperedges.extend(d.get('hyperedges', []))
                valid += 1
                print(f'Chunk {i}: {len(d[\"nodes\"])}n {len(good_edges)}e (dropped {len(d[\"edges\"])-len(good_edges)} bad edges)')
            else:
                invalid += 1
                print(f'Chunk {i}: missing nodes/edges, skip')
        except Exception as e:
            invalid += 1
            print(f'Chunk {i}: parse error ({e}), skip')
    else:
        print(f'Chunk {i}: file not found')

seen = set()
deduped = [n for n in sem_nodes if n.get('id') and n['id'] not in seen and not seen.add(n['id'])]
Path('.graphify_semantic.json').write_text(json.dumps({'nodes':deduped,'edges':sem_edges,'hyperedges':sem_hyperedges,'input_tokens':0,'output_tokens':0}, indent=2))
print(f'Semantic total: {len(deduped)} nodes, {len(sem_edges)} edges from {valid}/{valid+invalid} chunks')
"

# Step 2: Merge AST + semantic
$PYTHON -c "
import json
from pathlib import Path

ast = json.loads(Path('.graphify_ast.json').read_text())
sem = json.loads(Path('.graphify_semantic.json').read_text())

seen = {n['id'] for n in ast['nodes']}
merged_nodes = list(ast['nodes'])
for n in sem['nodes']:
    if n['id'] not in seen:
        merged_nodes.append(n)
        seen.add(n['id'])

merged = {
    'nodes': merged_nodes,
    'edges': ast['edges'] + sem['edges'],
    'hyperedges': sem.get('hyperedges', []),
    'input_tokens': 0, 'output_tokens': 0,
}
Path('.graphify_extract.json').write_text(json.dumps(merged, indent=2))
print(f'Merged: {len(merged_nodes)} nodes, {len(merged[\"edges\"])} edges ({len(ast[\"nodes\"])} AST + {len(sem[\"nodes\"])} semantic)')
"

# Step 3: Build graph + cluster
mkdir -p graphify-out
$PYTHON -c "
import json
from graphify.build import build_from_json
from graphify.cluster import cluster, score_all
from graphify.analyze import god_nodes, surprising_connections, suggest_questions
from graphify.report import generate
from graphify.export import to_json
from pathlib import Path

extraction = json.loads(Path('.graphify_extract.json').read_text())
detection  = json.loads(Path('.graphify_detect.json').read_text())

G = build_from_json(extraction)
communities = cluster(G)
cohesion = score_all(G, communities)
tokens = {'input': 0, 'output': 0}
gods = god_nodes(G)
surprises = surprising_connections(G, communities)
labels = {cid: 'Community ' + str(cid) for cid in communities}
questions = suggest_questions(G, communities, labels)

report = generate(G, communities, cohesion, labels, gods, surprises, detection, tokens, '.', suggested_questions=questions)
Path('graphify-out/GRAPH_REPORT.md').write_text(report)
to_json(G, communities, 'graphify-out/graph.json')

analysis = {
    'communities': {str(k): v for k, v in communities.items()},
    'cohesion': {str(k): v for k, v in cohesion.items()},
    'gods': gods,
    'surprises': surprises,
    'questions': questions,
}
Path('.graphify_analysis.json').write_text(json.dumps(analysis, indent=2))
print(f'Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges, {len(communities)} communities')
" 2>&1

echo "Build complete. Run labeling + viz next."
