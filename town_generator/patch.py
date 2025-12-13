"""
Patch class representing a city region
"""
from .polygon import Polygon
from .point import Point


class Patch:
    """A patch (region) in the city"""
    
    def __init__(self, vertices):
        if isinstance(vertices, Polygon):
            self.shape = vertices.copy()
        else:
            self.shape = Polygon(vertices)
        self.ward = None
        self.within_walls = False
        self.within_city = False
    
    @staticmethod
    def from_region(region):
        """Create patch from Voronoi region"""
        vertices = [tr.c for tr in region.vertices]
        return Patch(vertices)
    
    def to_dict(self):
        """Convert to dictionary for JSON export"""
        return {
            "shape": self.shape.to_dict(),
            "within_city": self.within_city,
            "within_walls": self.within_walls,
            "ward_type": self.ward.get_label() if self.ward else None,
            "ward_geometry": [g.to_dict() for g in self.ward.geometry] if self.ward and hasattr(self.ward, 'geometry') else []
        }
    
    @staticmethod
    def from_dict(d):
        """Create from dictionary"""
        from .polygon import Polygon
        patch = Patch(Polygon.from_dict(d["shape"]))
        patch.within_city = d.get("within_city", False)
        patch.within_walls = d.get("within_walls", False)
        return patch
