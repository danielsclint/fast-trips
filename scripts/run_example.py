import os

from fasttrips import Run

EXAMPLES_DIR   = os.path.join(os.path.dirname(os.getcwd()),"fasttrips","Examples","test_scenario")

def run_example():
    Run.run_fasttrips(
        input_network_dir    = os.path.join(EXAMPLES_DIR,"network"),
        input_demand_dir = os.path.join(EXAMPLES_DIR,"demand_reg"),
        run_config       = os.path.join(EXAMPLES_DIR,"demand_reg","config_ft.txt"),
        input_weights    = os.path.join(EXAMPLES_DIR,"demand_reg","pathweight_ft.txt"),
        output_dir       = os.path.join(EXAMPLES_DIR,"output"),
        output_folder    = "example",
        capacity=True,
        pathfinding_type = "stochastic",
        overlap_variable = "count",
        overlap_split_transit = True,
        iters            = 4,
        dispersion       = 0.50)

if __name__ == '__main__':
    run_example()

    