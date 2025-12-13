"""
Topology class for pathfinding
"""
from .point import Point
from .graph import Graph, Node


class Topology:
    """Topology for pathfinding in the city"""
    
    def __init__(self, model):
        self.model = model
        self.graph = Graph()
        self.pt2node = {}
        self.node2pt = {}
        self.inner = []
        self.outer = []
        
        # Build blocked points
        blocked = []
        if model.citadel is not None:
            blocked.extend(model.citadel.shape.vertices)
        if model.wall is not None:
            blocked.extend(model.wall.shape.vertices)
        blocked = [p for p in blocked if p not in model.gates]
        
        border = model.border.shape.vertices
        
        for p in model.patches:
            within_city = p.within_city
            
            if len(p.shape.vertices) == 0:
                continue
            
            v1 = p.shape.vertices[-1]
            n1 = self._process_point(v1, blocked, border, within_city)
            
            for i in range(len(p.shape.vertices)):
                v0 = v1
                v1 = p.shape.vertices[i]
                n0 = n1
                n1 = self._process_point(v1, blocked, border, within_city)
                
                if n0 is not None and v0 not in border:
                    if within_city:
                        if n0 not in self.inner:
                            self.inner.append(n0)
                    else:
                        if n0 not in self.outer:
                            self.outer.append(n0)
                
                if n1 is not None and v1 not in border:
                    if within_city:
                        if n1 not in self.inner:
                            self.inner.append(n1)
                    else:
                        if n1 not in self.outer:
                            self.outer.append(n1)
                
                if n0 is not None and n1 is not None:
                    n0.link(n1, v0.distance(v1))
    
    def _process_point(self, v, blocked, border, within_city):
        """Process a point and return node"""
        if v in blocked:
            return None
        
        if v not in self.pt2node:
            node = self.graph.add()
            self.pt2node[v] = node
            self.node2pt[node] = v
        
        return self.pt2node.get(v)
    
    def build_path(self, from_pt, to_pt, exclude=None):
        """Build path from one point to another"""
        if from_pt not in self.pt2node or to_pt not in self.pt2node:
            return None
        
        exclude_nodes = [self.pt2node[p] for p in (exclude or []) if p in self.pt2node]
        path = self.graph.a_star(self.pt2node[from_pt], self.pt2node[to_pt], exclude_nodes)
        
        if path is None:
            return None
        
        return [self.node2pt[node] for node in path]
