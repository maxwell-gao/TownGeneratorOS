"""
Step-by-step visualization for debugging town generation.

This module provides tools to visualize each stage of the generation process,
making it easier to identify where the Python implementation diverges from
the original Haxe version.
"""

import math
import os
from typing import List, Optional, Dict, Any

from .point import Point
from .polygon import Polygon
from .random import Random
from .voronoi import Voronoi, Region
from .patch import Patch
from .curtain_wall import CurtainWall
from .topology import Topology


class StepVisualizer:
    """
    Visualizer for debugging town generation steps.
    
    Usage:
        vis = StepVisualizer(n_patches=15, seed=12345)
        vis.run_step(1)  # Run and visualize step 1
        vis.visualize_step(1)  # Just visualize current state of step 1
        vis.run_all()  # Run all steps with visualization
    """
    
    # Color palette for visualization
    COLORS = {
        'background': '#f5f5dc',
        'patch_fill': '#e8e8e8',
        'patch_stroke': '#666666',
        'inner_fill': '#d4e6d4',
        'plaza_fill': '#ffd700',
        'citadel_fill': '#cd853f',
        'wall_fill': '#8b4513',
        'wall_stroke': '#4a2510',
        'gate': '#ff4500',
        'tower': '#8b0000',
        'street': '#444444',
        'road': '#888888',
        'center': '#ff0000',
        'vertex': '#0000ff',
        'merged_vertex': '#ff00ff',
        'building': '#d2691e',
        'node_inner': '#00ff00',
        'node_outer': '#0000ff',
        'node_blocked': '#ff0000',
    }
    
    # Ward type colors
    WARD_COLORS = {
        'Market': '#ffd700',
        'Castle': '#8b4513',
        'Craftsmen': '#cd853f',
        'Slum': '#a0522d',
        'Merchant': '#daa520',
        'Administration': '#4682b4',
        'Military': '#2f4f4f',
        'Patriciate': '#9370db',
        'Park': '#228b22',
        'Cathedral': '#4169e1',
        'Farm': '#f5deb3',
        'Gate': '#d2691e',
        None: '#e8e8e8',
    }
    
    def __init__(self, n_patches: int = 15, seed: int = -1, output_dir: str = './debug_output'):
        """
        Initialize visualizer.
        
        Args:
            n_patches: Number of patches (city size)
            seed: Random seed (-1 for random)
            output_dir: Directory for output SVG files
        """
        self.n_patches = n_patches
        self.seed = seed if seed > 0 else Random.get_seed()
        self.output_dir = output_dir
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # State for each step
        self.step_states: Dict[int, Dict[str, Any]] = {}
        
        # Current state
        self.reset()
    
    def reset(self):
        """Reset to initial state."""
        Random.reset(self.seed)
        
        self.plaza_needed = Random.bool()
        self.citadel_needed = Random.bool()
        self.walls_needed = Random.bool()
        
        self.patches: List[Patch] = []
        self.inner: List[Patch] = []
        self.citadel: Optional[Patch] = None
        self.plaza: Optional[Patch] = None
        self.center = Point(0, 0)
        self.border: Optional[CurtainWall] = None
        self.wall: Optional[CurtainWall] = None
        self.gates: List[Point] = []
        self.topology: Optional[Topology] = None
        self.streets: List[Polygon] = []
        self.roads: List[Polygon] = []
        self.arteries: List[Polygon] = []
        self.city_radius = 0.0
        
        # For step 1 debugging
        self.voronoi: Optional[Voronoi] = None
        self.spiral_points: List[Point] = []
        
        # For step 2 debugging
        self.merged_vertices: List[Point] = []
        
        self.step_states.clear()
    
    # =========================================================================
    # Step Execution
    # =========================================================================
    
    def run_step(self, step: int):
        """
        Run a specific step and save visualization.
        
        Args:
            step: Step number (1-6)
        """
        if step == 1:
            self._run_step1_build_patches()
        elif step == 2:
            self._run_step2_optimize_junctions()
        elif step == 3:
            self._run_step3_build_walls()
        elif step == 4:
            self._run_step4_build_streets()
        elif step == 5:
            self._run_step5_create_wards()
        elif step == 6:
            self._run_step6_build_geometry()
        else:
            raise ValueError(f"Unknown step: {step}")
        
        self.visualize_step(step)
    
    def run_all(self, max_retries: int = 10):
        """Run all steps with visualization. Retries with new seed on failure."""
        for attempt in range(max_retries):
            try:
                self.reset()
                for step in range(1, 7):
                    self.run_step(step)
                return  # Success
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                # Generate new seed for next attempt
                self.seed = Random.get_seed() + attempt + 1
        raise RuntimeError(f"Failed to generate city after {max_retries} attempts")
    
    def run_until(self, step: int):
        """Run all steps up to and including the specified step."""
        self.reset()
        for s in range(1, step + 1):
            self.run_step(s)
    
    # =========================================================================
    # Step 1: Build Patches
    # =========================================================================
    
    def _run_step1_build_patches(self):
        """Execute step 1: Build Voronoi patches."""
        # Generate spiral points
        sa = Random.float() * 2 * math.pi
        self.spiral_points = []
        for i in range(self.n_patches * 8):
            a = sa + math.sqrt(i) * 5
            r = 0 if i == 0 else 10 + i * (2 + Random.float())
            self.spiral_points.append(Point(math.cos(a) * r, math.sin(a) * r))
        
        # Build Voronoi diagram
        self.voronoi = Voronoi.build(self.spiral_points)
        
        # Relax central wards
        for _ in range(3):
            to_relax = self.voronoi.points[:3] + [self.voronoi.points[self.n_patches]]
            self.voronoi = Voronoi.relax(self.voronoi, to_relax)
        
        # Sort points by distance from center
        self.voronoi.points.sort(key=lambda p: p.length)
        regions = self.voronoi.partitioning()
        
        # Create patches
        self.patches = []
        self.inner = []
        
        count = 0
        for r in regions:
            patch = Patch.from_region(r)
            self.patches.append(patch)
            
            if count == 0:
                self.center = patch.shape.min(lambda p: p.length)
                if self.plaza_needed:
                    self.plaza = patch
            elif count == self.n_patches and self.citadel_needed:
                self.citadel = patch
                self.citadel.within_city = True
            
            if count < self.n_patches:
                patch.within_city = True
                patch.within_walls = self.walls_needed
                self.inner.append(patch)
            
            count += 1
        
        # Save state for visualization
        self.step_states[1] = {
            'spiral_points': self.spiral_points.copy(),
            'voronoi': self.voronoi,
            'patches': self.patches.copy(),
            'inner': self.inner.copy(),
            'center': Point(self.center.x, self.center.y),
            'plaza': self.plaza,
            'citadel': self.citadel,
        }
    
    # =========================================================================
    # Step 2: Optimize Junctions
    # =========================================================================
    
    def _run_step2_optimize_junctions(self):
        """Execute step 2: Optimize patch junctions."""
        self.merged_vertices = []
        
        patches_to_optimize = (
            self.inner if self.citadel is None else self.inner + [self.citadel]
        )
        
        wards_to_clean = []
        for w in patches_to_optimize:
            index = 0
            while index < len(w.shape.vertices):
                v0 = w.shape.vertices[index]
                v1 = w.shape.vertices[(index + 1) % len(w.shape.vertices)]
                
                if v0 != v1 and v0.distance(v1) < 8:
                    # Record merged vertex for visualization
                    mid = Point((v0.x + v1.x) / 2, (v0.y + v1.y) / 2)
                    self.merged_vertices.append(mid)
                    
                    for w1 in self._patch_by_vertex(v1):
                        if w1 != w:
                            idx = w1.shape.index_of(v1)
                            if idx != -1:
                                w1.shape.vertices[idx] = v0
                            wards_to_clean.append(w1)
                    
                    v0.set((v0.x + v1.x) / 2, (v0.y + v1.y) / 2)
                    w.shape.vertices.remove(v1)
                else:
                    index += 1
        
        # Remove duplicate vertices
        for w in wards_to_clean:
            i = 0
            while i < len(w.shape.vertices):
                v = w.shape.vertices[i]
                dup_idx = (
                    w.shape.vertices.index(v, i + 1)
                    if v in w.shape.vertices[i + 1:]
                    else -1
                )
                if dup_idx != -1:
                    w.shape.vertices.pop(dup_idx)
                else:
                    i += 1
        
        self.step_states[2] = {
            'patches': self.patches.copy(),
            'merged_vertices': self.merged_vertices.copy(),
        }
    
    def _patch_by_vertex(self, v: Point) -> List[Patch]:
        """Get patches containing vertex."""
        return [p for p in self.patches if p.shape.contains(v)]
    
    # =========================================================================
    # Step 3: Build Walls
    # =========================================================================
    
    def _run_step3_build_walls(self):
        """Execute step 3: Build city walls."""
        reserved = self.citadel.shape.vertices.copy() if self.citadel else []
        
        self.border = CurtainWall(self.walls_needed, self, self.inner, reserved)
        if self.walls_needed:
            self.wall = self.border
            self.wall.build_towers()
        
        radius = self.border.get_radius()
        self.patches = [
            p for p in self.patches if p.shape.distance(self.center) < radius * 3
        ]
        
        self.gates = self.border.gates.copy()
        
        if self.citadel is not None:
            from .ward import Castle
            castle = Castle(self, self.citadel)
            castle.wall.build_towers()
            self.citadel.ward = castle
            
            if self.citadel.shape.compactness < 0.75:
                raise ValueError("Bad citadel shape!")
            
            self.gates.extend(castle.wall.gates)
        
        self.step_states[3] = {
            'patches': self.patches.copy(),
            'border': self.border,
            'wall': self.wall,
            'gates': self.gates.copy(),
            'citadel': self.citadel,
        }
    
    # =========================================================================
    # Step 4: Build Streets
    # =========================================================================
    
    def _run_step4_build_streets(self):
        """Execute step 4: Build streets and roads."""
        self.streets = []
        self.roads = []
        
        self.topology = Topology(self)
        
        for gate in self.gates:
            end = (
                self.plaza.shape.min(lambda v: v.distance(gate))
                if self.plaza
                else self.center
            )
            
            street = self.topology.build_path(gate, end, self.topology.outer)
            if street is None:
                raise ValueError("Unable to build a street!")
            
            self.streets.append(Polygon(street))
            
            if gate in self.border.gates:
                dir_pt = gate.norm(1000)
                start = None
                dist = float("inf")
                for p in self.topology.node2pt.values():
                    d = p.distance(dir_pt)
                    if d < dist:
                        dist = d
                        start = p
                
                if start:
                    road = self.topology.build_path(start, gate, self.topology.inner)
                    if road:
                        self.roads.append(Polygon(road))
        
        self._tidy_up_roads()
        
        # Smooth arteries
        for a in self.arteries:
            smoothed = a.smooth_vertex_eq(3)
            for i in range(1, len(a.vertices) - 1):
                a.vertices[i].set(smoothed.vertices[i].x, smoothed.vertices[i].y)
        
        self.step_states[4] = {
            'topology': self.topology,
            'streets': self.streets.copy(),
            'roads': self.roads.copy(),
            'arteries': self.arteries.copy(),
        }
    
    def _tidy_up_roads(self):
        """Tidy up roads and create arteries."""
        segments = []
        
        def cut_to_segments(street):
            if len(street.vertices) < 2:
                return
            v0 = street.vertices[0]
            for i in range(1, len(street.vertices)):
                v1 = street.vertices[i]
                
                if self.plaza and (
                    self.plaza.shape.contains(v0) and self.plaza.shape.contains(v1)
                ):
                    v0 = v1
                    continue
                
                exists = False
                for seg in segments:
                    if seg[0] == v0 and seg[1] == v1:
                        exists = True
                        break
                
                if not exists:
                    segments.append((v0, v1))
                v0 = v1
        
        for street in self.streets:
            cut_to_segments(street)
        for road in self.roads:
            cut_to_segments(road)
        
        self.arteries = []
        while len(segments) > 0:
            seg = segments.pop()
            
            attached = False
            for a in self.arteries:
                if a.vertices[0] == seg[1]:
                    a.vertices.insert(0, seg[0])
                    attached = True
                    break
                elif a.vertices[-1] == seg[0]:
                    a.vertices.append(seg[1])
                    attached = True
                    break
            
            if not attached:
                self.arteries.append(Polygon([seg[0], seg[1]]))
    
    # =========================================================================
    # Step 5: Create Wards
    # =========================================================================
    
    def _run_step5_create_wards(self):
        """Execute step 5: Create wards."""
        from .ward import (
            Ward, CraftsmenWard, MerchantWard, Slum, Market, Castle,
            GateWard, AdministrationWard, MilitaryWard, PatriciateWard,
            Park, Cathedral, Farm
        )
        
        WARDS = [
            CraftsmenWard, CraftsmenWard, MerchantWard, CraftsmenWard, CraftsmenWard, Cathedral,
            CraftsmenWard, CraftsmenWard, CraftsmenWard, CraftsmenWard, CraftsmenWard,
            CraftsmenWard, CraftsmenWard, CraftsmenWard, AdministrationWard, CraftsmenWard,
            Slum, CraftsmenWard, Slum, PatriciateWard, Market,
            Slum, CraftsmenWard, CraftsmenWard, CraftsmenWard, Slum,
            CraftsmenWard, CraftsmenWard, CraftsmenWard, MilitaryWard, Slum,
            CraftsmenWard, Park, PatriciateWard, Market, MerchantWard,
        ]
        
        unassigned = self.inner.copy()
        
        if self.plaza:
            self.plaza.ward = Market(self, self.plaza)
            unassigned.remove(self.plaza)
        
        # Assign gate wards
        for gate in self.border.gates:
            for patch in self._patch_by_vertex(gate):
                if patch.within_city and patch.ward is None:
                    chance = 0.2 if self.wall is None else 0.5
                    if Random.bool(chance):
                        patch.ward = GateWard(self, patch)
                        if patch in unassigned:
                            unassigned.remove(patch)
        
        # Assign other wards
        wards = list(WARDS)
        for _ in range(len(wards) // 10):
            index = Random.int(0, len(wards) - 1)
            if index < len(wards) - 1:
                wards[index], wards[index + 1] = wards[index + 1], wards[index]
        
        while len(unassigned) > 0:
            best_patch = None
            
            ward_class = wards.pop(0) if len(wards) > 0 else Slum
            rate_func = getattr(ward_class, 'rate_location', None)
            
            if rate_func is None:
                best_patch = unassigned[Random.int(0, len(unassigned))]
            else:
                best_patch = min(
                    unassigned,
                    key=lambda p: float("inf") if p.ward else rate_func(self, p)
                )
            
            best_patch.ward = ward_class(self, best_patch)
            unassigned.remove(best_patch)
        
        # Outskirts
        if self.wall:
            for gate in self.wall.gates:
                if not Random.bool(1.0 / (self.n_patches - 5)):
                    for patch in self._patch_by_vertex(gate):
                        if patch.ward is None:
                            patch.within_city = True
                            patch.ward = GateWard(self, patch)
        
        # Calculate radius and countryside
        self.city_radius = 0
        for patch in self.patches:
            if patch.within_city:
                for v in patch.shape.vertices:
                    self.city_radius = max(self.city_radius, v.length)
            elif patch.ward is None:
                if Random.bool(0.2) and patch.shape.compactness >= 0.7:
                    patch.ward = Farm(self, patch)
                else:
                    patch.ward = Ward(self, patch)
        
        self.step_states[5] = {
            'patches': self.patches.copy(),
            'city_radius': self.city_radius,
        }
    
    # =========================================================================
    # Step 6: Build Geometry
    # =========================================================================
    
    def _run_step6_build_geometry(self):
        """Execute step 6: Build geometry for all patches."""
        for patch in self.patches:
            if patch.ward:
                patch.ward.create_geometry()
        
        self.step_states[6] = {
            'patches': self.patches.copy(),
        }
    
    # =========================================================================
    # Visualization Methods
    # =========================================================================
    
    def visualize_step(self, step: int, filename: str = None):
        """
        Generate SVG visualization for a specific step.
        
        Args:
            step: Step number (1-6)
            filename: Output filename (default: step_N.svg)
        """
        if step not in self.step_states:
            print(f"Step {step} has not been executed yet. Run run_step({step}) first.")
            return
        
        if filename is None:
            filename = f"step_{step}.svg"
        
        filepath = os.path.join(self.output_dir, filename)
        
        if step == 1:
            svg = self._visualize_step1()
        elif step == 2:
            svg = self._visualize_step2()
        elif step == 3:
            svg = self._visualize_step3()
        elif step == 4:
            svg = self._visualize_step4()
        elif step == 5:
            svg = self._visualize_step5()
        elif step == 6:
            svg = self._visualize_step6()
        else:
            svg = ""
        
        with open(filepath, 'w') as f:
            f.write(svg)
        
        print(f"Step {step} visualization saved to: {filepath}")
    
    def _get_bounds(self) -> tuple:
        """Calculate bounding box of all patches."""
        all_points = []
        for patch in self.patches:
            all_points.extend(patch.shape.vertices)
        
        if not all_points:
            return -100, -100, 100, 100
        
        min_x = min(p.x for p in all_points)
        min_y = min(p.y for p in all_points)
        max_x = max(p.x for p in all_points)
        max_y = max(p.y for p in all_points)
        
        # Add padding
        padding = 20
        return min_x - padding, min_y - padding, max_x + padding, max_y + padding
    
    def _svg_header(self, width: int = 800, height: int = 800) -> str:
        """Generate SVG header."""
        min_x, min_y, max_x, max_y = self._get_bounds()
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" 
     width="{width}" height="{height}" 
     viewBox="{min_x} {min_y} {max_x - min_x} {max_y - min_y}">
<style>
    .patch {{ fill: {self.COLORS['patch_fill']}; stroke: {self.COLORS['patch_stroke']}; stroke-width: 0.5; }}
    .inner {{ fill: {self.COLORS['inner_fill']}; }}
    .plaza {{ fill: {self.COLORS['plaza_fill']}; }}
    .citadel {{ fill: {self.COLORS['citadel_fill']}; }}
    .wall {{ fill: none; stroke: {self.COLORS['wall_stroke']}; stroke-width: 2; }}
    .wall-fill {{ fill: {self.COLORS['wall_fill']}; opacity: 0.3; }}
    .gate {{ fill: {self.COLORS['gate']}; }}
    .tower {{ fill: {self.COLORS['tower']}; }}
    .street {{ stroke: {self.COLORS['street']}; stroke-width: 1.5; fill: none; }}
    .road {{ stroke: {self.COLORS['road']}; stroke-width: 1; fill: none; stroke-dasharray: 3,2; }}
    .center {{ fill: {self.COLORS['center']}; }}
    .vertex {{ fill: {self.COLORS['vertex']}; }}
    .merged {{ fill: {self.COLORS['merged_vertex']}; }}
    .building {{ fill: {self.COLORS['building']}; stroke: #8b4513; stroke-width: 0.3; }}
    .node-inner {{ fill: {self.COLORS['node_inner']}; opacity: 0.5; }}
    .node-outer {{ fill: {self.COLORS['node_outer']}; opacity: 0.5; }}
    .spiral-point {{ fill: #999; }}
    .voronoi-point {{ fill: #333; }}
    .label {{ font-family: Arial, sans-serif; font-size: 3px; fill: #333; }}
</style>
<rect x="{min_x}" y="{min_y}" width="{max_x - min_x}" height="{max_y - min_y}" 
      fill="{self.COLORS['background']}"/>
'''
    
    def _svg_footer(self) -> str:
        """Generate SVG footer."""
        return '</svg>'
    
    def _polygon_to_path(self, poly: Polygon) -> str:
        """Convert polygon to SVG path."""
        if len(poly.vertices) < 2:
            return ""
        path = f"M {poly.vertices[0].x:.2f} {poly.vertices[0].y:.2f}"
        for v in poly.vertices[1:]:
            path += f" L {v.x:.2f} {v.y:.2f}"
        path += " Z"
        return path
    
    def _polyline_to_path(self, poly: Polygon) -> str:
        """Convert polygon to SVG path (no closing)."""
        if len(poly.vertices) < 2:
            return ""
        path = f"M {poly.vertices[0].x:.2f} {poly.vertices[0].y:.2f}"
        for v in poly.vertices[1:]:
            path += f" L {v.x:.2f} {v.y:.2f}"
        return path
    
    def _visualize_step1(self) -> str:
        """Visualize step 1: Voronoi patches."""
        svg = self._svg_header()
        svg += '<!-- Step 1: Build Patches -->\n'
        svg += '<g id="patches">\n'
        
        # Draw all patches
        for i, patch in enumerate(self.patches):
            css_class = "patch"
            if patch == self.plaza:
                css_class += " plaza"
            elif patch == self.citadel:
                css_class += " citadel"
            elif patch.within_city:
                css_class += " inner"
            
            path = self._polygon_to_path(patch.shape)
            svg += f'  <path class="{css_class}" d="{path}"/>\n'
        
        svg += '</g>\n'
        
        # Draw spiral points
        svg += '<g id="spiral-points">\n'
        for p in self.spiral_points[:20]:  # Just first 20 for clarity
            svg += f'  <circle class="spiral-point" cx="{p.x:.2f}" cy="{p.y:.2f}" r="1"/>\n'
        svg += '</g>\n'
        
        # Draw center
        svg += f'<circle class="center" cx="{self.center.x:.2f}" cy="{self.center.y:.2f}" r="3"/>\n'
        
        # Legend
        svg += self._add_legend(1)
        
        svg += self._svg_footer()
        return svg
    
    def _visualize_step2(self) -> str:
        """Visualize step 2: Junction optimization."""
        svg = self._svg_header()
        svg += '<!-- Step 2: Optimize Junctions -->\n'
        
        # Draw patches
        svg += '<g id="patches">\n'
        for patch in self.patches:
            css_class = "patch"
            if patch.within_city:
                css_class += " inner"
            path = self._polygon_to_path(patch.shape)
            svg += f'  <path class="{css_class}" d="{path}"/>\n'
        svg += '</g>\n'
        
        # Draw all vertices
        svg += '<g id="vertices">\n'
        for patch in self.inner:
            for v in patch.shape.vertices:
                svg += f'  <circle class="vertex" cx="{v.x:.2f}" cy="{v.y:.2f}" r="1"/>\n'
        svg += '</g>\n'
        
        # Highlight merged vertices
        svg += '<g id="merged-vertices">\n'
        for v in self.merged_vertices:
            svg += f'  <circle class="merged" cx="{v.x:.2f}" cy="{v.y:.2f}" r="2"/>\n'
        svg += '</g>\n'
        
        svg += self._add_legend(2)
        svg += self._svg_footer()
        return svg
    
    def _visualize_step3(self) -> str:
        """Visualize step 3: Walls and gates."""
        svg = self._svg_header()
        svg += '<!-- Step 3: Build Walls -->\n'
        
        # Draw patches
        svg += '<g id="patches">\n'
        for patch in self.patches:
            css_class = "patch"
            if patch == self.citadel:
                css_class += " citadel"
            elif patch.within_city:
                css_class += " inner"
            path = self._polygon_to_path(patch.shape)
            svg += f'  <path class="{css_class}" d="{path}"/>\n'
        svg += '</g>\n'
        
        # Draw wall (if walls_needed) or border (always exists)
        if self.wall:
            path = self._polygon_to_path(self.wall.shape)
            svg += f'<path class="wall-fill" d="{path}"/>\n'
            svg += f'<path class="wall" d="{path}"/>\n'
            
            # Draw towers
            svg += '<g id="towers">\n'
            for t in self.wall.towers:
                svg += f'  <rect class="tower" x="{t.x - 1.5:.2f}" y="{t.y - 1.5:.2f}" width="3" height="3"/>\n'
            svg += '</g>\n'
        elif self.border:
            # Draw border outline (even without walls)
            path = self._polygon_to_path(self.border.shape)
            svg += f'<path d="{path}" fill="none" stroke="#228b22" stroke-width="1.5" stroke-dasharray="5,3"/>\n'
        
        # Draw gates
        svg += '<g id="gates">\n'
        for g in self.gates:
            svg += f'  <circle class="gate" cx="{g.x:.2f}" cy="{g.y:.2f}" r="2"/>\n'
        svg += '</g>\n'
        
        # Draw citadel wall if exists
        if self.citadel and self.citadel.ward and hasattr(self.citadel.ward, 'wall'):
            cwall = self.citadel.ward.wall
            path = self._polygon_to_path(cwall.shape)
            svg += f'<path class="wall" d="{path}" style="stroke: #654321;"/>\n'
        
        svg += self._add_legend(3)
        svg += self._svg_footer()
        return svg
    
    def _visualize_step4(self) -> str:
        """Visualize step 4: Streets and roads."""
        svg = self._svg_header()
        svg += '<!-- Step 4: Build Streets -->\n'
        
        # Draw patches
        svg += '<g id="patches">\n'
        for patch in self.patches:
            css_class = "patch"
            if patch.within_city:
                css_class += " inner"
            path = self._polygon_to_path(patch.shape)
            svg += f'  <path class="{css_class}" d="{path}"/>\n'
        svg += '</g>\n'
        
        # Draw wall
        if self.wall:
            path = self._polygon_to_path(self.wall.shape)
            svg += f'<path class="wall" d="{path}"/>\n'
        
        # Draw roads (outside walls)
        svg += '<g id="roads">\n'
        for road in self.roads:
            path = self._polyline_to_path(road)
            svg += f'  <path class="road" d="{path}"/>\n'
        svg += '</g>\n'
        
        # Draw streets (inside walls)
        svg += '<g id="streets">\n'
        for street in self.streets:
            path = self._polyline_to_path(street)
            svg += f'  <path class="street" d="{path}"/>\n'
        svg += '</g>\n'
        
        # Draw arteries
        svg += '<g id="arteries">\n'
        for artery in self.arteries:
            path = self._polyline_to_path(artery)
            svg += f'  <path class="street" d="{path}" style="stroke: #222; stroke-width: 2;"/>\n'
        svg += '</g>\n'
        
        # Draw gates
        svg += '<g id="gates">\n'
        for g in self.gates:
            svg += f'  <circle class="gate" cx="{g.x:.2f}" cy="{g.y:.2f}" r="2"/>\n'
        svg += '</g>\n'
        
        svg += self._add_legend(4)
        svg += self._svg_footer()
        return svg
    
    def _visualize_step5(self) -> str:
        """Visualize step 5: Ward assignment."""
        svg = self._svg_header()
        svg += '<!-- Step 5: Create Wards -->\n'
        
        # Draw patches with ward colors
        svg += '<g id="patches">\n'
        for patch in self.patches:
            ward_label = patch.ward.get_label() if patch.ward else None
            color = self.WARD_COLORS.get(ward_label, self.WARD_COLORS[None])
            path = self._polygon_to_path(patch.shape)
            svg += f'  <path d="{path}" fill="{color}" stroke="#666" stroke-width="0.5"/>\n'
            
            # Add label
            if ward_label and patch.within_city:
                c = patch.shape.center
                svg += f'  <text class="label" x="{c.x:.2f}" y="{c.y:.2f}" text-anchor="middle">{ward_label}</text>\n'
        svg += '</g>\n'
        
        # Draw wall
        if self.wall:
            path = self._polygon_to_path(self.wall.shape)
            svg += f'<path class="wall" d="{path}"/>\n'
        
        # Draw arteries
        svg += '<g id="arteries">\n'
        for artery in self.arteries:
            path = self._polyline_to_path(artery)
            svg += f'  <path class="street" d="{path}"/>\n'
        svg += '</g>\n'
        
        svg += self._add_legend(5)
        svg += self._svg_footer()
        return svg
    
    def _visualize_step6(self) -> str:
        """Visualize step 6: Building geometry."""
        svg = self._svg_header()
        svg += '<!-- Step 6: Build Geometry -->\n'
        
        # Draw patches (light)
        svg += '<g id="patches">\n'
        for patch in self.patches:
            ward_label = patch.ward.get_label() if patch.ward else None
            color = self.WARD_COLORS.get(ward_label, self.WARD_COLORS[None])
            # Lighten color for background
            path = self._polygon_to_path(patch.shape)
            svg += f'  <path d="{path}" fill="{color}" opacity="0.3" stroke="#999" stroke-width="0.3"/>\n'
        svg += '</g>\n'
        
        # Draw buildings
        svg += '<g id="buildings">\n'
        for patch in self.patches:
            if patch.ward and patch.ward.geometry:
                for building in patch.ward.geometry:
                    path = self._polygon_to_path(building)
                    if path:
                        svg += f'  <path class="building" d="{path}"/>\n'
        svg += '</g>\n'
        
        # Draw wall
        if self.wall:
            path = self._polygon_to_path(self.wall.shape)
            svg += f'<path class="wall" d="{path}"/>\n'
            
            # Draw towers
            for t in self.wall.towers:
                svg += f'<rect class="tower" x="{t.x - 1.5:.2f}" y="{t.y - 1.5:.2f}" width="3" height="3"/>\n'
        
        # Draw arteries
        svg += '<g id="arteries">\n'
        for artery in self.arteries:
            path = self._polyline_to_path(artery)
            svg += f'  <path class="street" d="{path}"/>\n'
        svg += '</g>\n'
        
        svg += self._add_legend(6)
        svg += self._svg_footer()
        return svg
    
    def _add_legend(self, step: int) -> str:
        """Add legend for the step."""
        min_x, min_y, max_x, max_y = self._get_bounds()
        
        step_names = {
            1: "Step 1: Build Patches (Voronoi)",
            2: "Step 2: Optimize Junctions",
            3: "Step 3: Build Walls &amp; Gates",
            4: "Step 4: Build Streets &amp; Roads",
            5: "Step 5: Assign Ward Types",
            6: "Step 6: Generate Buildings",
        }
        
        # Title
        svg = f'<text x="{min_x + 5}" y="{min_y + 8}" font-family="Arial" font-size="6" font-weight="bold">{step_names.get(step, "")}</text>\n'
        
        # Info
        info = [
            f"Patches: {len(self.patches)}",
            f"Inner: {len(self.inner)}",
            f"Seed: {self.seed}",
            f"Plaza: {'Yes' if self.plaza_needed else 'No'}",
            f"Citadel: {'Yes' if self.citadel_needed else 'No'}",
            f"Walls: {'Yes' if self.walls_needed else 'No'}",
        ]
        
        for i, text in enumerate(info):
            svg += f'<text x="{min_x + 5}" y="{min_y + 14 + i * 4}" font-family="Arial" font-size="3">{text}</text>\n'
        
        return svg
    
    # =========================================================================
    # Helper Methods for Model Interface
    # =========================================================================
    
    def find_circumference(self, wards: List[Patch]) -> Polygon:
        """Find circumference polygon of wards (needed for CurtainWall)."""
        if len(wards) == 0:
            return Polygon()
        elif len(wards) == 1:
            return Polygon(wards[0].shape.vertices)
        
        A = []
        B = []
        
        for w1 in wards:
            for i in range(len(w1.shape.vertices)):
                a = w1.shape.vertices[i]
                b = w1.shape.vertices[(i + 1) % len(w1.shape.vertices)]
                
                outer_edge = True
                # Note: Haxe version checks ALL wards (including w1 itself)
                for w2 in wards:
                    if w2.shape.find_edge(b, a) != -1:
                        outer_edge = False
                        break
                
                if outer_edge:
                    A.append(a)
                    B.append(b)
        
        if len(A) == 0:
            return Polygon()
        
        result = Polygon()
        index = 0
        while True:
            result.append(A[index])
            try:
                next_index = A.index(B[index])
            except ValueError:
                break
            if next_index == index:
                break
            if next_index == 0:
                break
            index = next_index
        
        return result
    
    def patch_by_vertex(self, v: Point) -> List[Patch]:
        """Get patches containing vertex (public interface)."""
        return self._patch_by_vertex(v)
    
    def get_neighbour(self, patch: Patch, v: Point):
        """Get neighbouring patch at vertex."""
        next_v = patch.shape.next(v)
        if next_v is None:
            return None
        for p in self.patches:
            if p != patch and p.shape.find_edge(next_v, v) != -1:
                return p
        return None
    
    def get_neighbours(self, patch: Patch) -> List[Patch]:
        """Get all neighbouring patches."""
        return [p for p in self.patches if p != patch and p.shape.borders(patch.shape)]
    
    def is_enclosed(self, patch: Patch) -> bool:
        """Check if patch is enclosed."""
        if not patch.within_city:
            return False
        if patch.within_walls:
            return True
        return all(p.within_city for p in self.get_neighbours(patch))

