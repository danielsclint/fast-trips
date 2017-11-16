import os

from fasttrips import Run


def run_example():

    EXAMPLES_DIR   = os.path.join(os.path.dirname(os.getcwd()),"fasttrips","Examples","test_scenario")

    Run.run_fasttrips(
        input_network_dir    = os.path.join(EXAMPLES_DIR,"network"),
        input_demand_dir = os.path.join(EXAMPLES_DIR,"demand_converge"),
        run_config       = os.path.join(EXAMPLES_DIR,"demand_converge","config_ft.txt"),
        input_weights    = os.path.join(EXAMPLES_DIR,"demand_converge","pathweight_ft.txt"),
        output_dir       = os.path.join(EXAMPLES_DIR,"output"),
        output_folder    = "example_converge",
        pathfinding_type = "stochastic",
        overlap_variable = "count",
        overlap_split_transit = False,
        capacity=True,
        iters            = 15,
        dispersion       = 0.50)


if __name__ == '__main__':
    run_example()
