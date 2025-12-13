"""
Ward classes representing different city districts
"""

import math
from .polygon import Polygon
from .point import Point
from .random import Random
from .math_utils import distance2line, interpolate as geom_interpolate
from .cutter import Cutter


class Ward:
    """Base ward class"""

    MAIN_STREET = 2.0
    REGULAR_STREET = 1.0
    ALLEY = 0.6

    def __init__(self, model, patch):
        self.model = model
        self.patch = patch
        self.geometry = []

    def create_geometry(self):
        """Create geometry for this ward (override in subclasses)"""
        self.geometry = []

    def get_label(self):
        """Get label for this ward"""
        return None

    @staticmethod
    def rate_location(model, patch):
        """Rate location suitability (override in subclasses)"""
        return 0.0

    def get_city_block(self):
        """Get city block polygon"""
        inset_dist = []

        inner_patch = self.model.wall is None or self.patch.within_walls
        self.patch.shape.for_edge(
            lambda v0, v1: self._process_edge(v0, v1, inner_patch, inset_dist)
        )

        if self.patch.shape.is_convex():
            return self.patch.shape.shrink(inset_dist)
        else:
            return self.patch.shape.buffer(inset_dist)

    def _process_edge(self, v0, v1, inner_patch, inset_dist):
        """Process edge for city block calculation"""
        if self.model.wall is not None and self.model.wall.borders_by(
            self.patch, v0, v1
        ):
            inset_dist.append(self.MAIN_STREET / 2)
        else:
            on_street = inner_patch and (
                self.model.plaza is not None
                and self.model.plaza.shape.find_edge(v1, v0) != -1
            )
            if not on_street:
                for street in self.model.arteries:
                    if street.contains(v0) and street.contains(v1):
                        on_street = True
                        break
            inset_dist.append(
                (
                    self.MAIN_STREET
                    if on_street
                    else (self.REGULAR_STREET if inner_patch else self.ALLEY)
                )
                / 2
            )

    def filter_outskirts(self):
        """Filter buildings in outskirts"""
        populated_edges = []

        def add_edge(v1, v2, factor=1.0):
            dx = v2.x - v1.x
            dy = v2.y - v1.y
            distances = {}
            d = self.patch.shape.max(
                lambda v: distances.setdefault(
                    v,
                    (
                        0
                        if (v == v1 or v == v2)
                        else distance2line(v1.x, v1.y, dx, dy, v.x, v.y)
                    )
                    * factor,
                )
            )
            populated_edges.append(
                {
                    "x": v1.x,
                    "y": v1.y,
                    "dx": dx,
                    "dy": dy,
                    "d": distances.get(d, 0) if d else 0,
                }
            )

        self.patch.shape.for_edge(
            lambda v1, v2: self._process_outskirts_edge(v1, v2, add_edge)
        )

        # Density calculation
        density = []
        for v in self.patch.shape.vertices:
            if v in self.model.gates:
                density.append(1)
            else:
                all_city = all(p.within_city for p in self.model.patch_by_vertex(v))
                density.append(2 * Random.float() if all_city else 0)

        # Filter buildings
        self.geometry = [
            b
            for b in self.geometry
            if self._should_keep_building(b, populated_edges, density)
        ]

    def _process_outskirts_edge(self, v1, v2, add_edge):
        """Process edge for outskirts filtering"""
        on_road = False
        for street in self.model.arteries:
            if street.contains(v1) and street.contains(v2):
                on_road = True
                break

        if on_road:
            add_edge(v1, v2, 1)
        else:
            n = self.model.get_neighbour(self.patch, v1)
            if n is not None:
                if n.within_city:
                    enclosed = self.model.is_enclosed(n)
                    add_edge(v1, v2, 1 if enclosed else 0.4)

    def _should_keep_building(self, building, populated_edges, density):
        """Determine if building should be kept"""
        min_dist = 1.0
        for edge in populated_edges:
            for v in building.vertices:
                d = distance2line(
                    edge["x"], edge["y"], edge["dx"], edge["dy"], v.x, v.y
                )
                dist = d / edge["d"] if edge["d"] > 0 else float("inf")
                if dist < min_dist:
                    min_dist = dist

        c = building.center
        i = self.patch.shape.interpolate(c)
        p = sum(density[j] * i[j] for j in range(len(i)))
        min_dist /= p if p > 0 else 1

        return Random.fuzzy(1) > min_dist

    @staticmethod
    def create_alleys(
        poly, min_sq, grid_chaos, size_chaos, empty_prob=0.04, split=True, depth=0
    ):
        """Create alleys by recursively bisecting polygon"""
        # Limit recursion depth
        if depth > 20:
            return [poly] if poly.square >= min_sq else []

        from .cutter import Cutter

        # Find longest edge
        v = None
        length = -1.0

        def find_edge(p0, p1):
            nonlocal v, length
            len_val = p0.distance(p1)
            if len_val > length:
                length = len_val
                v = p0

        poly.for_edge(find_edge)

        if v is None or len(poly.vertices) < 3:
            return [poly] if poly.square >= min_sq else []

        spread = 0.8 * grid_chaos
        ratio = (1 - spread) / 2 + Random.float() * spread

        # Match Haxe: angleSpread = Math.PI / 6 * gridChaos * (p.square < minSq * 4 ? 0.0 : 1)
        angle_spread = (
            math.pi / 6 * grid_chaos * (0.0 if poly.square < min_sq * 4 else 1.0)
        )
        b = (Random.float() - 0.5) * angle_spread

        try:
            halves = Cutter.bisect(poly, v, ratio, b, split if split else 0.0)
        except:
            return [poly] if poly.square >= min_sq else []

        buildings = []
        for half in halves:
            if len(half.vertices) < 3:
                continue
            if half.square < min_sq * math.pow(
                2, 4 * size_chaos * (Random.float() - 0.5)
            ):
                if not Random.bool(empty_prob):
                    buildings.append(half)
            else:
                # Match Haxe: half.square > minSq / (Random.float() * Random.float())
                should_split = half.square > min_sq / (Random.float() * Random.float())
                buildings.extend(
                    Ward.create_alleys(
                        half,
                        min_sq,
                        grid_chaos,
                        size_chaos,
                        empty_prob,
                        should_split,
                        depth + 1,
                    )
                )

        return buildings if buildings else ([poly] if poly.square >= min_sq else [])

    @staticmethod
    def create_ortho_building(poly, min_block_sq, fill):
        """Create orthogonal buildings"""

        def slice(poly, c1, c2, depth=0):
            # Prevent runaway recursion
            if depth > 50:
                return []
            v0 = Ward._find_longest_edge_vertex(poly)
            v1 = poly.next(v0)
            v = v1 - v0

            ratio = 0.4 + Random.float() * 0.2
            p1 = geom_interpolate(v0, v1, ratio)

            from .math_utils import scalar

            # Match Haxe: choose c based on scalar comparison
            c = (
                c1
                if abs(scalar(v.x, v.y, c1.x, c1.y)) < abs(scalar(v.x, v.y, c2.x, c2.y))
                else c2
            )

            # Match Haxe: p1.add(c) - add point to point
            halves = poly.cut(p1, p1 + c)
            buildings = []
            for half in halves:
                if half.square < min_block_sq * math.pow(2, Random.normal() * 2 - 1):
                    if Random.bool(fill):
                        buildings.append(half)
                else:
                    buildings.extend(slice(half, c1, c2, depth + 1))
            return buildings

        if poly.square < min_block_sq:
            return [poly]
        else:
            v0 = Ward._find_longest_edge_vertex(poly)
            c1 = poly.vector(v0)
            c2 = c1.rotate90()
            # Match Haxe: while(true) loop until blocks.length > 0
            for _ in range(100):  # limit retries to avoid infinite loop
                blocks = slice(poly, c1, c2, 0)
                if len(blocks) > 0:
                    return blocks
            # Fallback: return original polygon if no blocks generated
            return [poly]

    @staticmethod
    def _find_longest_edge_vertex(poly):
        """Find vertex with longest edge"""
        return poly.min(lambda v: -poly.vector(v).length)


class CommonWard(Ward):
    """Common ward with buildings"""

    def __init__(self, model, patch, min_sq, grid_chaos, size_chaos, empty_prob=0.04):
        super().__init__(model, patch)
        self.min_sq = min_sq
        self.grid_chaos = grid_chaos
        self.size_chaos = size_chaos
        self.empty_prob = empty_prob

    def create_geometry(self):
        block = self.get_city_block()
        self.geometry = Ward.create_alleys(
            block, self.min_sq, self.grid_chaos, self.size_chaos, self.empty_prob
        )

        if not self.model.is_enclosed(self.patch):
            self.filter_outskirts()


class CraftsmenWard(CommonWard):
    """Craftsmen ward"""

    def __init__(self, model, patch):
        min_sq = 10 + 80 * Random.float() * Random.float()
        grid_chaos = 0.5 + Random.float() * 0.2
        size_chaos = 0.6
        super().__init__(model, patch, min_sq, grid_chaos, size_chaos)

    def get_label(self):
        return "Craftsmen"


class Slum(CommonWard):
    """Slum ward"""

    def __init__(self, model, patch):
        min_sq = 10 + 30 * Random.float() * Random.float()
        grid_chaos = 0.6 + Random.float() * 0.4
        size_chaos = 0.8
        super().__init__(model, patch, min_sq, grid_chaos, size_chaos, 0.03)

    @staticmethod
    def rate_location(model, patch):
        center = model.plaza.shape.center if model.plaza else model.center
        return -patch.shape.distance(center)

    def get_label(self):
        return "Slum"


class Market(Ward):
    """Market ward"""

    def create_geometry(self):
        statue = Random.bool(0.6)
        offset = statue or Random.bool(0.3)

        v0 = None
        v1 = None
        if statue or offset:
            self._market_length = -1.0
            self._market_v0 = None
            self._market_v1 = None
            self.patch.shape.for_edge(self._find_longest_edge_for_market)
            v0 = self._market_v0
            v1 = self._market_v1

        if statue:
            obj = Polygon.rect(1 + Random.float(), 1 + Random.float())
            if v0 and v1:
                angle = math.atan2(v1.y - v0.y, v1.x - v0.x)
                obj.rotate(angle)
        else:
            obj = Polygon.circle(1 + Random.float())

        if offset and v0 and v1:
            gravity = geom_interpolate(v0, v1, 0.5)
            centroid = self.patch.shape.centroid
            offset_pt = geom_interpolate(centroid, gravity, 0.2 + Random.float() * 0.4)
            obj.offset(offset_pt)
        else:
            obj.offset(self.patch.shape.centroid)

        self.geometry = [obj]

    def _find_longest_edge_for_market(self, p0, p1):
        """Helper for market - finds longest edge"""
        # This is called via for_edge, so we track in instance variables
        if not hasattr(self, "_market_length"):
            self._market_length = -1.0
            self._market_v0 = None
            self._market_v1 = None

        len_val = p0.distance(p1)
        if len_val > self._market_length:
            self._market_length = len_val
            self._market_v0 = p0
            self._market_v1 = p1

    @staticmethod
    def rate_location(model, patch):
        # One market should not touch another
        for p in model.inner:
            if isinstance(p.ward, Market) and p.shape.borders(patch.shape):
                return float("inf")

        # Market shouldn't be much larger than the plaza
        if model.plaza is not None:
            return patch.shape.square / model.plaza.shape.square
        else:
            return patch.shape.distance(model.center)

    def get_label(self):
        return "Market"


class Castle(Ward):
    """Castle ward"""

    def __init__(self, model, patch):
        super().__init__(model, patch)
        from .curtain_wall import CurtainWall

        reserved = [
            v
            for v in patch.shape.vertices
            if any(not p.within_city for p in model.patch_by_vertex(v))
        ]
        self.wall = CurtainWall(True, model, [patch], reserved)

    def create_geometry(self):
        block = self.patch.shape.shrink_eq(self.MAIN_STREET * 2)
        self.geometry = Ward.create_ortho_building(
            block, math.sqrt(block.square) * 4, 0.6
        )

    def get_label(self):
        return "Castle"


# Add more ward types as needed
class MerchantWard(CommonWard):
    """Merchant ward"""

    def __init__(self, model, patch):
        # Match Haxe: 50 + 60 * Random.float() * Random.float()
        min_sq = 50 + 60 * Random.float() * Random.float()
        # Match Haxe: 0.5 + Random.float() * 0.3
        grid_chaos = 0.5 + Random.float() * 0.3
        # Match Haxe: 0.7
        size_chaos = 0.7
        # Match Haxe: emptyProb = 0.15
        super().__init__(model, patch, min_sq, grid_chaos, size_chaos, 0.15)

    @staticmethod
    def rate_location(model, patch):
        """Rate location suitability for merchant ward"""
        # Merchant ward should be as close to the center as possible
        center = model.plaza.shape.center if model.plaza else model.center
        return patch.shape.distance(center)

    def get_label(self):
        return "Merchant"


class GateWard(CommonWard):
    """Gate ward"""

    def __init__(self, model, patch):
        # Match Haxe: 10 + 50 * Random.float() * Random.float()
        min_sq = 10 + 50 * Random.float() * Random.float()
        # Match Haxe: 0.5 + Random.float() * 0.3
        grid_chaos = 0.5 + Random.float() * 0.3
        # Match Haxe: 0.7
        size_chaos = 0.7
        super().__init__(model, patch, min_sq, grid_chaos, size_chaos)

    def get_label(self):
        return "Gate"


class AdministrationWard(CommonWard):
    """Administration ward"""

    def __init__(self, model, patch):
        # Match Haxe: 80 + 30 * Random.float() * Random.float()
        min_sq = 80 + 30 * Random.float() * Random.float()
        # Match Haxe: 0.1 + Random.float() * 0.3
        grid_chaos = 0.1 + Random.float() * 0.3
        # Match Haxe: 0.3
        size_chaos = 0.3
        super().__init__(model, patch, min_sq, grid_chaos, size_chaos)

    @staticmethod
    def rate_location(model, patch):
        """Rate location suitability for administration ward"""
        # Ideally administration ward should overlook the plaza,
        # otherwise it should be as close to the plaza as possible
        if model.plaza is not None:
            if patch.shape.borders(model.plaza.shape):
                return 0
            else:
                return patch.shape.distance(model.plaza.shape.center)
        else:
            return patch.shape.distance(model.center)

    def get_label(self):
        return "Administration"


class MilitaryWard(Ward):
    """Military ward - should border citadel or city walls"""

    def create_geometry(self):
        """Create geometry for military ward"""
        import math

        block = self.get_city_block()
        self.geometry = Ward.create_alleys(
            block,
            math.sqrt(block.square) * (1 + Random.float()),
            0.1 + Random.float() * 0.3,  # gridChaos: regular
            0.3,  # sizeChaos
            0.25,  # emptyProb: squares
        )

    @staticmethod
    def rate_location(model, patch):
        """Rate location suitability for military ward"""
        # Military ward should border the citadel or the city walls
        if model.citadel is not None and model.citadel.shape.borders(patch.shape):
            return 0
        elif model.wall is not None and model.wall.borders(patch):
            return 1
        else:
            # If no citadel and no wall, return 0; otherwise infinity
            return 0 if (model.citadel is None and model.wall is None) else float("inf")

    def get_label(self):
        return "Military"


class PatriciateWard(CommonWard):
    """Patriciate ward"""

    def __init__(self, model, patch):
        # Match Haxe: 80 + 30 * Random.float() * Random.float()
        min_sq = 80 + 30 * Random.float() * Random.float()
        # Match Haxe: 0.5 + Random.float() * 0.3
        grid_chaos = 0.5 + Random.float() * 0.3
        # Match Haxe: 0.8
        size_chaos = 0.8
        # Match Haxe: emptyProb = 0.2
        super().__init__(model, patch, min_sq, grid_chaos, size_chaos, 0.2)

    @staticmethod
    def rate_location(model, patch):
        """Rate location suitability for patriciate ward"""
        # Patriciate ward prefers to border a park and not to border slums
        rate = 0
        for p in model.patches:
            if p.ward is not None and p.shape.borders(patch.shape):
                from .ward import Park, Slum

                if isinstance(p.ward, Park):
                    rate -= 1
                elif isinstance(p.ward, Slum):
                    rate += 1
        return rate

    def get_label(self):
        return "Patriciate"


class Park(Ward):
    def create_geometry(self):
        block = self.get_city_block()
        if block.compactness >= 0.7:
            # Radial groves from centroid
            self.geometry = Cutter.radial(block, None, self.ALLEY)
        else:
            # Semi-radial groves from nearest vertex
            self.geometry = Cutter.semi_radial(block, None, self.ALLEY)

    def get_label(self):
        return "Park"


class Cathedral(Ward):
    """Cathedral ward"""

    def create_geometry(self):
        block = self.get_city_block()
        if Random.bool(0.4):
            # 40% ring layout
            self.geometry = Cutter.ring(block, 2 + Random.float() * 4)
        else:
            # Orthogonal layout
            self.geometry = Ward.create_ortho_building(block, 50, 0.8)

    @staticmethod
    def rate_location(model, patch):
        """Rate location suitability for cathedral"""
        # Ideally the main temple should overlook the plaza,
        # otherwise it should be as close to the plaza as possible
        if model.plaza is not None and patch.shape.borders(model.plaza.shape):
            return -1 / patch.shape.square
        else:
            center = model.plaza.shape.center if model.plaza else model.center
            return patch.shape.distance(center) * patch.shape.square

    def get_label(self):
        return "Temple"


class Farm(Ward):
    def create_geometry(self):
        # Single house plus ortho subdivision
        housing = Polygon.rect(4, 4)
        verts = self.patch.shape.vertices
        if not verts:
            self.geometry = [housing]
            return

        # Pick random vertex and interpolate toward centroid
        idx = int(Random.float() * len(verts)) % len(verts)
        rand_v = verts[idx]
        centroid = self.patch.shape.centroid
        pos = geom_interpolate(rand_v, centroid, 0.3 + Random.float() * 0.4)

        housing.rotate(Random.float() * math.pi)
        housing.offset(pos)

        self.geometry = Ward.create_ortho_building(housing, 8, 0.5)

    def get_label(self):
        return "Farm"
