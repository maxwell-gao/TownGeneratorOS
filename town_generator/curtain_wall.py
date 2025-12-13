"""
CurtainWall class for city walls
"""

from .polygon import Polygon
from .point import Point
from .random import Random


class CurtainWall:
    """City wall representation"""

    def __init__(self, real, model, patches, reserved):
        # Match Haxe: this.real = true (always true, ignoring parameter)
        self.real = True
        self.patches = patches
        self.gates = []
        self.towers = []
        self.segments = []

        if len(patches) == 1:
            # Match Haxe: shape = patches[0].shape (no copy, direct reference)
            self.shape = patches[0].shape
        else:
            self.shape = model.find_circumference(patches)

            if self.real:
                smooth_factor = min(1, 40 / len(patches))
                # Match Haxe: shape.set([for (v in shape) ...])
                # Haxe Polygon.set(): for (i in 0...p.length) this[i].set(p[i])
                # The new array has same length as shape, so just update in place
                for i, v in enumerate(self.shape.vertices):
                    if v in reserved:
                        # Keep original vertex (already in place)
                        pass
                    else:
                        # Update vertex with smoothed version
                        smoothed_v = self.shape.smooth_vertex(v, smooth_factor)
                        v.set(smoothed_v.x, smoothed_v.y)

        self.segments = [True] * len(self.shape.vertices)
        self._build_gates(real, model, reserved)

    def _build_gates(self, real, model, reserved):
        """Build gates in the wall"""
        if len(self.patches) > 1:
            entrances = [
                v
                for v in self.shape.vertices
                if v not in reserved
                and sum(1 for p in self.patches if p.shape.contains(v)) > 1
            ]
        else:
            entrances = [v for v in self.shape.vertices if v not in reserved]

        if len(entrances) == 0:
            raise ValueError("Bad walled area shape!")

        # Fallback: if entrances are fewer than 3, just use them directly (robustness)
        if len(entrances) < 3:
            self.gates = list(entrances)
            if self.real:
                for gate in self.gates:
                    if gate in self.shape.vertices:
                        smoothed_point = self.shape.smooth_vertex(gate)
                        gate.set(smoothed_point.x, smoothed_point.y)
            return

        while len(entrances) >= 3:
            # Haxe Random.int(0, length) returns [0, length) (exclusive)
            index = Random.int(0, len(entrances))
            gate = entrances[index]
            self.gates.append(gate)

            if self.real:
                outer_wards = [
                    w for w in model.patch_by_vertex(gate) if w not in self.patches
                ]
                if len(outer_wards) == 1:
                    outer = outer_wards[0]
                    if len(outer.shape.vertices) > 3:
                        wall_next = self.shape.next(gate)
                        wall_prev = self.shape.prev(gate)
                        wall = wall_next - wall_prev
                        out = Point(wall.y, -wall.x)

                        farthest = outer.shape.max(
                            lambda v: float("-inf")
                            if (self.shape.contains(v) or v in reserved)
                            else ((v - gate).dot(out) / (v - gate).length)
                            if (v - gate).length > 0
                            else float("-inf")
                        )

                        if farthest:
                            from .patch import Patch

                            halves = outer.shape.split(gate, farthest)
                            new_patches = [Patch(half) for half in halves]
                            # Match Haxe: model.patches.replace(outer, newPatches)
                            # Haxe replace: a[index++] = newEls[0]; then insert rest
                            try:
                                idx = model.patches.index(outer)
                                # Replace at index with new_patches[0], then insert rest
                                model.patches[idx] = new_patches[0]
                                for i in range(1, len(new_patches)):
                                    model.patches.insert(idx + i, new_patches[i])
                            except ValueError:
                                # If outer not found, just add new_patches
                                model.patches.extend(new_patches)

            # Remove neighboring entrances (match Haxe splice operations)
            # Haxe splice(start, count) removes count elements starting from start
            if index == 0:
                # Haxe: entrances.splice(0, 2) then entrances.pop()
                entrances = entrances[2:]  # Remove first 2 elements
                if len(entrances) > 0:
                    entrances.pop()  # Remove last element
            elif index == len(entrances) - 1:
                # Haxe: entrances.splice(index - 1, 2) then entrances.shift()
                entrances = (
                    entrances[: index - 1] + entrances[index + 1 :]
                )  # Remove 2 elements at index-1 and index
                if len(entrances) > 0:
                    entrances.pop(0)  # Remove first element (shift)
            else:
                # Haxe: entrances.splice(index - 1, 3)
                # Remove 3 elements starting from index-1 (index-1, index, index+1)
                entrances = entrances[: index - 1] + entrances[index + 2 :]

        if len(self.gates) == 0:
            # As a fallback, if entrances remain, pick the first as a gate
            if len(entrances) > 0:
                self.gates.append(entrances[0])
            else:
                raise ValueError("Bad walled area shape!")

        # Smooth gate sections (match Haxe: gate.set(shape.smoothVertex(gate)))
        if self.real:
            # Update gates in place - they are references to shape vertices
            for gate in self.gates:
                if gate in self.shape.vertices:
                    smoothed_point = self.shape.smooth_vertex(gate)
                    gate.set(smoothed_point.x, smoothed_point.y)

    def build_towers(self):
        """Build towers along the wall"""
        self.towers = []
        if self.real:
            length = len(self.shape.vertices)
            for i, t in enumerate(self.shape.vertices):
                if t not in self.gates and (
                    self.segments[(i + length - 1) % length] or self.segments[i]
                ):
                    self.towers.append(t)

    def get_radius(self):
        """Get radius of wall"""
        radius = 0.0
        for v in self.shape.vertices:
            radius = max(radius, v.length)
        return radius

    def borders_by(self, patch, v0, v1):
        """Check if wall borders patch at edge"""
        index = (
            self.shape.find_edge(v0, v1)
            if patch in self.patches
            else self.shape.find_edge(v1, v0)
        )
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
