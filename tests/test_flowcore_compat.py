from flowcore.cli.main import main as legacy_main
from lee.cli.main import main as current_main


def test_legacy_flowcore_entrypoint_maps_to_lee_main():
    assert legacy_main is current_main

