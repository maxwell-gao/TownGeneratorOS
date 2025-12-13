"""
Polygon class for 2D polygons
"""
import math
from .point import Point
from .math_utils import cross, intersect_lines, interpolate as geom_interpolate, sign


class Polygon:
    """2D polygon represented as a list of points"""
    
    DELTA = 0.000001
    
    def __init__(self, vertices=None):
        if vertices is None:
            self.vertices = []
        else:
            self.vertices = [Point(v.x, v.y) if isinstance(v, Point) else Point(v[0], v[1]) for v in vertices]
    
    def __len__(self):
        return len(self.vertices)
    
    def __getitem__(self, index):
        return self.vertices[index]
    
    def __setitem__(self, index, value):
        self.vertices[index] = value
    
    def __iter__(self):
        return iter(self.vertices)
    
    def __repr__(self):
        return f"Polygon({len(self.vertices)} vertices)"
    
    def copy(self):
        """Create a copy of the polygon"""
        return Polygon([Point(v.x, v.y) for v in self.vertices])
    
    def append(self, point):
        """Add a vertex"""
        self.vertices.append(point)
    
    def extend(self, points):
        """Add multiple vertices"""
        self.vertices.extend(points)
    
    def index_of(self, point):
        """Find index of point"""
        for i, v in enumerate(self.vertices):
            if v == point:
                return i
        return -1
    
    def contains(self, point):
        """Check if polygon contains a point (as vertex)"""
        return point in self.vertices
    
    @property
    def square(self):
        """Calculate polygon area"""
        if len(self.vertices) < 3:
            return 0.0
        s = 0.0
        for i in range(len(self.vertices)):
            v1 = self.vertices[i]
            v2 = self.vertices[(i + 1) % len(self.vertices)]
            s += v1.x * v2.y - v2.x * v1.y
        return abs(s) * 0.5
    
    @property
    def perimeter(self):
        """Calculate perimeter"""
        if len(self.vertices) < 2:
            return 0.0
        length = 0.0
        for i in range(len(self.vertices)):
            v0 = self.vertices[i]
            v1 = self.vertices[(i + 1) % len(self.vertices)]
            length += v0.distance(v1)
        return length
    
    @property
    def compactness(self):
        """Compactness measure (1.0 for circle, 0.79 for square, 0.60 for triangle)"""
        p = self.perimeter
        if p == 0:
            return 0.0
        return 4 * math.pi * self.square / (p * p)
    
    @property
    def center(self):
        """Fast approximation of centroid (average of vertices)"""
        if len(self.vertices) == 0:
            return Point(0, 0)
        c = Point(0, 0)
        for v in self.vertices:
            c.x += v.x
            c.y += v.y
        c.x /= len(self.vertices)
        c.y /= len(self.vertices)
        return c
    
    @property
    def centroid(self):
        """True centroid"""
        if len(self.vertices) < 3:
            return self.center
        x = 0.0
        y = 0.0
        a = 0.0
        for i in range(len(self.vertices)):
            v0 = self.vertices[i]
            v1 = self.vertices[(i + 1) % len(self.vertices)]
            f = cross(v0.x, v0.y, v1.x, v1.y)
            a += f
            x += (v0.x + v1.x) * f
            y += (v0.y + v1.y) * f
        if abs(a) < 1e-10:
            return self.center
        s6 = 1 / (3 * a)
        return Point(s6 * x, s6 * y)
    
    def for_edge(self, func):
        """Iterate over edges"""
        length = len(self.vertices)
        for i in range(length):
            func(self.vertices[i], self.vertices[(i + 1) % length])
    
    def for_segment(self, func):
        """Iterate over segments (excluding closing edge)"""
        for i in range(len(self.vertices) - 1):
            func(self.vertices[i], self.vertices[i + 1])
    
    def next(self, point):
        """Get next vertex after given point"""
        index = self.index_of(point)
        if index == -1:
            return None
        return self.vertices[(index + 1) % len(self.vertices)]
    
    def prev(self, point):
        """Get previous vertex before given point"""
        index = self.index_of(point)
        if index == -1:
            return None
        return self.vertices[(index + len(self.vertices) - 1) % len(self.vertices)]
    
    def vector(self, point):
        """Get vector from point to next point"""
        next_p = self.next(point)
        if next_p is None:
            return Point(0, 0)
        return next_p - point
    
    def find_edge(self, a, b):
        """Find edge index from a to b"""
        index = self.index_of(a)
        if index == -1:
            return -1
        next_index = (index + 1) % len(self.vertices)
        if self.vertices[next_index] == b:
            return index
        return -1
    
    def is_convex_vertex(self, v):
        """Check if vertex is convex"""
        v0 = self.prev(v)
        v2 = self.next(v)
        if v0 is None or v2 is None:
            return False
        return cross(v.x - v0.x, v.y - v0.y, v2.x - v.x, v2.y - v.y) > 0
    
    def is_convex(self):
        """Check if polygon is convex"""
        for v in self.vertices:
            if not self.is_convex_vertex(v):
                return False
        return True
    
    def smooth_vertex(self, v, f=1.0):
        """Smooth a vertex"""
        prev_v = self.prev(v)
        next_v = self.next(v)
        if prev_v is None or next_v is None:
            return Point(v.x, v.y)
        return Point(
            (prev_v.x + v.x * f + next_v.x) / (2 + f),
            (prev_v.y + v.y * f + next_v.y) / (2 + f)
        )
    
    def smooth_vertex_eq(self, f=1.0):
        """Smooth all vertices"""
        length = len(self.vertices)
        if length < 3:
            return self.copy()
        result = []
        for i in range(length):
            v0 = self.vertices[(i + length - 1) % length]
            v1 = self.vertices[i]
            v2 = self.vertices[(i + 1) % length]
            result.append(Point(
                (v0.x + v1.x * f + v2.x) / (2 + f),
                (v0.y + v1.y * f + v2.y) / (2 + f)
            ))
        return Polygon(result)
    
    def rotate(self, angle):
        """Rotate polygon by angle"""
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        for v in self.vertices:
            vx = v.x * cos_a - v.y * sin_a
            vy = v.y * cos_a + v.x * sin_a
            v.set_to(vx, vy)
    
    def offset(self, point):
        """Offset polygon by point"""
        for v in self.vertices:
            v.x += point.x
            v.y += point.y
    
    def distance(self, point):
        """Minimal distance from any vertex to point"""
        if len(self.vertices) == 0:
            return float('inf')
        min_dist = self.vertices[0].distance(point)
        for v in self.vertices[1:]:
            d = v.distance(point)
            if d < min_dist:
                min_dist = d
        return min_dist
    
    def borders(self, another):
        """Check if polygons share an edge"""
        for i, v in enumerate(self.vertices):
            j = another.index_of(v)
            if j != -1:
                next_v = self.vertices[(i + 1) % len(self.vertices)]
                len2 = len(another.vertices)
                if (next_v == another.vertices[(j + 1) % len2] or
                    next_v == another.vertices[(j + len2 - 1) % len2]):
                    return True
        return False
    
    def min(self, func):
        """Find vertex that minimizes function"""
        if len(self.vertices) == 0:
            return None
        best = self.vertices[0]
        best_val = func(best)
        for v in self.vertices[1:]:
            val = func(v)
            if val < best_val:
                best = v
                best_val = val
        return best
    
    def max(self, func):
        """Find vertex that maximizes function"""
        if len(self.vertices) == 0:
            return None
        best = self.vertices[0]
        best_val = func(best)
        for v in self.vertices[1:]:
            val = func(v)
            if val > best_val:
                best = v
                best_val = val
        return best
    
    def shrink(self, distances):
        """Shrink polygon by distances (simplified version)"""
        # This is a simplified version - full implementation is complex
        # For now, we'll use buffer with negative distances
        return self.buffer([-d for d in distances])
    
    def shrink_eq(self, d):
        """Shrink all edges by same distance"""
        return self.shrink([d] * len(self.vertices))
    
    def buffer(self, distances):
        """Buffer polygon by distances (simplified)"""
        # Simplified buffer - creates offset edges
        result = Polygon()
        for i in range(len(self.vertices)):
            v0 = self.vertices[i]
            v1 = self.vertices[(i + 1) % len(self.vertices)]
            d = distances[i] if i < len(distances) else 0
            if d == 0:
                result.append(v0)
                result.append(v1)
            else:
                v = v1 - v0
                n = v.rotate90().norm(abs(d))
                if d < 0:
                    n = n * -1
                result.append(v0 + n)
                result.append(v1 + n)
        # For now, return simplified result
        # Full implementation would handle self-intersections
        return result
    
    def buffer_eq(self, d):
        """Buffer all edges by same distance"""
        return self.buffer([d] * len(self.vertices))
    
    def cut(self, p1, p2, gap=0.0):
        """Cut polygon with line from p1 to p2"""
        x1, y1 = p1.x, p1.y
        dx1, dy1 = p2.x - x1, p2.y - y1
        
        length = len(self.vertices)
        edge1 = 0
        ratio1 = 0.0
        edge2 = 0
        ratio2 = 0.0
        count = 0
        
        for i in range(length):
            v0 = self.vertices[i]
            v1 = self.vertices[(i + 1) % length]
            
            x2, y2 = v0.x, v0.y
            dx2, dy2 = v1.x - x2, v1.y - y2
            
            t = intersect_lines(x1, y1, dx1, dy1, x2, y2, dx2, dy2)
            if t is not None and 0 <= t.y <= 1:
                if count == 0:
                    edge1 = i
                    ratio1 = t.x
                elif count == 1:
                    edge2 = i
                    ratio2 = t.x
                count += 1
        
        if count == 2:
            point1 = geom_interpolate(p1, p2, ratio1)
            point2 = geom_interpolate(p1, p2, ratio2)
            
            # Create two halves
            half1_verts = [point1] + self.vertices[edge1 + 1:edge2 + 1] + [point2]
            half2_verts = [point2] + self.vertices[edge2 + 1:] + self.vertices[:edge1 + 1] + [point1]
            
            half1 = Polygon(half1_verts)
            half2 = Polygon(half2_verts)
            
            if gap > 0:
                # Apply gap (simplified)
                pass
            
            # Determine order based on cross product
            v = self.vector(self.vertices[edge1])
            if cross(dx1, dy1, v.x, v.y) > 0:
                return [half1, half2]
            else:
                return [half2, half1]
        else:
            return [self.copy()]
    
    def split(self, p1, p2):
        """Split polygon at two points"""
        i1 = self.index_of(p1)
        i2 = self.index_of(p2)
        if i1 == -1 or i2 == -1:
            return [self.copy()]
        return self.spliti(i1, i2)
    
    def spliti(self, i1, i2):
        """Split polygon at two indices"""
        if i1 > i2:
            i1, i2 = i2, i1
        return [
            Polygon(self.vertices[i1:i2 + 1]),
            Polygon(self.vertices[i2:] + self.vertices[:i1 + 1])
        ]
    
    def interpolate(self, p):
        """Get interpolation weights for point"""
        weights = []
        total = 0.0
        for v in self.vertices:
            d = 1.0 / v.distance(p) if v.distance(p) > 0 else 1e10
            weights.append(d)
            total += d
        return [w / total for w in weights]
    
    def to_dict(self):
        """Convert to dictionary for JSON export"""
        return [v.to_dict() for v in self.vertices]
    
    @staticmethod
    def from_dict(d):
        """Create from dictionary"""
        return Polygon([Point.from_dict(v) for v in d])
    
    @staticmethod
    def rect(w=1.0, h=1.0):
        """Create rectangle"""
        return Polygon([
            Point(-w/2, -h/2),
            Point(w/2, -h/2),
            Point(w/2, h/2),
            Point(-w/2, h/2)
        ])
    
    @staticmethod
    def regular(n=8, r=1.0):
        """Create regular polygon"""
        return Polygon([
            Point(r * math.cos(i / n * math.pi * 2), r * math.sin(i / n * math.pi * 2))
            for i in range(n)
        ])
    
    @staticmethod
    def circle(r=1.0):
        """Create circle approximation"""
        return Polygon.regular(16, r)
