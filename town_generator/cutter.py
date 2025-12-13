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
