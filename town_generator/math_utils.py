"""
Mathematical utility functions
"""
import math


def gate(value, min_val, max_val):
    """Clamp value between min and max"""
    return min_val if value < min_val else (value if value < max_val else max_val)


def gatei(value, min_val, max_val):
    """Clamp integer value between min and max"""
    return min_val if value < min_val else (value if value < max_val else max_val)


def sign(value):
    """Sign of value: -1, 0, or 1"""
    if value == 0:
        return 0
    return -1 if value < 0 else 1


def cross(x1, y1, x2, y2):
    """2D cross product"""
    return x1 * y2 - y1 * x2


def scalar(x1, y1, x2, y2):
    """Scalar product"""
    return x1 * x2 + y1 * y2


def distance2line(x1, y1, dx, dy, px, py):
    """Distance from point to line"""
    # Line: (x1, y1) + t*(dx, dy)
    # Point: (px, py)
    # Vector from line start to point
    vx = px - x1
    vy = py - y1
    
    # Projection length
    t = (vx * dx + vy * dy) / (dx * dx + dy * dy) if (dx * dx + dy * dy) > 0 else 0
    
    # Clamp to line segment
    t = max(0, min(1, t))
    
    # Closest point on line
    closest_x = x1 + t * dx
    closest_y = y1 + t * dy
    
    # Distance
    dx_dist = px - closest_x
    dy_dist = py - closest_y
    return math.sqrt(dx_dist * dx_dist + dy_dist * dy_dist)


def interpolate(p1, p2, ratio):
    """Interpolate between two points"""
    from .point import Point
    return Point(
        p1.x + (p2.x - p1.x) * ratio,
        p1.y + (p2.y - p1.y) * ratio
    )


def intersect_lines(x1, y1, dx1, dy1, x2, y2, dx2, dy2):
    """
    Find intersection of two lines.
    Returns (t1, t2) where intersection is at (x1 + t1*dx1, y1 + t1*dy1)
    or None if lines are parallel.
    """
    # Line 1: (x1, y1) + t1*(dx1, dy1)
    # Line 2: (x2, y2) + t2*(dx2, dy2)
    
    # Solve: x1 + t1*dx1 = x2 + t2*dx2
    #        y1 + t1*dy1 = y2 + t2*dy2
    
    denom = dx1 * dy2 - dy1 * dx2
    if abs(denom) < 1e-10:
        return None  # Parallel lines
    
    t2 = ((x1 - x2) * dy1 - (y1 - y2) * dx1) / denom
    t1 = ((x2 - x1) * dx2 + (y2 - y1) * dy2) / (-denom) if abs(dx1) < 1e-10 else (x2 + t2 * dx2 - x1) / dx1
    
    from .point import Point
    return Point(t1, t2)
