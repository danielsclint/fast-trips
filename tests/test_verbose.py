import os

from fasttrips import Run


def test_verbose_network():
    """
    Test to ensure that a network with all optional fields stated, does not break
    the application.
    """

    EXAMPLES_DIR = os.path.join(os.getcwd(), "fasttrips", "Examples")

    INPUT_NETWORK = os.path.join(EXAMPLES_DIR, "networks", 'verbose')
    INPUT_DEMAND = os.path.join(EXAMPLES_DIR, "demand", "flexpress")
    OUTPUT_DIR = os.path.join(EXAMPLES_DIR, "output")

    r = Run.run_fasttrips(
        input_network_dir=INPUT_NETWORK,
        input_demand_dir=INPUT_DEMAND,
        run_config=os.path.join(INPUT_DEMAND, "config_ft.txt"),
        input_weights=os.path.join(INPUT_DEMAND, "pathweight_ft.txt"),
        output_dir=OUTPUT_DIR,
        output_folder="verbose",
        pathfinding_type="stochastic",
        capacity=True,
        iters=1,
        OVERLAP = "None",
        dispersion=1.0
    )

    assert 1646 == r['paths_found']
