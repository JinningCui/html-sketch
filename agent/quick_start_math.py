from main import run_agent

# run a example for graph max flow. save the execution trace, answer, and usage summary under outputs/graph_maxflow
run_agent("../tasks/graph_maxflow/0", "../outputs/graph_max_flow", task_type="math", task_name="graph_maxflow")

# run a example for geometry. save the execution trace, answer, and usage summary under outputs/geometry
run_agent("../tasks/geometry/2078", "../outputs/geometry", task_type="geo")