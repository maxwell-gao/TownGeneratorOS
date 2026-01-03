"""
Polygon class for 2D polygons
"""
import math
from .point import Point
from .math_utils import cross, intersect_lines, interpolate as geom_interpolate, sign


class Polygon:
    """2D polygon represented as a list of points"""
    
    DELTA = 0.000001
    
    def __init__(self, vertices=None, copy_points=False):
        if vertices is None:
            self.vertices = []
        elif copy_points:
            # Create copies of points (used when we explicitly want copies)
            self.vertices = [Point(v.x, v.y) if isinstance(v, Point) else Point(v[0], v[1]) for v in vertices]
        else:
            # Preserve point references (matches Haxe behavior)
            self.vertices = [v if isinstance(v, Point) else Point(v[0], v[1]) for v in list(vertices)]
    
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
        """Create a copy of the polygon with copied points"""
        return Polygon(self.vertices, copy_points=True)
    
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
        """Shrink polygon by cutting each edge inward.
        
        This works well for convex polygons. It iteratively cuts 
        along each edge that has a positive distance, keeping the 
        shrunken side.
        """
        q = self.copy()
        i = 0
        
        def process_edge(v1, v2):
            nonlocal q, i
            dd = distances[i] if i < len(distances) else 0
            i += 1
            if dd > 0:
                v = v2 - v1
                n = v.rotate90().norm(dd)
                # Cut and keep the first half (the shrunken side)
                halves = q.cut(v1 + n, v2 + n, 0)
                if len(halves) > 0:
                    q = halves[0]
        
        self.for_edge(process_edge)
        return q
    
    def shrink_eq(self, d):
        """Shrink all edges by same distance"""
        return self.shrink([d] * len(self.vertices))
    
    def peel(self, v1, d):
        """Cut a peel along one edge starting at v1.
        
        This is a version of shrink for insetting just one edge.
        """
        i1 = self.index_of(v1)
        if i1 == -1:
            return self.copy()
        i2 = (i1 + 1) % len(self.vertices)
        v2 = self.vertices[i2]
        
        v = v2 - v1
        n = v.rotate90().norm(d)
        
        return self.cut(v1 + n, v2 + n, 0)[0]
    
    def buffer(self, distances):
        """Buffer polygon by offsetting edges and resolving self-intersections.
        
        Creates a polygon with offset edges, finds all self-intersections,
        and returns the largest valid sub-polygon.
        """
        # Step 1: Create polygon with offset edges
        q = Polygon()
        i = 0
        
        def add_offset_edge(v0, v1):
            nonlocal i
            dd = distances[i] if i < len(distances) else 0
            i += 1
            if dd == 0:
                q.append(Point(v0.x, v0.y))
                q.append(Point(v1.x, v1.y))
            else:
                v = v1 - v0
                n = v.rotate90().norm(dd)
                q.append(v0 + n)
                q.append(v1 + n)
        
        self.for_edge(add_offset_edge)
        
        if len(q.vertices) < 3:
            return self.copy()
        
        # Step 2: Find and insert self-intersection points
        was_cut = True
        last_edge = 0
        
        while was_cut:
            was_cut = False
            n = len(q.vertices)
            
            for i in range(last_edge, n - 2):
                last_edge = i
                
                p11 = q.vertices[i]
                p12 = q.vertices[i + 1]
                x1, y1 = p11.x, p11.y
                dx1, dy1 = p12.x - x1, p12.y - y1
                
                end_j = n if i > 0 else n - 1
                for j in range(i + 2, end_j):
                    p21 = q.vertices[j]
                    p22 = q.vertices[(j + 1) % n]
                    x2, y2 = p21.x, p21.y
                    dx2, dy2 = p22.x - x2, p22.y - y2
                    
                    t = intersect_lines(x1, y1, dx1, dy1, x2, y2, dx2, dy2)
                    if t is not None:
                        if (t.x > self.DELTA and t.x < 1 - self.DELTA and 
                            t.y > self.DELTA and t.y < 1 - self.DELTA):
                            pn = Point(x1 + dx1 * t.x, y1 + dy1 * t.x)
                            
                            # Insert at j+1 first (to not affect i+1)
                            q.vertices.insert(j + 1, Point(pn.x, pn.y))
                            q.vertices.insert(i + 1, Point(pn.x, pn.y))
                            
                            was_cut = True
                            break
                
                if was_cut:
                    break
        
        # Step 3: Find the largest closed sub-polygon
        regular = list(range(len(q.vertices)))
        
        best_part = None
        best_part_sq = float('-inf')
        
        while len(regular) > 0:
            indices = []
            start = regular[0]
            i = start
            
            while True:
                indices.append(i)
                if i in regular:
                    regular.remove(i)
                
                next_idx = (i + 1) % len(q.vertices)
                v = q.vertices[next_idx]
                
                # Find if this vertex appears elsewhere (self-intersection point)
                next1 = -1
                for k, qv in enumerate(q.vertices):
                    if k == next_idx:
                        continue
                    if abs(qv.x - v.x) < self.DELTA and abs(qv.y - v.y) < self.DELTA:
                        next1 = k
                        break
                
                i = next1 if next1 != -1 else next_idx
                
                if i == start:
                    break
                
                # Safety: prevent infinite loops
                if len(indices) > len(q.vertices) * 2:
                    break
            
            if len(indices) >= 3:
                p = Polygon([q.vertices[idx] for idx in indices])
                s = p.square
                if s > best_part_sq:
                    best_part = p
                    best_part_sq = s
        
        return best_part if best_part is not None else self.copy()
    
    def buffer_eq(self, d):
        """Buffer all edges by same distance"""
        return self.buffer([d] * len(self.vertices))
    
    def cut(self, p1, p2, gap=0.0):
        """Cut polygon with line from p1 to p2.
        
        Returns two halves of the polygon. If gap > 0, applies a peel
        operation to create a gap between the halves.
        """
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
            # Match Haxe: point = p1.add(p2.subtract(p1).scale(ratio))
            point1 = p1 + (p2 - p1) * ratio1
            point2 = p1 + (p2 - p1) * ratio2
            
            # Create two halves matching Haxe order
            # half1: slice(edge1+1, edge2+1), then unshift(point1), push(point2)
            half1_verts = [point1] + list(self.vertices[edge1 + 1:edge2 + 1]) + [point2]
            
            # half2: slice(edge2+1).concat(slice(0, edge1+1)), then unshift(point2), push(point1)
            half2_verts = [point2] + list(self.vertices[edge2 + 1:]) + list(self.vertices[:edge1 + 1]) + [point1]
            
            half1 = Polygon(half1_verts)
            half2 = Polygon(half2_verts)
            
            if gap > 0:
                # Apply gap by peeling edges from cut line
                half1 = half1.peel(point2, gap / 2)
                half2 = half2.peel(point1, gap / 2)
            
            # Determine order based on cross product
            v = self.vectori(edge1)
            if cross(dx1, dy1, v.x, v.y) > 0:
                return [half1, half2]
            else:
                return [half2, half1]
        else:
            return [self.copy()]
    
    def vectori(self, index):
        """Get vector from vertex at index to next vertex"""
        if index < 0 or index >= len(self.vertices):
            return Point(0, 0)
        v0 = self.vertices[index]
        v1 = self.vertices[(index + 1) % len(self.vertices)]
        return v1 - v0
    
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
