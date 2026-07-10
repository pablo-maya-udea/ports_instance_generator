"""Worked example: generate one small instance and print its statistics.

Run from the repository root:

    python examples/quickstart.py

The output is deterministic. It should match, byte for byte, the block shown
under "Worked example" in README.md. If it does not, something in your
environment changes the random stream — please open an issue.
"""

import sys
from pathlib import Path

# Make `generator` importable when this script is run from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generator import create_instance, instance_stats  # noqa: E402


def main():
    instance = create_instance("port_layout_small.json", n_ships=5, seed=42)
    stats = instance_stats(instance)

    print("=== instance ===")
    print(f"ships          : {instance['Ships']}")
    print(f"nodes          : {len(instance['Nodes'])}")
    print(f"directed arcs  : {len(instance['Arcs'])}")
    print(f"berths (Ports) : {instance['Ports']}")
    print(f"planning periods: {instance['n_periods']}")

    print("\n=== berth assignment (ship -> berth) ===")
    for ship, berth in instance["port_ship"].items():
        print(f"  ship {ship}: berth {berth}")

    print("\n=== route of ship 1 (out-and-back) ===")
    print(f"  {instance['Routes']['1']}")

    print("\n=== ship times ===")
    print(f"{'ship':>5} {'release':>9} {'scheduled':>11} {'unload':>8}")
    for s in instance["Ships"]:
        k = str(s)
        print(f"{s:>5} {instance['t_release'][k]:>9} "
              f"{instance['t_scheduled'][k]:>11} {instance['t_unload'][k]:>8}")

    print("\n=== selected statistics ===")
    print(f"mean travel time per arc : {stats['mean_t_travel']:.4f}")
    print(f"busiest berth used by    : {stats['max_port_count']} ships")
    print(f"busiest arc traversed    : {stats['max_arc_count']} times")


if __name__ == "__main__":
    main()
