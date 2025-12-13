"""
Voronoi diagram implementation
"""
import math
from .point import Point
from .math_utils import cross, sign


class Triangle:
    """Triangle for Voronoi diagram"""
    
    def __init__(self, p1, p2, p3):
        # Determine orientation (CCW)
        s = (p2.x - p1.x) * (p2.y + p1.y) + (p3.x - p2.x) * (p3.y + p2.y) + (p1.x - p3.x) * (p1.y + p3.y)
        
        self.p1 = p1
        if s > 0:
            self.p2 = p2
            self.p3 = p3
        else:
            self.p2 = p3
            self.p3 = p2
        
        # Calculate circumcenter
        x1 = (p1.x + self.p2.x) / 2
        y1 = (p1.y + self.p2.y) / 2
        x2 = (self.p2.x + self.p3.x) / 2
        y2 = (self.p2.y + self.p3.y) / 2
        
        dx1 = p1.y - self.p2.y
        dy1 = self.p2.x - p1.x
        dx2 = self.p2.y - self.p3.y
        dy2 = self.p3.x - self.p2.x
        
        if abs(dx1) < 1e-10:
            # Vertical line
            t2 = (x1 - x2) / dx2 if abs(dx2) > 1e-10 else 0
        else:
            tg1 = dy1 / dx1
            t2 = ((y1 - y2) - (x1 - x2) * tg1) / (dy2 - dx2 * tg1) if abs(dy2 - dx2 * tg1) > 1e-10 else 0
        
        self.c = Point(x2 + dx2 * t2, y2 + dy2 * t2)
        self.r = self.c.distance(p1)
    
    def has_edge(self, a, b):
        """Check if triangle has edge from a to b"""
        return ((self.p1 == a and self.p2 == b) or
                (self.p2 == a and self.p3 == b) or
                (self.p3 == a and self.p1 == b))


class Region:
    """Voronoi region"""
    
    def __init__(self, seed):
        self.seed = seed
        self.vertices = []
    
    def sort_vertices(self):
        """Sort vertices by angle"""
        self.vertices.sort(key=lambda v: self._compare_angles(v))
        return self
    
    def _compare_angles(self, v):
        """Helper for sorting"""
        x = v.c.x - self.seed.x
        y = v.c.y - self.seed.y
        return (math.atan2(y, x), v.c.distance(self.seed))
    
    def center(self):
        """Get center of region"""
        if len(self.vertices) == 0:
            return Point(self.seed.x, self.seed.y)
        c = Point(0, 0)
        for v in self.vertices:
            c.x += v.c.x
            c.y += v.c.y
        c.x /= len(self.vertices)
        c.y /= len(self.vertices)
        return c
    
    def borders(self, other):
        """Check if regions share an edge"""
        for v1 in self.vertices:
            for v2 in other.vertices:
                if v1 == v2:
                    i1 = self.vertices.index(v1)
                    i2 = other.vertices.index(v2)
                    len1 = len(self.vertices)
                    len2 = len(other.vertices)
                    if self.vertices[(i1 + 1) % len1] == other.vertices[(i2 + len2 - 1) % len2]:
                        return True
        return False


class Voronoi:
    """Voronoi diagram"""
    
    def __init__(self, minx, miny, maxx, maxy):
        self.triangles = []
        self.points = []
        self.frame = []
        self._regions = {}
        self._regions_dirty = False
        
        # Create frame
        c1 = Point(minx, miny)
        c2 = Point(minx, maxy)
        c3 = Point(maxx, miny)
        c4 = Point(maxx, maxy)
        self.frame = [c1, c2, c3, c4]
        self.points = [c1, c2, c3, c4]
        
        self.triangles.append(Triangle(c1, c2, c3))
        self.triangles.append(Triangle(c2, c3, c4))
        
        # Build initial regions
        for p in self.points:
            self._regions[p] = self._build_region(p)
        self._regions_dirty = False
    
    def _is_real(self, tr):
        """Check if triangle is real (not using frame points)"""
        return not (tr.p1 in self.frame or tr.p2 in self.frame or tr.p3 in self.frame)
    
    def add_point(self, p):
        """Add a point to the Voronoi diagram"""
        to_split = []
        for tr in self.triangles:
            if p.distance(tr.c) < tr.r:
                to_split.append(tr)
        
        if len(to_split) > 0:
            self.points.append(p)
            
            a = []
            b = []
            for t1 in to_split:
                e1 = True
                e2 = True
                e3 = True
                for t2 in to_split:
                    if t2 != t1:
                        if e1 and t2.has_edge(t1.p2, t1.p1):
                            e1 = False
                        if e2 and t2.has_edge(t1.p3, t1.p2):
                            e2 = False
                        if e3 and t2.has_edge(t1.p1, t1.p3):
                            e3 = False
                        if not (e1 or e2 or e3):
                            break
                if e1:
                    a.append(t1.p1)
                    b.append(t1.p2)
                if e2:
                    a.append(t1.p2)
                    b.append(t1.p3)
                if e3:
                    a.append(t1.p3)
                    b.append(t1.p1)
            
            index = 0
            if len(a) > 0:
                while True:
                    self.triangles.append(Triangle(p, a[index], b[index]))
                    try:
                        index = a.index(b[index])
                    except ValueError:
                        break
                    if index == 0:
                        break
            
            for tr in to_split:
                self.triangles.remove(tr)
            
            self._regions_dirty = True
    
    def _build_region(self, p):
        """Build region for a point"""
        r = Region(p)
        for tr in self.triangles:
            if tr.p1 == p or tr.p2 == p or tr.p3 == p:
                r.vertices.append(tr)
        return r.sort_vertices()
    
    @property
    def regions(self):
        """Get all regions"""
        if self._regions_dirty:
            self._regions = {}
            for p in self.points:
                self._regions[p] = self._build_region(p)
            self._regions_dirty = False
        return self._regions
    
    def triangulation(self):
        """Get real triangles (without frame points)"""
        return [tr for tr in self.triangles if self._is_real(tr)]
    
    def partitioning(self):
        """Get real regions"""
        result = []
        for p in self.points:
            r = self.regions[p]
            is_real = True
            for v in r.vertices:
                if not self._is_real(v):
                    is_real = False
                    break
            if is_real:
                result.append(r)
        return result
    
    def get_neighbours(self, r1):
        """Get neighbouring regions"""
        return [r2 for r2 in self.regions.values() if r1.borders(r2)]
    
    @staticmethod
    def relax(voronoi, to_relax=None):
        """Relax Voronoi diagram"""
        regions = voronoi.partitioning()
        points = [p for p in voronoi.points if p not in voronoi.frame]
        
        if to_relax is None:
            to_relax = voronoi.points
        
        for r in regions:
            if r.seed in to_relax:
                if r.seed in points:
                    points.remove(r.seed)
                points.append(r.center())
        
        return Voronoi.build(points)
    
    @staticmethod
    def build(vertices):
        """Build Voronoi diagram from vertices"""
        if len(vertices) == 0:
            return Voronoi(-100, -100, 100, 100)
        
        minx = min(v.x for v in vertices)
        miny = min(v.y for v in vertices)
        maxx = max(v.x for v in vertices)
        maxy = max(v.y for v in vertices)
        
        dx = (maxx - minx) * 0.5
        dy = (maxy - miny) * 0.5
        
        voronoi = Voronoi(minx - dx/2, miny - dy/2, maxx + dx/2, maxy + dy/2)
        for v in vertices:
            voronoi.add_point(v)
        
        return voronoi
