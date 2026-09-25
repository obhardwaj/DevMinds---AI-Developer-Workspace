from app.engine.parser import parse_repository
from app.engine.graph_builder import build_dependency_edges
from app.modules.health_index import compute_health_index
from app.modules.dead_code import find_dead_code

graph = parse_repository(r"C:\Users\Ojass Bhardwaj\Desktop\shopsync-main")
graph = build_dependency_edges(graph)
result=compute_health_index(graph)
dead_code=find_dead_code(graph)

print(f"Nodes: {len(graph.nodes)}, Edges: {len(graph.edges)}")
for edge in graph.edges:
    print(edge.relation, edge.source_id, "->", edge.target_id)

#health index
print("Score:", result["score"])
print("Breakdown:", result["breakdown"])
print("Flagged files:", result["details"]["flagged_files"])
print("Duplicate groups:", result["details"]["duplicate_groups"])

#dead code
print("Orphaned files:", dead_code["orphaned_files"])
print("Dead private functions:", dead_code["dead_private_functions"])
print("Note:", dead_code["note"])