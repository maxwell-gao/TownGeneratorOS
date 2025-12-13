"""
CurtainWall class for city walls
"""
from .polygon import Polygon
from .point import Point
from .random import Random


class CurtainWall:
    """City wall representation"""
    
    def __init__(self, real, model, patches, reserved):
        self.real = real
        self.patches = patches
        self.gates = []
        self.towers = []
        self.segments = []
        
        if len(patches) == 1:
            self.shape = patches[0].shape.copy()
        else:
            self.shape = model.find_circumference(patches)
            
            if real:
                smooth_factor = min(1, 40 / len(patches))
                smoothed = []
                for v in self.shape.vertices:
                    if v in reserved:
                        smoothed.append(v)
                    else:
                        smoothed.append(self.shape.smooth_vertex(v, smooth_factor))
                self.shape = Polygon(smoothed)
        
        self.segments = [True] * len(self.shape.vertices)
        self._build_gates(real, model, reserved)
    
    def _build_gates(self, real, model, reserved):
        """Build gates in the wall"""
        if len(self.patches) > 1:
            entrances = [v for v in self.shape.vertices 
                        if v not in reserved and 
                        sum(1 for p in self.patches if p.shape.contains(v)) > 1]
        else:
            entrances = [v for v in self.shape.vertices if v not in reserved]
        
        if len(entrances) == 0:
            raise ValueError("Bad walled area shape!")
        
        while len(entrances) >= 3:
            index = Random.int(0, len(entrances))
            gate = entrances[index]
            self.gates.append(gate)
            
            if real:
                outer_wards = [w for w in model.patch_by_vertex(gate) 
                              if w not in self.patches]
                if len(outer_wards) == 1:
                    outer = outer_wards[0]
                    if len(outer.shape.vertices) > 3:
                        wall_next = self.shape.next(gate)
                        wall_prev = self.shape.prev(gate)
                        wall = wall_next - wall_prev
                        out = Point(wall.y, -wall.x)
                        
                        farthest = outer.shape.max(lambda v: 
                            float('-inf') if (self.shape.contains(v) or v in reserved) 
                            else ((v - gate).dot(out) / (v - gate).length) if (v - gate).length > 0 else float('-inf'))
                        
                        if farthest:
                            from .patch import Patch
                            halves = outer.shape.split(gate, farthest)
                            new_patches = [Patch(half) for half in halves]
                            model.patches = [p if p != outer else new_patches[0] for p in model.patches]
                            model.patches.extend(new_patches[1:])
            
            # Remove neighboring entrances
            if index == 0:
                entrances = entrances[2:]
                if len(entrances) > 0:
                    entrances.pop()
            elif index == len(entrances) - 1:
                entrances = entrances[:index-1]
                if len(entrances) > 0:
                    entrances.pop(0)
            else:
                entrances = entrances[:index-1] + entrances[index+2:]
        
        if len(self.gates) == 0:
            raise ValueError("Bad walled area shape!")
        
        # Smooth gate sections
        if real:
            smoothed = []
            for v in self.shape.vertices:
                if v in self.gates:
                    smoothed.append(self.shape.smooth_vertex(v))
                else:
                    smoothed.append(v)
            self.shape = Polygon(smoothed)
    
    def build_towers(self):
        """Build towers along the wall"""
        self.towers = []
        if self.real:
            length = len(self.shape.vertices)
            for i, t in enumerate(self.shape.vertices):
                if t not in self.gates and (self.segments[(i + length - 1) % length] or self.segments[i]):
                    self.towers.append(t)
    
    def get_radius(self):
        """Get radius of wall"""
        radius = 0.0
        for v in self.shape.vertices:
            radius = max(radius, v.length)
        return radius
    
    def borders_by(self, patch, v0, v1):
        """Check if wall borders patch at edge"""
        index = self.shape.find_edge(v0, v1) if patch in self.patches else self.shape.find_edge(v1, v0)
        if index != -1 and self.segments[index]:
            return True
        return False
    
    def borders(self, patch):
        """Check if wall borders patch"""
        within_walls = patch in self.patches
        length = len(self.shape.vertices)
        
        for i in range(length):
            if self.segments[i]:
                v0 = self.shape.vertices[i]
                v1 = self.shape.vertices[(i + 1) % length]
                if within_walls:
                    index = patch.shape.find_edge(v0, v1)
                else:
                    index = patch.shape.find_edge(v1, v0)
                if index != -1:
                    return True
        return False
