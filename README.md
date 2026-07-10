# ports_instance_generator

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21298924.svg)](https://doi.org/10.5281/zenodo.21298924)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-blue?logo=github)](https://github.com/pablo-maya-udea/ports_instance_generator)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Reproducible random instance generator for the port scheduling problem, developed to support the computational experiments reported in **Restricted two-way channel access flow optimization in multi-port terminals under tidal conditions**.

Ships arrive at a port, sail through a channel network from a single sea entrance to an assigned berth, unload, and sail back out. This tool generates synthetic instances of that problem—including the channel network, berth assignments, routes, travel times, release times, scheduled times, unloading times, security times, and per-arc time windows—from a port layout graph and a random seed.

Every instance is fully determined by its layout file and its seed. Given both, anyone can regenerate a bit-identical instance on any machine and any NumPy version.

---

## Installation

Requires Python ≥ 3.9. Tested on Python 3.13.

```bash
git clone https://github.com/pablo-maya-udea/ports_instance_generator.git
cd ports_instance_generator
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

The generator itself requires only `numpy`. `pytest` is used for the test suite.

---

## Quick start

Generate one instance with 20 ships on the medium layout:

```bash
python generator.py --layout port_layout_med.json --ships 20 --seed 42 --out instance_med_20.json
```

A bare filename is resolved against the bundled `data/` directory; a full path is used as given.

Run

```bash
python generator.py --help
```

for all available options.

From Python:

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

This generates a deterministic 5-ship instance on the small layout using seed 42.

If your output differs, your environment is perturbing the random stream. Please open an issue—reproducibility is the main objective of this repository.

---

## Input: the port layout file

A layout is a JSON object containing two keys:

```json
{
  "arcs": [[1,2],[2,3],[3,4],[4,5],[5,6],[6,7],[5,26],[6,25],[7,24]],
  "ports": [24,25,26]
}
```

| Key | Type | Meaning |
|------|------|---------|
| `arcs` | list of `[u,v]` | Undirected channel segments. The reverse direction is generated automatically. |
| `ports` | list | Berth node identifiers. |

Two assumptions must hold:

- Node **1** is always the sea entrance.
- Every berth must be reachable from node 1.

Three layouts are included:

| Layout | Arcs | Berths | Paper notation |
|--------|----:|-------:|----------------|
| Small | 9 | 3 | S |
| Medium | 25 | 11 | M |
| Large | 40 | 18 | L |

---

## Output

The generator produces a JSON instance containing:

- Sets
- Network structure
- Ship routes
- Travel parameters
- Time windows
- Release times
- Scheduled times
- Unloading times
- Security times

Composite keys are encoded as strings to comply with the JSON standard.

---

## Reproducing the paper instances

Instances are uniquely identified by the triple

```
(layout, number of ships, random seed)
```

All remaining parameters keep their default values.

The following script reproduces the experimental instances:

```bash
for seed in 1 2 3; do
  for ships in 10 15 20 25 30 35 40 45 50; do
    python generator.py --layout port_layout_small.json --ships $ships --seed $seed \
        --out instances/S_${ships}_${seed}.json
    python generator.py --layout port_layout_med.json --ships $ships --seed $seed \
        --out instances/M_${ships}_${seed}.json
    python generator.py --layout port_layout.json --ships $ships --seed $seed \
        --out instances/L_${ships}_${seed}.json
  done
done
```

---

## Reproducibility

The generator uses NumPy's legacy `RandomState`, whose bit stream is guaranteed to remain stable across NumPy releases.

Consequently, the same

- layout,
- number of ships, and
- random seed

always generate exactly the same instance.

---

## Tests

Run

```bash
pytest
```

The test suite verifies reproducibility, validates generated instances, and checks reference SHA-256 hashes for selected benchmark instances.

---

## Repository structure

```
ports_instance_generator/
├── generator.py
├── data/
│   ├── port_layout_small.json
│   ├── port_layout_med.json
│   └── port_layout.json
├── examples/
│   └── quickstart.py
├── tests/
│   └── test_generator.py
├── requirements.txt
├── CITATION.cff
├── LICENSE
└── README.md
```

---

# Citation

If you use this software in academic work, please cite both the software and the accompanying paper.

### Software

> Maya-Duque, P. (2026). *ports_instance_generator: Random instance generator for the port scheduling problem* (Version 1.0.2). Zenodo. https://doi.org/10.5281/zenodo.21298924

A BibTeX citation can be downloaded directly from the Zenodo record.

### Accompanying paper

> Maya-Duque, P. *Restricted two-way channel access flow optimization in multi-port terminals under tidal conditions*. Maritime Business Review, 2026.

GitHub also provides a **Cite this repository** button based on the `CITATION.cff` metadata.

---

# License

This project is distributed under the **MIT License**. See the [LICENSE](LICENSE) file for details.
