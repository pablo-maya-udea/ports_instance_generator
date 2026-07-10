# -*- coding: utf-8 -*-
"""Random instance generator for the port scheduling problem.

Generates synthetic instances from a port layout graph and writes them as JSON.

The layout file is a JSON object with two keys:

    {
      "arcs":  [[u, v], ...],   # undirected edges of the port channel network
      "ports": [p, ...]         # nodes that are berths where ships may unload
    }

Node `ENTRANCE_NODE` is the sea entrance: every ship enters the network there,
sails to its assigned berth, and sails back out along the same path.

Run as a script to emit one instance:

    python generator.py --layout port_layout_med.json --ships 20 --seed 42 \
        --out instance_med_20.json
"""

import argparse
import json
from collections import deque, Counter
from pathlib import Path
from statistics import mean, stdev

import numpy as np

# Directory searched for layout files given as a bare filename.
DATA_DIR = Path(__file__).resolve().parent / "data"

# Node at which every ship enters and leaves the port network.
ENTRANCE_NODE = 1

DEFAULT_N_SHIPS = 20
DEFAULT_T_TRAVEL_LW = 0.5
DEFAULT_T_TRAVEL_UP = 1.5
DEFAULT_T_UNLOAD_LW = 1
DEFAULT_T_UNLOAD_UP = 6
DEFAULT_T_SECURITY = 0.20
DEFAULT_N_PERIODS = 24
DEFAULT_TIME_WINDOWS = {
    "small": [0, 25],
    "medium": [3, 21],
    "large": [4, 20],
}


def resolve_layout_path(layout_path):
    """Accept either a full path or a bare filename resolved against DATA_DIR."""
    path = Path(layout_path)
    if path.is_file():
        return path
    return DATA_DIR / path.name


def load_graph(file_path):
    with open(file_path, "r") as f:
        data = json.load(f)
    return data["arcs"], data["ports"]


def build_adj_list(arcs):
    graph = {}
    for u, v in arcs:
        if u not in graph:
            graph[u] = []
        if v not in graph:
            graph[v] = []
        graph[u].append(v)
        graph[v].append(u)  # Assuming undirected graph
    return graph


def find_route(graph, start, end):
    """Return the out-and-back route from `start` to `end`.

    Finds a shortest path by breadth-first search, then appends that path
    reversed, so the returned node sequence sails to `end` and returns to
    `start`. For a shortest path [1, 4, 7] the route is [1, 4, 7, 4, 1].
    """
    queue = deque([(start, [start])])
    visited = set()

    while queue:
        node, path = queue.popleft()
        if node == end:
            # add reversed path
            path_reversed = path[::-1]
            path_reversed.pop(0)
            path.extend(path_reversed)
            return path

        if node not in visited:
            visited.add(node)
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    queue.append((neighbor, path + [neighbor]))

    return None  # No path found


def compute_travel_time(route, travel_times):
    """Sum the travel time along `route`. Raises if an arc has no travel time."""
    total_time = 0
    for i in range(len(route) - 1):
        arc = [route[i], route[i + 1]]
        arc_key = str(arc)
        if arc_key not in travel_times:
            raise KeyError(f"no travel time defined for arc {arc_key}")
        total_time += travel_times[arc_key]

    return total_time


def create_instance(layout_path,
                    n_ships=DEFAULT_N_SHIPS,
                    t_travel_lw=DEFAULT_T_TRAVEL_LW,
                    t_travel_up=DEFAULT_T_TRAVEL_UP,
                    t_unload_lw=DEFAULT_T_UNLOAD_LW,
                    t_unload_up=DEFAULT_T_UNLOAD_UP,
                    t_security=DEFAULT_T_SECURITY,
                    time_windows=None,
                    seed=42):
    """Build one random instance from the layout at `layout_path`.

    Keys of the emitted dictionaries are stringified Python literals, because
    JSON permits only string keys. An arc (u, v) is keyed "[u, v]"; a
    ship-arc pair is keyed "(s, (u, v))". Parse them back with
    `ast.literal_eval`.

    `RandomState` (not `default_rng`) is used deliberately: its stream is
    guaranteed stable across NumPy versions, so a given `seed` reproduces the
    same instance indefinitely.
    """
    if time_windows is None:
        time_windows = DEFAULT_TIME_WINDOWS

    rng = np.random.RandomState(seed)
    instance = {}

    arcs, ports = load_graph(resolve_layout_path(layout_path))
    instance['n_periods'] = DEFAULT_N_PERIODS
    instance['Ships'] = list(range(1, n_ships + 1))
    nodes = [node for arc in arcs for node in arc]
    instance['Nodes'] = list(set(nodes))
    instance['Ports'] = ports
    bi_arcs = arcs + [[j, i] for i, j in arcs]
    instance['Arcs'] = bi_arcs
    instance['port_ship'] = {str(s): int(rng.choice(ports)) for s in instance['Ships']}
    graph = build_adj_list(arcs)
    instance['Routes'] = {str(s): find_route(graph, ENTRANCE_NODE, p)
                          for s, p in instance['port_ship'].items()}

    t_travel_fw = {str(arc): round(rng.uniform(t_travel_lw, t_travel_up), 1) for arc in arcs}
    t_travel_bw = {str([arc[1], arc[0]]): t_travel_fw[str(arc)] for arc in arcs}
    instance['t_travel'] = {**t_travel_fw, **t_travel_bw}

    if isinstance(t_security, dict):
        raise NotImplementedError("per-arc security times are not supported yet; "
                                  "pass a single float for t_security")
    instance['t_security'] = {arc: t_security for arc in instance['t_travel'].keys()}

    # compute the scheduled times based on the total travel time
    total_travel = {s: compute_travel_time(instance['Routes'][str(s)], instance['t_travel'])
                    for s in instance['Ships']}
    max_travel = max(total_travel.values())
    instance['t_release'] = {str(s): round(rng.uniform(0, max_travel), 1)
                             for s in instance['Ships']}
    instance['t_scheduled'] = {
        str(s): round(rng.uniform(total_travel[s] + instance['t_release'][str(s)],
                                  2 * total_travel[s]), 1)
        for s in instance['Ships']
    }
    instance['t_unload'] = {str(s): round(rng.uniform(t_unload_lw, t_unload_up), 1)
                            for s in instance['Ships']}
    instance['tw_ini'] = {}
    instance['tw_end'] = {}

    for s in instance['Ships']:
        s_type = rng.choice(list(time_windows.keys()))
        tw_ini = time_windows[s_type][0]
        tw_end = time_windows[s_type][1]
        route = instance['Routes'][str(s)]
        for i in range(len(route) - 1):
            arc = [route[i], route[i + 1]]
            arc_key = str((s, tuple(arc)))
            instance['tw_ini'][arc_key] = tw_ini
            instance['tw_end'][arc_key] = tw_end
    return instance


def _stdev(values):
    """Sample standard deviation, defined as 0.0 for a single observation."""
    values = list(values)
    return stdev(values) if len(values) > 1 else 0.0


def instance_stats(instance):
    # numebr of times that each port is used
    stat_dict = {}
    # frecuency of each port
    port_count = dict(Counter(instance['port_ship'].values()))
    stat_dict['port_count'] = port_count
    for k, v in port_count.items():
        stat_dict[f'port{k}_count'] = v
    values = port_count.values()
    stat_dict['min_port_count'] = min(values)
    stat_dict['max_port_count'] = max(values)
    stat_dict['mean_port_count'] = mean(values)
    stat_dict['std_port_count'] = _stdev(values)
    # Frecuency of each arc
    Routes = instance['Routes']
    arcsXships_dict = {k: [(Routes[str(k)][i], Routes[str(k)][i+1]) for i in range(len(Routes[str(k)])-1)] for k in instance['Ships']}
    arcsXships_dict = [arc for k in instance['Ships'] for arc in arcsXships_dict[k] if arc[0] < arc[1]]
    stat_dict['arcsXships_dict'] = arcsXships_dict
    arc_count = dict(Counter(arcsXships_dict))
    stat_dict['arc_count'] = arc_count
    for k, v in arc_count.items():
        stat_dict[f'{k}_count'] = v
    values = arc_count.values()
    stat_dict['min_arc_count'] = min(values)
    stat_dict['max_arc_count'] = max(values)
    stat_dict['mean_arc_count'] = mean(values)
    stat_dict['std_arc_count'] = _stdev(values)
    # total travel time in arcs
    arc_travel = {arc: value*instance['t_travel'][str(list(arc))] for arc, value in arc_count.items()}
    stat_dict['arc_travel'] = arc_travel
    # travel times
    values = instance['t_travel'].values()
    stat_dict['min_t_travel'] = min(values)
    stat_dict['max_t_travel'] = max(values)
    stat_dict['mean_t_travel'] = mean(values)
    stat_dict['std_t_travel'] = _stdev(values)
    # travel release
    values = instance['t_release'].values()
    stat_dict['min_t_release'] = min(values)
    stat_dict['max_t_release'] = max(values)
    stat_dict['mean_t_release'] = mean(values)
    stat_dict['std_t_release'] = _stdev(values)
    # scheduled time
    values = instance['t_scheduled'].values()
    stat_dict['min_t_scheduled'] = min(values)
    stat_dict['max_t_scheduled'] = max(values)
    stat_dict['mean_t_scheduled'] = mean(values)
    stat_dict['std_t_scheduled'] = _stdev(values)

    # tw count
    tw_ini_count = dict(Counter(instance['tw_ini'].values()))
    stat_dict['tw_ini_count'] = tw_ini_count
    for k, v in tw_ini_count.items():
        stat_dict[f'tw_ini_{k}_count'] = v
    tw_end_count = dict(Counter(instance['tw_end'].values()))
    stat_dict['tw_end_count'] = tw_end_count
    for k, v in tw_end_count.items():
        stat_dict[f'tw_end_{k}_count'] = v

    return stat_dict


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--layout", default="port_layout.json",
                        help="layout JSON: a full path, or a filename inside ../data")
    parser.add_argument("--ships", type=int, default=DEFAULT_N_SHIPS,
                        help="number of ships to generate")
    parser.add_argument("--seed", type=int, default=42,
                        help="RNG seed; a given seed always yields the same instance")
    parser.add_argument("--t-travel-lw", type=float, default=DEFAULT_T_TRAVEL_LW)
    parser.add_argument("--t-travel-up", type=float, default=DEFAULT_T_TRAVEL_UP)
    parser.add_argument("--t-unload-lw", type=float, default=DEFAULT_T_UNLOAD_LW)
    parser.add_argument("--t-unload-up", type=float, default=DEFAULT_T_UNLOAD_UP)
    parser.add_argument("--t-security", type=float, default=DEFAULT_T_SECURITY)
    parser.add_argument("--out", default="instance.json",
                        help="path of the JSON instance to write")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    instance = create_instance(
        layout_path=args.layout,
        n_ships=args.ships,
        t_travel_lw=args.t_travel_lw,
        t_travel_up=args.t_travel_up,
        t_unload_lw=args.t_unload_lw,
        t_unload_up=args.t_unload_up,
        t_security=args.t_security,
        seed=args.seed,
    )
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as file:
        json.dump(instance, file, indent=4)
    print(f"Wrote {len(instance['Ships'])} ships to {out_path}")


if __name__ == "__main__":
    main()
