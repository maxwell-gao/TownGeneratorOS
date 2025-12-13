"""
Point class for 2D coordinates
"""
import math


class Point:
    """2D point with x, y coordinates"""
    
    def __init__(self, x=0.0, y=0.0):
        self.x = float(x)
        self.y = float(y)
    
    def __eq__(self, other):
        if not isinstance(other, Point):
            return False
        return abs(self.x - other.x) < 1e-10 and abs(self.y - other.y) < 1e-10
    
    def __hash__(self):
        return hash((self.x, self.y))
    
    def __repr__(self):
        return f"Point({self.x:.2f}, {self.y:.2f})"
    
    def __add__(self, other):
        if isinstance(other, Point):
            return Point(self.x + other.x, self.y + other.y)
        return Point(self.x + other, self.y + other)
    
    def __sub__(self, other):
        if isinstance(other, Point):
            return Point(self.x - other.x, self.y - other.y)
        return Point(self.x - other, self.y - other)
    
    def __mul__(self, scalar):
        return Point(self.x * scalar, self.y * scalar)
    
    def __rmul__(self, scalar):
        return self.__mul__(scalar)
    
    def __truediv__(self, scalar):
        return Point(self.x / scalar, self.y / scalar)
    
    def clone(self):
        return Point(self.x, self.y)
    
    def set(self, x, y=None):
        """Set coordinates. Can take Point or (x, y)"""
        if isinstance(x, Point):
            self.x = x.x
            self.y = x.y
        elif y is not None:
            self.x = float(x)
            self.y = float(y)
        else:
            raise ValueError("Invalid arguments")
    
    def set_to(self, x, y):
        self.x = float(x)
        self.y = float(y)
    
    @property
    def length(self):
        return math.sqrt(self.x * self.x + self.y * self.y)
    
    def normalize(self, length=1.0):
        """Normalize to given length, returns self"""
        l = self.length
        if l > 0:
            self.x = (self.x / l) * length
            self.y = (self.y / l) * length
        return self
    
    def norm(self, length=1.0):
        """Return normalized copy"""
        l = self.length
        if l > 0:
            return Point((self.x / l) * length, (self.y / l) * length)
        return Point(0, 0)
    
    def dot(self, other):
        """Dot product"""
        return self.x * other.x + self.y * other.y
    
    def rotate90(self):
        """Rotate 90 degrees counterclockwise"""
        return Point(-self.y, self.x)
    
    def atan(self):
        """Angle in radians"""
        return math.atan2(self.y, self.x)
    
    def distance(self, other):
        """Distance to another point"""
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)
    
    def to_dict(self):
        """Convert to dictionary for JSON export"""
        return {"x": self.x, "y": self.y}
    
    @staticmethod
    def from_dict(d):
        """Create from dictionary"""
        return Point(d["x"], d["y"])
