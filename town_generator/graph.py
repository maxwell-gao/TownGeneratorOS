"""
Graph class for pathfinding
"""
from .point import Point


class Node:
    """Node in graph"""
    
    def __init__(self):
        self.links = {}  # Map<Node, Float>
    
    def link(self, other, weight):
        """Link to another node"""
        self.links[other] = weight
        other.links[self] = weight
    
    def unlink(self, other):
        """Unlink from another node"""
        if other in self.links:
            del self.links[other]
        if self in other.links:
            del other.links[self]
    
    def unlink_all(self):
        """Unlink from all nodes"""
        for other in list(self.links.keys()):
            self.unlink(other)


class Graph:
    """Graph for pathfinding"""
    
    def __init__(self):
        self.nodes = []
    
    def add(self, node=None):
        """Add a node"""
        if node is None:
            node = Node()
        self.nodes.append(node)
        return node
    
    def remove(self, node):
        """Remove a node"""
        node.unlink_all()
        if node in self.nodes:
            self.nodes.remove(node)
    
    def a_star(self, start, goal, exclude=None):
        """A* pathfinding"""
        closed_set = set(exclude or [])
        open_set = [start]
        came_from = {}
        g_score = {start: 0}
        
        while len(open_set) > 0:
            # Find node with lowest g_score
            current = min(open_set, key=lambda n: g_score.get(n, float('inf')))
            
            if current == goal:
                return self._build_path(came_from, current)
            
            open_set.remove(current)
            closed_set.add(current)
            
            cur_score = g_score[current]
            for neighbour, weight in current.links.items():
                if neighbour in closed_set:
                    continue
                
                score = cur_score + weight
                if neighbour not in open_set:
                    open_set.append(neighbour)
                elif score >= g_score.get(neighbour, float('inf')):
                    continue
                
                came_from[neighbour] = current
                g_score[neighbour] = score
        
        return None
    
    def _build_path(self, came_from, current):
        """Build path from came_from map"""
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path
