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

        # Build blocked points (match Haxe: citadel.shape and wall.shape are arrays)
        blocked = []
        if model.citadel is not None:
            blocked.extend(model.citadel.shape.vertices)
        if model.wall is not None:
            blocked.extend(model.wall.shape.vertices)
        # Remove gates from blocked (difference operation)
        blocked = [p for p in blocked if p not in model.gates]

        # border is the shape itself (Polygon), not vertices
        border = model.border.shape

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

                # Match Haxe: !border.contains(v0) - border is Polygon, check contains
                if n0 is not None and not border.contains(v0):
                    if within_city:
                        if n0 not in self.inner:
                            self.inner.append(n0)
                    else:
                        if n0 not in self.outer:
                            self.outer.append(n0)

                if n1 is not None and not border.contains(v1):
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
        # Match Haxe: first get or create node, then check if blocked
        if v not in self.pt2node:
            node = self.graph.add()
            self.pt2node[v] = node
            self.node2pt[node] = v

        node = self.pt2node[v]
        # Return null if blocked (match Haxe: return blocked.contains(v) ? null : n)
        return None if v in blocked else node

    def build_path(self, from_pt, to_pt, exclude=None):
        """Build path from one point to another.
        
        Args:
            from_pt: Starting point
            to_pt: Ending point  
            exclude: List of Nodes to exclude from pathfinding (NOT Points!)
                     In Haxe: topology.buildPath(gate, end, topology.outer)
                     where topology.outer is Array<Node>
        """
        if from_pt not in self.pt2node or to_pt not in self.pt2node:
            return None

        # exclude is already a list of Nodes (matching Haxe: exclude:Array<Node>=null)
        path = self.graph.a_star(
            self.pt2node[from_pt], self.pt2node[to_pt], exclude
        )

        if path is None:
            return None

        return [self.node2pt[node] for node in path]
