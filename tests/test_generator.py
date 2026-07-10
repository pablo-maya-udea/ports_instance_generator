"""Smoke tests for the instance generator.

The hash tests are the important ones. They assert that a fixed seed produces
a byte-for-byte fixed instance. If a NumPy upgrade ever silently changes the
random stream, these fail loudly instead of quietly invalidating published
results.

Run from the repository root:

    pytest
"""

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generator import (  # noqa: E402
    ENTRANCE_NODE,
    compute_travel_time,
    create_instance,
    instance_stats,
)

# sha256 of json.dumps(instance, sort_keys=True), generated with numpy 2.5.1.
# RandomState guarantees a stable stream, so these must hold on any NumPy.
REFERENCE_HASHES = {
    ("port_layout_small.json", 5, 42):
        "8eef19d40895a889161019e9425d0f20894fc47625fed635547a419913f3fe4a",
    ("port_layout_med.json", 20, 42):
        "acb6eea4804d0c09915ad73648463bb0aeab68a54b239a6bb08323f0e4f78530",
    ("port_layout.json", 25, 14):
        "86fb3e9d0c0c79f93a82c95aeb853f874b6c9d76c3458ce411d5c876786c2fbc",
}


def instance_hash(instance):
    return hashlib.sha256(json.dumps(instance, sort_keys=True).encode()).hexdigest()


@pytest.mark.parametrize("key,expected", sorted(REFERENCE_HASHES.items()))
def test_fixed_seed_gives_fixed_instance(key, expected):
    layout, ships, seed = key
    instance = create_instance(layout, n_ships=ships, seed=seed)
    assert instance_hash(instance) == expected, (
        f"instance for {layout} (ships={ships}, seed={seed}) changed; "
        f"published results generated with this seed are no longer reproducible"
    )


def test_same_seed_is_deterministic():
    a = create_instance("port_layout_small.json", n_ships=7, seed=3)
    b = create_instance("port_layout_small.json", n_ships=7, seed=3)
    assert a == b


def test_different_seeds_differ():
    a = create_instance("port_layout_small.json", n_ships=7, seed=3)
    b = create_instance("port_layout_small.json", n_ships=7, seed=4)
    assert a != b


def test_no_global_rng_leak():
    """create_instance must not disturb the global NumPy random state."""
    np = pytest.importorskip("numpy")
    np.random.seed(1234)
    before = np.random.rand()
    np.random.seed(1234)
    create_instance("port_layout_small.json", n_ships=5, seed=99)
    after = np.random.rand()
    assert before == after


def test_routes_start_and_end_at_entrance():
    instance = create_instance("port_layout_med.json", n_ships=10, seed=1)
    for ship, route in instance["Routes"].items():
        assert route[0] == ENTRANCE_NODE
        assert route[-1] == ENTRANCE_NODE
        berth = instance["port_ship"][ship]
        assert berth in route


def test_route_travel_times_are_defined():
    instance = create_instance("port_layout_med.json", n_ships=10, seed=1)
    for route in instance["Routes"].values():
        assert compute_travel_time(route, instance["t_travel"]) > 0


def test_release_times_within_bounds():
    """t_release must lie in [0, max_travel] -- regression test for the
    `np.random.uniform(max_travel)` bug, which floored releases at 1.0."""
    instance = create_instance("port_layout.json", n_ships=30, seed=7)
    total = {s: compute_travel_time(instance["Routes"][str(s)], instance["t_travel"])
             for s in instance["Ships"]}
    max_travel = max(total.values())
    for value in instance["t_release"].values():
        assert 0.0 <= value <= max_travel


def test_single_ship_stats_do_not_crash():
    """stdev() is undefined for one observation; instance_stats must cope."""
    instance = create_instance("port_layout_small.json", n_ships=1, seed=5)
    stats = instance_stats(instance)
    assert stats["std_port_count"] == 0.0
    assert stats["std_t_release"] == 0.0


def test_dict_security_time_is_rejected():
    with pytest.raises(NotImplementedError):
        create_instance("port_layout_small.json", n_ships=5, t_security={"a": 1})


def test_missing_arc_raises():
    with pytest.raises(KeyError):
        compute_travel_time([1, 999], {})


def test_instance_is_json_serialisable():
    instance = create_instance("port_layout_small.json", n_ships=5, seed=42)
    json.dumps(instance)
