# Town Generator - Generation Process

This document describes the step-by-step generation process for medieval fantasy cities.

## Overview

The generation process consists of 6 main stages executed in sequence:

```
┌─────────────────┐
│  build_patches  │  Step 1: Create Voronoi patches
└────────┬────────┘
         │
┌────────▼────────┐
│optimize_junctions│ Step 2: Merge close vertices
└────────┬────────┘
         │
┌────────▼────────┐
│   build_walls   │  Step 3: Create city walls & gates
└────────┬────────┘
         │
┌────────▼────────┐
│  build_streets  │  Step 4: Create street network
└────────┬────────┘
         │
┌────────▼────────┐
│  create_wards   │  Step 5: Assign ward types
└────────┬────────┘
         │
┌────────▼────────┐
│ build_geometry  │  Step 6: Generate buildings
└────────┴────────┘
```

## Step 1: Build Patches (`_build_patches`)

### Purpose
Generate the city layout using Voronoi tessellation.

### Algorithm
1. **Generate spiral points**: Create `n_patches * 8` points in a spiral pattern
   ```python
   for i in range(n_patches * 8):
       a = sa + sqrt(i) * 5           # angle (spiral)
       r = 0 if i == 0 else 10 + i * (2 + random())  # radius
       points.append(Point(cos(a) * r, sin(a) * r))
   ```

2. **Build Voronoi diagram**: Use Delaunay triangulation to create Voronoi regions

3. **Relax central wards**: Apply Lloyd's relaxation 3 times to first 3 points + citadel point
   ```python
   for _ in range(3):
       to_relax = voronoi.points[:3] + [voronoi.points[n_patches]]
       voronoi = Voronoi.relax(voronoi, to_relax)
   ```

4. **Sort points by distance**: Order patches by distance from center

5. **Create patches**: Convert Voronoi regions to Patch objects
   - First patch (center) may become plaza
   - Patch at index `n_patches` may become citadel
   - First `n_patches` patches are "inner" city patches

### Key Data Structures
- `patches`: All patches in the city
- `inner`: Patches within the city (first `n_patches`)
- `plaza`: Central patch (if `plaza_needed`)
- `citadel`: Castle patch (if `citadel_needed`)
- `center`: City center point

### Visualization Points
- Voronoi diagram with points
- Patch boundaries
- Center point
- Plaza and citadel highlights

---

## Step 2: Optimize Junctions (`_optimize_junctions`)

### Purpose
Clean up patch geometry by merging vertices that are too close together.

### Algorithm
1. For each patch in `inner` (+ citadel if exists):
   - Iterate through consecutive vertex pairs
   - If distance < 8 units: merge vertices
     - Set both to midpoint
     - Update all patches sharing the vertex
   
2. Remove duplicate vertices from affected patches

### Why This Matters
- Prevents tiny edges that cause rendering issues
- Creates cleaner intersections for streets
- Reduces polygon complexity

### Visualization Points
- Before/after vertex positions
- Highlight merged vertices
- Show affected patches

---

## Step 3: Build Walls (`_build_walls`)

### Purpose
Create city fortifications and establish gates.

### Algorithm
1. **Find circumference**: Compute outer boundary of all inner patches
   ```python
   # For each edge: if no neighbor shares it (reversed), it's an outer edge
   for edge in patch.edges:
       if no_neighbor_shares(edge.reverse):
           outer_edges.append(edge)
   ```

2. **Smooth walls**: Apply smoothing to wall shape (except reserved citadel vertices)

3. **Build gates**: Select entrances where multiple wards meet
   - Split outer patches at gates for road access
   - Remove neighboring entrances to ensure minimum spacing

4. **Filter patches**: Remove patches too far from center (> 3x wall radius)

5. **Build citadel**: If citadel exists, create Castle ward with its own wall

### Key Data Structures
- `border`: CurtainWall object (always created)
- `wall`: CurtainWall object (only if `walls_needed`)
- `gates`: All city entrances (wall gates + citadel gates)

### Visualization Points
- Wall polygon
- Gate positions
- Tower positions
- Citadel outline

---

## Step 4: Build Streets (`_build_streets`)

### Purpose
Create road network connecting gates to city center.

### Algorithm
1. **Build topology graph**:
   - Create graph nodes for patch vertices
   - Block nodes on walls/citadel (except gates)
   - Link adjacent nodes with distance weights
   - Classify nodes as `inner` (city) or `outer` (outside)

2. **For each gate**:
   - Find path from gate to plaza center (or city center)
   - Use A* pathfinding on topology graph
   - Exclude outer nodes for inner streets
   
3. **For wall gates** (not citadel):
   - Find point farthest in gate direction
   - Build road from that point to gate
   - Exclude inner nodes for roads

4. **Tidy up roads**:
   - Remove duplicate segments
   - Remove segments along plaza
   - Merge segments into arteries

5. **Smooth streets**: Apply vertex smoothing to all arteries

### Key Data Structures
- `topology`: Topology object with graph
- `streets`: Streets inside walls
- `roads`: Roads outside walls
- `arteries`: Combined unique segments

### Visualization Points
- Topology graph nodes and edges
- Individual street paths
- Road paths
- Artery network

---

## Step 5: Create Wards (`_create_wards`)

### Purpose
Assign ward types to each patch.

### Algorithm
1. **Assign plaza**: If exists, set to Market

2. **Assign gate wards**: For patches touching gates
   - 50% chance if walls exist, 20% otherwise

3. **Assign inner wards**:
   - Use WARDS array (weighted distribution)
   - Shuffle slightly for variety
   - For each unassigned patch:
     - If ward has `rate_location`: pick best rated patch
     - Else: pick random unassigned patch
   - Create ward instance

4. **Assign outskirts**: For patches outside walls near gates
   - Random chance based on city size

5. **Assign countryside**: For remaining patches
   - 20% chance of Farm (if compact enough)
   - Otherwise: empty Ward

6. **Calculate city radius**: Farthest vertex from center

### Ward Type Distribution
```
WARDS = [
    CraftsmenWard, CraftsmenWard, MerchantWard,  # Early wards
    CraftsmenWard, CraftsmenWard, Cathedral,
    CraftsmenWard × 8,
    AdministrationWard, CraftsmenWard,
    Slum, CraftsmenWard, Slum, PatriciateWard, Market,
    Slum, CraftsmenWard × 3, Slum,
    CraftsmenWard × 3, MilitaryWard, Slum,
    CraftsmenWard, Park, PatriciateWard, Market, MerchantWard
]
```

### Ward Rating Functions
- **Slum**: Prefers far from center (negative distance)
- **Market**: Must not touch another market, size similar to plaza
- Most wards: Random selection

### Visualization Points
- Ward type colors
- Ward boundaries
- Rate scores for placement decisions

---

## Step 6: Build Geometry (`_build_geometry`)

### Purpose
Generate building footprints within each ward.

### Algorithm
For each patch, call `ward.create_geometry()`:

1. **Get city block**: Inset patch shape based on streets
   - Main street: 2.0 units
   - Regular street: 1.0 units
   - Alley: 0.6 units

2. **Create buildings** (varies by ward type):

   **CommonWard (Craftsmen, Slum, Merchant, etc.)**:
   ```python
   create_alleys(block, min_sq, grid_chaos, size_chaos, empty_prob):
       # Find longest edge
       # Bisect at random ratio with angle perturbation
       # Recursively divide until min_sq reached
       # Random chance to leave empty
   ```

   **Market**:
   - Create statue (rect) or fountain (circle)
   - Position at offset toward longest edge

   **Castle**:
   - Shrink shape significantly
   - Create orthogonal buildings

   **Park**:
   - Create grove areas

   **Cathedral**:
   - Single large building

   **Farm**:
   - No buildings

3. **Filter outskirts**: For non-enclosed patches
   - Remove buildings far from roads/city

### Building Parameters by Ward Type
| Ward Type | min_sq | grid_chaos | size_chaos |
|-----------|--------|------------|------------|
| Craftsmen | 10-90 | 0.5-0.7 | 0.6 |
| Slum | 10-40 | 0.6-1.0 | 0.8 |
| Merchant | 20-120 | 0.3-0.5 | 0.5 |
| Patriciate | 40-190 | 0.2-0.4 | 0.3 |

### Visualization Points
- City block outlines
- Building footprints
- Building subdivision process

---

## Comparison: Haxe vs Python Implementation

### File Mapping

| Haxe Source | Python Module |
|-------------|---------------|
| `building/Model.hx` | `model.py` |
| `building/Patch.hx` | `patch.py` |
| `building/CurtainWall.hx` | `curtain_wall.py` |
| `building/Topology.hx` | `topology.py` |
| `building/Cutter.hx` | `cutter.py` |
| `geom/Voronoi.hx` | `voronoi.py` |
| `geom/Polygon.hx` | `polygon.py` |
| `geom/Graph.hx` | `graph.py` |
| `wards/*.hx` | `ward.py` |
| `utils/Random.hx` | `random.py` |
| `utils/MathUtils.hx` | `math_utils.py` |

### Key Differences to Watch
1. **Array indexing**: Haxe uses `array[i]`, Python uses `.vertices[i]`
2. **Random behavior**: Must match exactly for reproducible results
3. **Polygon operations**: Buffer, shrink, cut need careful implementation
4. **Reference equality**: Haxe uses `==` for object identity, Python needs explicit checks

---

## Debugging Workflow

Use the `StepVisualizer` class to debug each step:

```python
from town_generator.step_visualizer import StepVisualizer

# Create model with debugging
vis = StepVisualizer(n_patches=15, seed=12345)

# Visualize each step
vis.visualize_step(1)  # Voronoi patches
vis.visualize_step(2)  # Junction optimization
vis.visualize_step(3)  # Walls and gates
vis.visualize_step(4)  # Streets and roads
vis.visualize_step(5)  # Ward assignment
vis.visualize_step(6)  # Building geometry

# Or visualize all steps
vis.visualize_all()
```

Each step outputs an SVG file showing the current state.

