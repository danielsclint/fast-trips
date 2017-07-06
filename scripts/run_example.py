import os

from fasttrips import Run

# note: this MUST be in __main__ or the run will error when trying to fork subprocesses
if __name__ == "__main__":

    EXAMPLES_DIR   = os.path.join(os.getcwd(),"fasttrips","Examples","test_scenario")

    Run.run_fasttrips(
        input_network_dir     = os.path.join(EXAMPLES_DIR,"network"),
        input_demand_dir      = os.path.join(EXAMPLES_DIR,"demand_reg"),
        run_config            = os.path.join(EXAMPLES_DIR,"demand_reg","config_ft.txt"),
        input_weights         = os.path.join(EXAMPLES_DIR,"demand_reg","pathweight_ft.txt"),
        output_dir            = os.path.join(EXAMPLES_DIR,"output"),
        output_folder         = "example",
        pathfinding_type      = "stochastic",
        overlap_variable      = "count",
        overlap_split_transit = True,
        iters                 = 1,
        dispersion            = 0.50)
