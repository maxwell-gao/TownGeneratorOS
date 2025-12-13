#!/usr/bin/env python3
"""
SVG visualization for Town Generator JSON output
"""

import json
import argparse
import sys
from pathlib import Path


def polygon_to_svg_path(coords, scale=1.0, offset_x=0, offset_y=0):
    """Convert polygon coordinates to SVG path string"""
    if not coords or len(coords) == 0:
        return ""

    # Handle nested coordinates structure safely
    points = None

    try:
        # Check structure depth safely
        if len(coords) > 0 and len(coords[0]) > 0:
            if isinstance(coords[0][0], (int, float)):
                # Single ring: [[x, y], [x, y], ...]
                points = coords
            elif len(coords[0]) > 0 and len(coords[0][0]) > 0:
                if isinstance(coords[0][0][0], (int, float)):
                    # Multiple rings: [[[x, y], ...], [[x, y], ...]]
                    # Use first ring
                    points = coords[0] if coords[0] else None
    except (IndexError, TypeError):
        return ""

    if not points or len(points) < 2:
        return ""

    path_parts = []
    for i, point in enumerate(points):
        try:
            if len(point) < 2:
                continue
            x = point[0] * scale + offset_x
            y = point[1] * scale + offset_y
            if i == 0:
                path_parts.append(f"M {x:.2f} {y:.2f}")
            else:
                path_parts.append(f"L {x:.2f} {y:.2f}")
        except (IndexError, TypeError):
            continue

    if len(path_parts) < 2:  # Need at least M and one L
        return ""

    # Close path
    path_parts.append("Z")
    return " ".join(path_parts)


def linestring_to_svg_path(coords, scale=1.0, offset_x=0, offset_y=0):
    """Convert LineString coordinates to SVG path string"""
    if not coords or len(coords) < 2:
        return ""

    path_parts = []
    for i, point in enumerate(coords):
        x = point[0] * scale + offset_x
        y = point[1] * scale + offset_y
        if i == 0:
            path_parts.append(f"M {x:.2f} {y:.2f}")
        else:
            path_parts.append(f"L {x:.2f} {y:.2f}")

    return " ".join(path_parts)


def multipoint_to_svg_circles(coords, scale=1.0, offset_x=0, offset_y=0, radius=2):
    """Convert MultiPoint coordinates to SVG circles"""
    if not coords or len(coords) == 0:
        return ""

    circles = []
    for point in coords:
        x = point[0] * scale + offset_x
        y = point[1] * scale + offset_y
        circles.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius}" />')

    return "\n".join(circles)


def calculate_bounds(features):
    """Calculate bounding box of all features"""
    min_x = float("inf")
    min_y = float("inf")
    max_x = float("-inf")
    max_y = float("-inf")

    def update_bounds(coords):
        nonlocal min_x, min_y, max_x, max_y
        if not coords or len(coords) == 0:
            return

        # Check structure and extract points safely
        points_to_process = []

        try:
            if isinstance(coords[0], (int, float)):
                # Single point: [x, y]
                if len(coords) >= 2:
                    points_to_process.append((coords[0], coords[1]))
            elif len(coords) > 0 and isinstance(coords[0], list):
                if len(coords[0]) > 0:
                    if isinstance(coords[0][0], (int, float)):
                        # List of points: [[x, y], [x, y], ...]
                        for point in coords:
                            if point and len(point) >= 2:
                                try:
                                    points_to_process.append((point[0], point[1]))
                                except (IndexError, TypeError):
                                    continue
                    elif isinstance(coords[0][0], list):
                        # Nested list (polygon rings): [[[x, y], ...], [[x, y], ...]]
                        for ring in coords:
                            if ring and len(ring) > 0:
                                for point in ring:
                                    if point and len(point) >= 2:
                                        try:
                                            points_to_process.append(
                                                (point[0], point[1])
                                            )
                                        except (IndexError, TypeError):
                                            continue
        except (IndexError, TypeError):
            return

        # Update bounds
        for x, y in points_to_process:
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)

    for feature in features:
        feat_type = feature.get("type")
        coords = feature.get("coordinates", [])

        if feat_type == "Polygon":
            update_bounds(coords)
        elif feat_type == "LineString":
            update_bounds(coords)
        elif feat_type == "MultiPolygon":
            for polygon in coords:
                if polygon:  # Skip empty polygons
                    for ring in polygon:
                        if ring:  # Skip empty rings
                            update_bounds(ring)
        elif feat_type == "MultiPoint":
            update_bounds(coords)
        elif feat_type == "GeometryCollection":
            for geom in feature.get("geometries", []):
                geom_coords = geom.get("coordinates", [])
                geom_type = geom.get("type")
                if geom_type == "Polygon" and geom_coords:
                    update_bounds(geom_coords)
                elif geom_type == "LineString" and geom_coords:
                    update_bounds(geom_coords)

    return min_x, min_y, max_x, max_y


def visualize_json(json_file, output_file=None, width=1200, height=800, scale=None):
    """Visualize JSON file as SVG"""
    with open(json_file, "r") as f:
        data = json.load(f)

    features = data.get("features", [])
    if len(features) == 0:
        print("No features found in JSON", file=sys.stderr)
        return

    # Calculate bounds (with error handling)
    try:
        min_x, min_y, max_x, max_y = calculate_bounds(features)
    except Exception as e:
        print(f"Error calculating bounds: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return

    # Calculate scale and offset
    if scale is None:
        # Check for valid bounds
        if (
            min_x == float("inf")
            or max_x == float("-inf")
            or min_y == float("inf")
            or max_y == float("-inf")
        ):
            print(
                "Warning: Invalid bounds detected, using default scale", file=sys.stderr
            )
            scale = 1.0
            offset_x = 50
            offset_y = 50
        else:
            scale_x = (width - 100) / (max_x - min_x) if max_x > min_x else 1
            scale_y = (height - 100) / (max_y - min_y) if max_y > min_y else 1
            scale = min(scale_x, scale_y)
            offset_x = -min_x * scale + 50
            offset_y = -min_y * scale + 50
    else:
        offset_x = -min_x * scale + 50 if min_x != float("inf") else 50
        offset_y = -min_y * scale + 50 if min_y != float("inf") else 50

    # SVG header
    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<defs>",
        "  <style>",
        "    .earth { fill: #f0f0f0; stroke: #999; stroke-width: 1; }",
        "    .buildings { fill: #d4a574; stroke: #8b6f47; stroke-width: 0.5; }",
        "    .roads { stroke: #666; stroke-width: 2; fill: none; }",
        "    .planks { stroke: #888; stroke-width: 1.5; fill: none; }",
        "    .walls { fill: #555; stroke: #333; stroke-width: 1; }",
        "    .districts { fill: none; stroke: #999; stroke-width: 0.5; opacity: 0.3; }",
        "    .prisms { fill: #c0c0c0; stroke: #888; stroke-width: 0.5; }",
        "    .squares { fill: #87ceeb; stroke: #4682b4; stroke-width: 0.5; }",
        "    .greens { fill: #90ee90; stroke: #228b22; stroke-width: 0.5; }",
        "    .fields { fill: #deb887; stroke: #8b7355; stroke-width: 0.5; }",
        "    .water { fill: #87ceeb; stroke: #4682b4; stroke-width: 0.5; opacity: 0.5; }",
        "    .trees { fill: #228b22; }",
        "  </style>",
        "</defs>",
        '<rect width="100%" height="100%" fill="white"/>',
    ]

    # Process features in order
    for feature_idx, feature in enumerate(features):
        feat_id = feature.get("id", "")
        feat_type = feature.get("type", "")
        coords = feature.get("coordinates", [])

        # Skip processing if coordinates are empty or invalid
        if not coords and feat_type not in ("GeometryCollection", "Feature"):
            continue

        # Safety check: limit processing to prevent hangs
        try:
            if feat_id == "earth" and feat_type == "Polygon":
                pass
                # path = polygon_to_svg_path(coords, scale, offset_x, offset_y)
                # if path:
                #     svg_parts.append(f'<path class="earth" d="{path}"/>')

            elif feat_id == "buildings" and feat_type == "MultiPolygon":
                for polygon in coords:
                    if polygon and len(polygon) > 0:
                        path = polygon_to_svg_path(polygon, scale, offset_x, offset_y)
                        if path:
                            svg_parts.append(f'<path class="buildings" d="{path}"/>')

            # elif feat_id == "roads" and feat_type == "GeometryCollection":
            #     for geom in feature.get("geometries", []):
            #         if geom.get("type") == "LineString":
            #             path = linestring_to_svg_path(
            #                 geom.get("coordinates", []), scale, offset_x, offset_y
            #             )
            #             if path:
            #                 svg_parts.append(f'<path class="roads" d="{path}"/>')

            # elif feat_id == "planks" and feat_type == "GeometryCollection":
            #     for geom in feature.get("geometries", []):
            #         if geom.get("type") == "LineString":
            #             path = linestring_to_svg_path(
            #                 geom.get("coordinates", []), scale, offset_x, offset_y
            #             )
            #             if path:
            #                 svg_parts.append(f'<path class="planks" d="{path}"/>')

            # elif feat_id == "walls" and feat_type == "GeometryCollection":
            #     for geom in feature.get("geometries", []):
            #         if geom.get("type") == "Polygon":
            #             path = polygon_to_svg_path(
            #                 geom.get("coordinates", []), scale, offset_x, offset_y
            #             )
            #             if path:
            #                 svg_parts.append(f'<path class="walls" d="{path}"/>')

            elif feat_id == "districts" and feat_type == "GeometryCollection":
                # Districts can have many geometries, process efficiently
                for geom in feature.get("geometries", []):
                    if geom.get("type") == "Polygon":
                        geom_coords = geom.get("coordinates", [])
                        if geom_coords:  # Skip empty coordinates
                            path = polygon_to_svg_path(
                                geom_coords, scale, offset_x, offset_y
                            )
                            if path:
                                svg_parts.append(
                                    f'<path class="districts" d="{path}"/>'
                                )

            # elif feat_id == "prisms" and feat_type == "MultiPolygon":
            #     for polygon in coords:
            #         if polygon and len(polygon) > 0:
            #             path = polygon_to_svg_path(polygon, scale, offset_x, offset_y)
            #             if path:
            #                 svg_parts.append(f'<path class="prisms" d="{path}"/>')

            # elif feat_id == "squares" and feat_type == "MultiPolygon":
            #     for polygon in coords:
            #         if polygon and len(polygon) > 0:
            #             path = polygon_to_svg_path(polygon, scale, offset_x, offset_y)
            #             if path:
            #                 svg_parts.append(f'<path class="squares" d="{path}"/>')

            elif feat_id == "greens" and feat_type == "MultiPolygon":
                for polygon in coords:
                    if polygon and len(polygon) > 0:
                        path = polygon_to_svg_path(polygon, scale, offset_x, offset_y)
                        if path:
                            svg_parts.append(f'<path class="greens" d="{path}"/>')

            # elif feat_id == "fields" and feat_type == "MultiPolygon":
            #     for polygon in coords:
            #         if polygon and len(polygon) > 0:
            #             path = polygon_to_svg_path(polygon, scale, offset_x, offset_y)
            #             if path:
            #                 svg_parts.append(f'<path class="fields" d="{path}"/>')

            elif feat_id == "water" and feat_type == "MultiPolygon":
                for polygon in coords:
                    if polygon and len(polygon) > 0:
                        path = polygon_to_svg_path(polygon, scale, offset_x, offset_y)
                        if path:
                            svg_parts.append(f'<path class="water" d="{path}"/>')

            elif feat_id == "trees" and feat_type == "MultiPoint":
                circles = multipoint_to_svg_circles(
                    coords, scale, offset_x, offset_y, radius=1
                )
                if circles:
                    svg_parts.append(f'<g class="trees">{circles}</g>')

        except Exception as e:
            print(
                f"Warning: Error processing feature {feat_id} ({feat_type}): {e}",
                file=sys.stderr,
            )
            continue

    svg_parts.append("</svg>")

    # Join SVG parts efficiently
    try:
        svg_content = "\n".join(svg_parts)
    except Exception as e:
        print(f"Error creating SVG content: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return

    if output_file:
        try:
            with open(output_file, "w") as f:
                f.write(svg_content)
            print(f"SVG saved to {output_file}", file=sys.stderr)
        except Exception as e:
            print(f"Error writing SVG file: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc()
    else:
        try:
            print(svg_content)
        except Exception as e:
            print(f"Error printing SVG: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(description="Visualize Town Generator JSON as SVG")
    parser.add_argument("input", help="Input JSON file")
    parser.add_argument(
        "-o", "--output", help="Output SVG file (default: print to stdout)"
    )
    parser.add_argument(
        "-w", "--width", type=int, default=1200, help="SVG width (default: 1200)"
    )
    parser.add_argument(
        "--height", type=int, default=800, help="SVG height (default: 800)"
    )
    parser.add_argument(
        "-s",
        "--scale",
        type=float,
        default=None,
        help="Scale factor (auto if not specified)",
    )

    args = parser.parse_args()

    visualize_json(args.input, args.output, args.width, args.height, args.scale)


if __name__ == "__main__":
    main()
