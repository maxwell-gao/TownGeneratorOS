"""
Model class - core city generation logic
"""

import math
from .point import Point
from .polygon import Polygon
from .random import Random
from .voronoi import Voronoi
from .patch import Patch
from .curtain_wall import CurtainWall
from .topology import Topology
from .ward import (
    Ward,
    CraftsmenWard,
    MerchantWard,
    Slum,
    Market,
    Castle,
    GateWard,
    AdministrationWard,
    MilitaryWard,
    PatriciateWard,
    Park,
    Cathedral,
    Farm,
)


class Model:
    """Main model for city generation"""

    # Ward types distribution
    WARDS = [
        CraftsmenWard,
        CraftsmenWard,
        MerchantWard,
        CraftsmenWard,
        CraftsmenWard,
        Cathedral,
        CraftsmenWard,
        CraftsmenWard,
        CraftsmenWard,
        CraftsmenWard,
        CraftsmenWard,
        CraftsmenWard,
        CraftsmenWard,
        CraftsmenWard,
        AdministrationWard,
        CraftsmenWard,
        Slum,
        CraftsmenWard,
        Slum,
        PatriciateWard,
        Market,
        Slum,
        CraftsmenWard,
        CraftsmenWard,
        CraftsmenWard,
        Slum,
        CraftsmenWard,
        CraftsmenWard,
        CraftsmenWard,
        MilitaryWard,
        Slum,
        CraftsmenWard,
        Park,
        PatriciateWard,
        Market,
        MerchantWard,
    ]

    instance = None

    def __init__(self, n_patches=-1, seed=-1):
        if seed > 0:
            Random.reset(seed)
        self.n_patches = n_patches if n_patches != -1 else 15

        self.plaza_needed = Random.bool()
        self.citadel_needed = Random.bool()
        self.walls_needed = Random.bool()

        self.topology = None
        self.patches = []
        self.all_patches = []  # All original patches before filtering
        self.waterbody = []
        self.inner = []
        self.citadel = None
        self.plaza = None
        self.center = Point(0, 0)
        self.border = None
        self.wall = None
        self.city_radius = 0.0
        self.gates = []
        self.arteries = []
        self.streets = []
        self.roads = []

        # Try to build until successful (limit retries)
        max_retries = 10
        retries = 0
        while retries < max_retries:
            try:
                self._build()
                Model.instance = self
                break
            except Exception as e:
                retries += 1
                if retries >= max_retries:
                    raise RuntimeError(
                        f"Failed to build city after {max_retries} attempts: {e}"
                    )
                Random.reset()  # Reset with new seed

    def _build(self):
        """Build the city"""
        self.streets = []
        self.roads = []

        self._build_patches()
        self._optimize_junctions()
        self._build_walls()
        self._build_streets()
        self._create_wards()
        self._build_geometry()

    def _build_patches(self):
        """Build Voronoi patches"""
        sa = Random.float() * 2 * math.pi
        points = []
        for i in range(self.n_patches * 8):
            a = sa + math.sqrt(i) * 5
            r = 0 if i == 0 else 10 + i * (2 + Random.float())
            points.append(Point(math.cos(a) * r, math.sin(a) * r))

        voronoi = Voronoi.build(points)

        # Relax central wards
        for _ in range(3):
            to_relax = voronoi.points[:3] + [voronoi.points[self.n_patches]]
            voronoi = Voronoi.relax(voronoi, to_relax)

        # Sort points by distance from center
        voronoi.points.sort(key=lambda p: p.length)
        regions = voronoi.partitioning()

        self.patches = []
        self.all_patches = []  # Save all original patches
        self.inner = []

        count = 0
        for r in regions:
            patch = Patch.from_region(r)
            self.patches.append(patch)
            self.all_patches.append(patch)  # Keep all patches

            if count == 0:
                self.center = patch.shape.min(lambda p: p.length)
                if self.plaza_needed:
                    self.plaza = patch
            elif count == self.n_patches and self.citadel_needed:
                self.citadel = patch
                self.citadel.within_city = True

            if count < self.n_patches:
                patch.within_city = True
                patch.within_walls = self.walls_needed
                self.inner.append(patch)

            count += 1

    def _optimize_junctions(self):
        """Optimize patch junctions"""
        patches_to_optimize = (
            self.inner if self.citadel is None else self.inner + [self.citadel]
        )

        wards_to_clean = []
        for w in patches_to_optimize:
            index = 0
            while index < len(w.shape.vertices):
                v0 = w.shape.vertices[index]
                v1 = w.shape.vertices[(index + 1) % len(w.shape.vertices)]

                if v0 != v1 and v0.distance(v1) < 8:
                    for w1 in self.patch_by_vertex(v1):
                        if w1 != w:
                            idx = w1.shape.index_of(v1)
                            if idx != -1:
                                w1.shape.vertices[idx] = v0
                            wards_to_clean.append(w1)

                    v0.set((v0.x + v1.x) / 2, (v0.y + v1.y) / 2)
                    w.shape.vertices.remove(v1)
                else:
                    index += 1

        # Remove duplicate vertices
        for w in wards_to_clean:
            i = 0
            while i < len(w.shape.vertices):
                v = w.shape.vertices[i]
                dup_idx = (
                    w.shape.vertices.index(v, i + 1)
                    if v in w.shape.vertices[i + 1 :]
                    else -1
                )
                if dup_idx != -1:
                    w.shape.vertices.pop(dup_idx)
                else:
                    i += 1

    def _build_walls(self):
        """Build city walls"""
        reserved = self.citadel.shape.vertices.copy() if self.citadel else []

        self.border = CurtainWall(self.walls_needed, self, self.inner, reserved)
        if self.walls_needed:
            self.wall = self.border
            self.wall.build_towers()

        radius = self.border.get_radius()
        self.patches = [
            p for p in self.patches if p.shape.distance(self.center) < radius * 3
        ]

        self.gates = self.border.gates.copy()

        if self.citadel is not None:
            castle = Castle(self, self.citadel)
            castle.wall.build_towers()
            self.citadel.ward = castle

            if self.citadel.shape.compactness < 0.75:
                raise ValueError("Bad citadel shape!")

            self.gates.extend(castle.wall.gates)

    def _build_streets(self):
        """Build streets and roads"""

        def smooth_street(street):
            smoothed = street.smooth_vertex_eq(3)
            for i in range(1, len(street.vertices) - 1):
                street.vertices[i].set(smoothed.vertices[i])

        self.topology = Topology(self)

        for gate in self.gates:
            end = (
                self.plaza.shape.min(lambda v: v.distance(gate))
                if self.plaza
                else self.center
            )

            street = self.topology.build_path(gate, end, self.topology.outer)
            if street is None:
                raise ValueError("Unable to build a street!")

            self.streets.append(Polygon(street))

            if gate in self.border.gates:
                dir_pt = gate.norm(1000)
                start = None
                dist = float("inf")
                for p in self.topology.node2pt.values():
                    d = p.distance(dir_pt)
                    if d < dist:
                        dist = d
                        start = p

                if start:
                    road = self.topology.build_path(start, gate, self.topology.inner)
                    if road:
                        self.roads.append(Polygon(road))

        self._tidy_up_roads()

        for a in self.arteries:
            smooth_street(a)

    def _tidy_up_roads(self):
        """Tidy up roads and create arteries"""
        segments = []

        def cut_to_segments(street):
            if len(street.vertices) < 2:
                return
            v0 = street.vertices[0]
            for i in range(1, len(street.vertices)):
                v1 = street.vertices[i]

                # Remove segments along plaza
                if self.plaza and (
                    self.plaza.shape.contains(v0) and self.plaza.shape.contains(v1)
                ):
                    v0 = v1
                    continue

                # Check if segment already exists
                exists = False
                for seg in segments:
                    if seg[0] == v0 and seg[1] == v1:
                        exists = True
                        break

                if not exists:
                    segments.append((v0, v1))
                v0 = v1

        for street in self.streets:
            cut_to_segments(street)
        for road in self.roads:
            cut_to_segments(road)

        # Build arteries from segments
        self.arteries = []
        while len(segments) > 0:
            seg = segments.pop()

            attached = False
            for a in self.arteries:
                if a.vertices[0] == seg[1]:
                    a.vertices.insert(0, seg[0])
                    attached = True
                    break
                elif a.vertices[-1] == seg[0]:
                    a.vertices.append(seg[1])
                    attached = True
                    break

            if not attached:
                self.arteries.append(Polygon([seg[0], seg[1]]))

    def _create_wards(self):
        """Create wards"""
        unassigned = self.inner.copy()

        if self.plaza:
            from .ward import Market

            self.plaza.ward = Market(self, self.plaza)
            unassigned.remove(self.plaza)

        # Assign gate wards
        for gate in self.border.gates:
            for patch in self.patch_by_vertex(gate):
                if patch.within_city and patch.ward is None:
                    chance = 0.2 if self.wall is None else 0.5
                    if Random.bool(chance):
                        from .ward import GateWard

                        patch.ward = GateWard(self, patch)
                        if patch in unassigned:
                            unassigned.remove(patch)

        # Assign other wards
        wards = list(self.WARDS)
        # Some shuffling
        for _ in range(len(wards) // 10):
            index = Random.int(0, len(wards) - 1)
            if index < len(wards) - 1:
                wards[index], wards[index + 1] = wards[index + 1], wards[index]

        while len(unassigned) > 0:
            best_patch = None

            ward_class = wards.pop(0) if len(wards) > 0 else Slum
            rate_func = getattr(ward_class, "rate_location", None)

            if rate_func is None:
                best_patch = unassigned[Random.int(0, len(unassigned))]
            else:
                best_patch = min(
                    unassigned,
                    key=lambda p: float("inf") if p.ward else rate_func(self, p),
                )

            best_patch.ward = ward_class(self, best_patch)
            unassigned.remove(best_patch)

        # Outskirts
        if self.wall:
            for gate in self.wall.gates:
                if not Random.bool(1.0 / (self.n_patches - 5)):
                    for patch in self.patch_by_vertex(gate):
                        if patch.ward is None:
                            patch.within_city = True
                            from .ward import GateWard

                            patch.ward = GateWard(self, patch)

        # Calculate radius and process countryside
        self.city_radius = 0
        for patch in self.patches:
            if patch.within_city:
                for v in patch.shape.vertices:
                    self.city_radius = max(self.city_radius, v.length)
            elif patch.ward is None:
                if Random.bool(0.2) and patch.shape.compactness >= 0.7:
                    patch.ward = Farm(self, patch)
                else:
                    patch.ward = Ward(self, patch)

    def _build_geometry(self):
        """Build geometry for all patches"""
        for patch in self.patches:
            if patch.ward:
                patch.ward.create_geometry()

    def find_circumference(self, wards):
        """Find circumference polygon of wards"""
        if len(wards) == 0:
            return Polygon()
        elif len(wards) == 1:
            return Polygon(wards[0].shape.vertices)

        A = []
        B = []

        for w1 in wards:
            w1.shape.for_edge(
                lambda a, b: self._process_circumference_edge(a, b, w1, wards, A, B)
            )

        if len(A) == 0:
            return Polygon()

        # Build a map from point to list of indices where it appears as A
        point_to_indices = {}
        for i, point in enumerate(A):
            if point not in point_to_indices:
                point_to_indices[point] = []
            point_to_indices[point].append(i)

        # Find the longest cycle starting from each unvisited edge
        result = Polygon()
        visited_edges = set()

        for start_idx in range(len(A)):
            if start_idx in visited_edges:
                continue

            cycle = []
            current_idx = start_idx
            cycle_visited = set()

            while current_idx not in cycle_visited and current_idx not in visited_edges:
                cycle_visited.add(current_idx)
                visited_edges.add(current_idx)
                cycle.append(A[current_idx])

                # Find next edge: B[current_idx] should be A[next_idx]
                next_point = B[current_idx]
                if next_point in point_to_indices:
                    # Find an unvisited index that matches
                    found = False
                    for next_idx in point_to_indices[next_point]:
                        if next_idx not in visited_edges:
                            current_idx = next_idx
                            found = True
                            break
                    if not found:
                        # Try any matching index
                        if point_to_indices[next_point]:
                            current_idx = point_to_indices[next_point][0]
                            if current_idx in visited_edges:
                                break
                        else:
                            break
                else:
                    break

                # Check if we've completed a cycle
                if current_idx == start_idx or A[current_idx] == A[start_idx]:
                    break

            # Keep the longest cycle
            if len(cycle) > len(result.vertices):
                result = Polygon(cycle)

        return result

    def _process_circumference_edge(self, a, b, w1, wards, A, B):
        """Process edge for circumference"""
        outer_edge = True
        for w2 in wards:
            if w2 != w1 and w2.shape.find_edge(b, a) != -1:
                outer_edge = False
                break
        if outer_edge:
            A.append(a)
            B.append(b)

    def patch_by_vertex(self, v):
        """Get patches containing vertex"""
        return [p for p in self.patches if p.shape.contains(v)]

    def get_neighbour(self, patch, v):
        """Get neighbouring patch at vertex"""
        next_v = patch.shape.next(v)
        if next_v is None:
            return None
        for p in self.patches:
            if p != patch and p.shape.find_edge(next_v, v) != -1:
                return p
        return None

    def get_neighbours(self, patch):
        """Get all neighbouring patches"""
        return [p for p in self.patches if p != patch and p.shape.borders(patch.shape)]

    def is_enclosed(self, patch):
        """Check if patch is enclosed"""
        if not patch.within_city:
            return False
        if patch.within_walls:
            return True
        return all(p.within_city for p in self.get_neighbours(patch))

    def to_dict(self):
        """Convert to dictionary for JSON export"""
        return {
            "n_patches": self.n_patches,
            "seed": Random.get_seed(),
            "plaza_needed": self.plaza_needed,
            "citadel_needed": self.citadel_needed,
            "walls_needed": self.walls_needed,
            "center": self.center.to_dict(),
            "city_radius": self.city_radius,
            "gates": [g.to_dict() for g in self.gates],
            "patches": [p.to_dict() for p in self.patches],
            "streets": [s.to_dict() for s in self.streets],
            "roads": [r.to_dict() for r in self.roads],
            "arteries": [a.to_dict() for a in self.arteries],
            "wall": {
                "shape": self.wall.shape.to_dict() if self.wall else None,
                "gates": [g.to_dict() for g in (self.wall.gates if self.wall else [])],
                "towers": [
                    t.to_dict() for t in (self.wall.towers if self.wall else [])
                ],
            }
            if self.wall
            else None,
            "citadel": {
                "shape": self.citadel.shape.to_dict() if self.citadel else None,
                "wall": {
                    "shape": self.citadel.ward.wall.shape.to_dict()
                    if (
                        self.citadel
                        and self.citadel.ward
                        and hasattr(self.citadel.ward, "wall")
                    )
                    else None,
                    "gates": [
                        g.to_dict()
                        for g in (
                            self.citadel.ward.wall.gates
                            if (
                                self.citadel
                                and self.citadel.ward
                                and hasattr(self.citadel.ward, "wall")
                            )
                            else []
                        )
                    ],
                    "towers": [
                        t.to_dict()
                        for t in (
                            self.citadel.ward.wall.towers
                            if (
                                self.citadel
                                and self.citadel.ward
                                and hasattr(self.citadel.ward, "wall")
                            )
                            else []
                        )
                    ],
                }
                if (
                    self.citadel
                    and self.citadel.ward
                    and hasattr(self.citadel.ward, "wall")
                )
                else None,
            }
            if self.citadel
            else None,
            "plaza": self.plaza.shape.to_dict() if self.plaza else None,
        }
