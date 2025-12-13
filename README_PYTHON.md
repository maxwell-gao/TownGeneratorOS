# Medieval Fantasy City Generator - Python Port

This is a Python port of the Medieval Fantasy City Generator, originally written in Haxe. This version only includes the core generation logic and JSON export functionality - all visualization code has been removed.

## Features

- Procedural city generation using Voronoi diagrams
- Multiple ward types (Craftsmen, Merchant, Slum, Market, Castle, etc.)
- City walls and gates
- Street and road networks
- JSON export of generated cities

## Installation

No external dependencies required - uses only Python standard library.

## Usage

### Command Line

```bash
python main.py [options]
```

Options:
- `-s, --size`: City size (6=Small Town, 10=Large Town, 15=Small City, 24=Large City, 40=Metropolis). Default: 15
- `--seed`: Random seed (-1 for random). Default: -1
- `-o, --output`: Output JSON file (default: print to stdout)
- `--indent`: JSON indentation. Default: 2

Examples:

```bash
# Generate a small city and print JSON
python main.py -s 15

# Generate a large city with specific seed and save to file
python main.py -s 24 --seed 12345 -o city.json

# Generate a metropolis
python main.py -s 40 -o metropolis.json
```

### Python API

```python
from town_generator.model import Model
from town_generator.export import export_to_json

# Generate a city
model = Model(n_patches=15, seed=-1)

# Export to JSON
export_to_json(model, 'city.json')

# Or get JSON string
json_str = export_to_json(model)
```

## JSON Format

The exported JSON contains:

- `n_patches`: Number of patches
- `seed`: Random seed used
- `center`: City center point
- `city_radius`: City radius
- `gates`: List of gate positions
- `patches`: List of all patches with:
  - `shape`: Polygon vertices
  - `within_city`: Whether patch is in city
  - `within_walls`: Whether patch is within walls
  - `ward_type`: Type of ward (e.g., "Craftsmen", "Market")
  - `ward_geometry`: Building geometries
- `streets`: Street polygons
- `roads`: Road polygons
- `arteries`: Combined street/road network
- `wall`: City wall information (if walls exist)
- `citadel`: Citadel information (if citadel exists)
- `plaza`: Plaza polygon (if plaza exists)

## City Sizes

- 6: Small Town
- 10: Large Town
- 15: Small City
- 24: Large City
- 40: Metropolis

## Ward Types

- **CraftsmenWard**: Craftsmen districts
- **MerchantWard**: Merchant districts
- **Slum**: Slum districts
- **Market**: Market squares
- **Castle**: Castle/citadel
- **GateWard**: Gate districts
- **AdministrationWard**: Administrative districts
- **MilitaryWard**: Military districts
- **PatriciateWard**: Patrician districts
- **Park**: Parks
- **Cathedral**: Cathedrals
- **Farm**: Farmland

## Notes

- The generator may retry if initial generation fails
- Some geometric operations are simplified compared to the original
- The generator uses a deterministic random number generator with seed support

## License

See LICENSE file for original license.
