# ports_instance_generator

Reproducible random instance generator for the port scheduling problem, released as
the computational annex of Restricted two-way channel access flow optimization in 
multi-port terminals under tidal conditions.

Ships arrive at a port, sail through a channel network from a single sea entrance to
an assigned berth, unload, and sail back out. This tool generates synthetic instances
of that problem — network, berth assignments, routes, travel/release/unloading times,
and per-arc time windows — from a port layout graph and a random seed.

Every instance is fully determined by its layout file and its seed. Given both, anyone
can regenerate a bit-identical instance on any machine and any NumPy version.

---

## Installation

Requires Python ≥ 3.9. Tested on Python 3.13.13.

```bash
git clone https://github.com/<YOUR GITHUB USER>/ports_instance_generator.git
cd ports_instance_generator
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

The generator itself needs only `numpy`. `pytest` is used for the test suite.

---

## Quick start

Generate one instance with 20 ships on the medium layout:

```bash
python generator.py --layout port_layout_med.json --ships 20 --seed 42 --out instance_med_20.json
```

A bare filename is resolved against the bundled `data/` directory; a full path is used
as given. Run `python generator.py --help` for all options.

Or from Python:

```python
from generator import create_instance, instance_stats

instance = create_instance("port_layout_med.json", n_ships=20, seed=42)
stats = instance_stats(instance)
```

Importing the module has no side effects.

---

## Worked example

```bash
python examples/quickstart.py
```

This generates a 5-ship instance on the small layout with seed 42 and prints:

```
=== instance ===
ships          : [1, 2, 3, 4, 5]
nodes          : 10
directed arcs  : 18
berths (Ports) : [24, 25, 26]
planning periods: 24

=== berth assignment (ship -> berth) ===
  ship 1: berth 26
  ship 2: berth 24
  ship 3: berth 26
  ship 4: berth 26
  ship 5: berth 24

=== route of ship 1 (out-and-back) ===
  [1, 2, 3, 4, 5, 26, 5, 4, 3, 2, 1]

=== ship times ===
 ship   release   scheduled   unload
    1      11.6        21.2      5.9
    2       0.0        12.7      2.2
    3      12.3        20.5      1.5
    4       7.7        18.1      4.1
    5       7.6        20.2      2.9

=== selected statistics ===
mean travel time per arc : 0.8889
busiest berth used by    : 3 ships
busiest arc traversed    : 5 times
```

If your output differs, your environment is perturbing the random stream. Please open
an issue — reproducibility is the point of this repository.

---

## Input: the port layout file

A layout is a JSON object with exactly two keys. Here is `data/port_layout_small.json`
in full:

```json
{
    "arcs": [[1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7],
             [5, 26], [6, 25], [7, 24]],
    "ports": [24, 25, 26]
}
```

| Key | Type | Meaning |
|---|---|---|
| `arcs` | list of `[u, v]` | **Undirected** edges of the channel network. Each edge is listed once; the generator adds the reverse direction itself. |
| `ports` | list of node ids | Nodes that are berths, where a ship may dock and unload. |

Two conventions are load-bearing and are **not** stated inside the file:

1. **Node `1` is the sea entrance.** Every ship enters and leaves the network there.
   It is the constant `ENTRANCE_NODE` in [`generator.py`](generator.py). A custom layout
   must use node id `1` for its entrance, or the constant must be changed.
2. **The graph must be connected**, and every node in `ports` must be reachable from
   node `1`. Otherwise route construction fails.

Node ids need not be contiguous — in the layouts above, channel nodes are `1..7` while
berths are numbered from `24` up.

Three layouts are bundled:

| File | Undirected arcs | Berths | Used in the paper as |
|---|---|---|---|
| `data/port_layout_small.json` | 9 | 3 | S |
| `data/port_layout_med.json` | 25 | 11 | M |
| `data/port_layout.json` | 40 | 18 | L |

---

## Output: the instance file

`create_instance` returns a dictionary, written as JSON by the CLI. Let $S$ be the set
of ships, $N$ the nodes, $A$ the directed arcs, and $P \subseteq N$ the berths. All
times are in hours, rounded to one decimal.

### Sets

| Field | Type | Meaning |
|---|---|---|
| `n_periods` | int | Number of periods $T$ in the planning horizon. Fixed at 24. |
| `Ships` | list[int] | Ship ids $S = \{1, \dots, n\}$. |
| `Nodes` | list[int] | All nodes $N$ appearing in the layout. |
| `Ports` | list[int] | Berth nodes $P$, copied from the layout. |
| `Arcs` | list[[int,int]] | Directed arcs $A$: each undirected layout edge in both directions, so $\lvert A\rvert = 2\lvert\text{arcs}\rvert$. |

### Structure

| Field | Type | Meaning |
|---|---|---|
| `port_ship` | `{s: p}` | Berth $p \in P$ assigned to ship $s$, drawn uniformly at random from `Ports`. |
| `Routes` | `{s: [n₀, n₁, …]}` | The **out-and-back tour** of ship $s$: a shortest path (by hop count) from the entrance to its berth, followed by the same path reversed. Starts and ends at node `1`. For instance `[1, 2, 3, 4, 5, 26, 5, 4, 3, 2, 1]`. |

### Parameters

| Field | Type | Meaning | Distribution |
|---|---|---|---|
| `t_travel` | `{arc: float}` | Time to traverse arc $(u,v)$. Symmetric: $t_{uv} = t_{vu}$. | $\mathcal{U}(0.5,\ 1.5)$ per undirected edge |
| `t_security` | `{arc: float}` | Minimum safety headway on arc $(u,v)$ between consecutive ships. | constant $0.20$ |
| `t_release` | `{s: float}` | Earliest time ship $s$ may enter the port. | $\mathcal{U}(0,\ \max_{s'} T_{s'})$ |
| `t_scheduled` | `{s: float}` | Contractually scheduled arrival time of ship $s$; lateness is measured against it. | $\mathcal{U}(T_s + r_s,\ 2T_s)$ — **see Known limitations** |
| `t_unload` | `{s: float}` | Time ship $s$ spends unloading at its berth. | $\mathcal{U}(1,\ 6)$ |
| `tw_ini` | `{(s,(u,v)): float}` | Start of the time window in which ship $s$ may traverse arc $(u,v)$. | by ship class, below |
| `tw_end` | `{(s,(u,v)): float}` | End of that time window. | by ship class, below |

Here $T_s$ = `compute_travel_time(Routes[s], t_travel)` is the total travel time of
ship $s$'s complete out-and-back tour, and $r_s$ = `t_release[s]`.

Each ship is independently assigned one of three classes, uniformly at random, which
fixes the time window applied to *every* arc on its route:

| Class | `tw_ini` | `tw_end` |
|---|---|---|
| `small` | 0 | 25 |
| `medium` | 3 | 21 |
| `large` | 4 | 20 |

### Key encoding

JSON permits only string keys, so composite keys are stored as **stringified Python
literals**:

| Field | Key format | Example |
|---|---|---|
| `Ships`-indexed (`t_release`, `t_scheduled`, `t_unload`, `port_ship`, `Routes`) | `"s"` | `"3"` |
| `t_travel`, `t_security` | `"[u, v]"` | `"[5, 26]"` |
| `tw_ini`, `tw_end` | `"(s, (u, v))"` | `"(3, (5, 26))"` |

Parse them back with `ast.literal_eval`:

```python
import ast, json

instance = json.load(open("instance_med_20.json"))
travel = {ast.literal_eval(k): v for k, v in instance["t_travel"].items()}
windows = {ast.literal_eval(k): v for k, v in instance["tw_ini"].items()}
```

---

## Reproducing the instances used in the paper

Instances are identified by the triple **(layout, number of ships, seed)**. Nothing
else varies: all other parameters keep the defaults in `create_instance`.

> **TODO — confirm before publishing.** The sweep below is transcribed from the
> experiment scripts and covers sizes S/M/L, ship counts 10–50, and seeds 1–3. Replace
> it with the exact grid reported in the paper, and state which table or figure each
> block feeds.

```bash
for seed in 1 2 3; do
  for ships in 10 15 20 25 30 35 40 45 50; do
    python generator.py --layout port_layout_small.json --ships $ships --seed $seed \
        --out instances/S_${ships}_${seed}.json
    python generator.py --layout port_layout_med.json   --ships $ships --seed $seed \
        --out instances/M_${ships}_${seed}.json
    python generator.py --layout port_layout.json       --ships $ships --seed $seed \
        --out instances/L_${ships}_${seed}.json
  done
done
```

### Why the instances are stable

The generator uses NumPy's legacy `RandomState`, not the newer `default_rng`.
`RandomState`'s bit stream is guaranteed never to change, by NumPy's own backwards
compatibility policy ([NEP 19](https://numpy.org/neps/nep-0019-rng-policy.html)). A
seed therefore names the same instance forever, across NumPy versions and platforms.

`RandomState` is instantiated locally rather than seeded globally, so generating an
instance does not disturb the ambient `numpy.random` state of any calling program.
`tests/test_generator.py::test_no_global_rng_leak` asserts this.

---

## Tests

```bash
pytest
```

Thirteen tests. The important ones pin the SHA-256 of three reference instances: if a
future NumPy silently alters the random stream, the suite fails loudly instead of
quietly invalidating published results.

```
sha256(port_layout_small.json,  5 ships, seed 42) = 8eef19d4…3fe4a
sha256(port_layout_med.json,   20 ships, seed 42) = acb6eea4…78530
sha256(port_layout.json,       25 ships, seed 14) = 86fb3e9d…c2fbc
```

---

## Known limitations

**`t_scheduled` is drawn from an inverted interval for a substantial fraction of
ships.** It is sampled from $\mathcal{U}(T_s + r_s,\ 2T_s)$. Whenever a ship's release
time $r_s$ exceeds its own tour time $T_s$, the lower bound exceeds the upper bound.
NumPy does not raise on this; it silently samples from the reversed interval.

Because $r_s$ is drawn against $\max_{s'} T_{s'}$ — the *global* maximum tour time —
any ship with a shorter-than-maximal route is prone to it. Measured over 1250
ship-draws on the large layout (25 ships × 50 seeds):

- the interval is inverted for **40%** of ships;
- **40%** receive a `t_scheduled` earlier than $r_s + T_s$, i.e. earlier than the
  soonest they could physically complete their tour.

If `t_scheduled` is intended to be an attainable target arrival, the upper bound
$2T_s$ is too small; something of the form $\mathcal{U}(r_s + T_s,\ r_s + 2T_s)$ would
preserve the apparent intent. This has been left as-is rather than changed
unilaterally, because it alters the meaning of the model.

**`n_periods` is fixed at 24** while the `small` ship class carries a time window
ending at 25, one hour beyond the horizon.

**Per-arc security times are unimplemented.** Passing a `dict` for `t_security` raises
`NotImplementedError`; only a single scalar applied to every arc is supported.

---

## Repository layout

```
ports_instance_generator/
├── generator.py              # the generator: library + CLI
├── data/                     # port layout graphs
│   ├── port_layout_small.json
│   ├── port_layout_med.json
│   └── port_layout.json
├── examples/quickstart.py    # worked example, deterministic output
├── tests/test_generator.py   # smoke tests + fixed-seed instance hashes
├── requirements.txt
├── CITATION.cff
├── LICENSE
└── README.md
```

---

## Citing

Please cite the paper, and the archived software snapshot rather than this repository's
URL — a GitHub repository can be deleted or rewritten, a Zenodo record cannot.

> **TODO.** Archive a tagged release on [Zenodo](https://zenodo.org) (enable the repo
> under *Zenodo → GitHub*, then publish a release), uncomment the `doi:` field in
> `CITATION.cff`, and paste the DOI badge here.

Once `CITATION.cff` is filled in, GitHub renders a *Cite this repository* button in the
sidebar.

---

## License

MIT — see [LICENSE](LICENSE).
