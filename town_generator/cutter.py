"""
Cutter class for polygon operations
"""

import math
from .polygon import Polygon
from .point import Point
from .math_utils import interpolate


class Cutter:
    """Utility class for cutting polygons"""

    @staticmethod
    def bisect(poly, vertex, ratio=0.5, angle=0.0, gap=0.0):
        """Bisect polygon at vertex"""
        next_v = poly.next(vertex)
        if next_v is None:
            return [poly.copy()]

        p1 = interpolate(vertex, next_v, ratio)
        d = next_v - vertex

        cos_b = math.cos(angle)
        sin_b = math.sin(angle)
        vx = d.x * cos_b - d.y * sin_b
        vy = d.y * cos_b + d.x * sin_b
        p2 = Point(p1.x - vy, p1.y + vx)

        return poly.cut(p1, p2, gap)

    @staticmethod
    def radial(poly, center=None, gap=0.0):
        """Create radial sectors from centroid to each edge"""
        if center is None:
            center = poly.centroid

        sectors = []
        poly.for_edge(lambda v0, v1: sectors.append(Polygon([center, v0, v1])))

        if gap > 0:
            half_gap = gap / 2
            sectors = [sector.shrink([half_gap, 0, half_gap]) for sector in sectors]

        return sectors

    @staticmethod
    def semi_radial(poly, center=None, gap=0.0):
        """Create semi-radial sectors from nearest vertex to edges"""
        if center is None:
            centroid = poly.centroid
            center = poly.min(lambda v: v.distance(centroid))

        half_gap = gap / 2
        sectors = []

        def add_sector(v0, v1):
            if v0 == center or v1 == center:
                return
            sector = Polygon([center, v0, v1])
            if gap > 0:
                d = [
                    0 if poly.find_edge(center, v0) != -1 else half_gap,
                    0,
                    0 if poly.find_edge(v1, center) != -1 else half_gap,
                ]
                sector = sector.shrink(d)
            sectors.append(sector)

        poly.for_edge(add_sector)
        return sectors

    @staticmethod
    def ring(poly, thickness):
        """Slice polygon into ring peel segments with given thickness"""
        slices = []

        def collect_slice(v1, v2):
            v = v2 - v1
            n = v.rotate90().norm(thickness)
            slices.append({"p1": v1 + n, "p2": v2 + n, "len": v.length})

        poly.for_edge(collect_slice)

        # Short sides first
        slices.sort(key=lambda s: s["len"])

        peel = []
        p = poly
        for sl in slices:
            halves = p.cut(sl["p1"], sl["p2"])
            p = halves[0]
            if len(halves) == 2:
                peel.append(halves[1])

        return peel
