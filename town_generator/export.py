"""
JSON export functionality - GeoJSON FeatureCollection format
"""

import json
from pathlib import Path
from .model import Model
from .ward import Market, Park, Farm


def _get_version():
    """Get version from pyproject.toml"""
    try:
        # Try tomllib (Python 3.11+)
        import tomllib

        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            pyproject = tomllib.load(f)
            return pyproject.get("project", {}).get("version", "0.1.0")
    except ImportError:
        # Fallback for Python < 3.11: try tomli package
        try:
            import tomli

            pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
            with open(pyproject_path, "rb") as f:
                pyproject = tomli.load(f)
                return pyproject.get("project", {}).get("version", "0.1.0")
        except Exception:
            # Final fallback: parse manually
            pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
            if pyproject_path.exists():
                with open(pyproject_path, "r") as f:
                    for line in f:
                        if line.strip().startswith("version"):
                            # Extract version from line like: version = "0.1.0"
                            parts = line.split("=")
                            if len(parts) == 2:
                                version = parts[1].strip().strip('"').strip("'")
                                return version
            return "0.1.0"
    except Exception:
        return "0.1.0"


def polygon_to_coordinates(polygon):
    """Convert polygon to GeoJSON coordinates format"""
    if not polygon or len(polygon.vertices) == 0:
        return []
    coords = [[v.x, v.y] for v in polygon.vertices]
    # Don't force close - match ref.json format
    return [coords]


def linestring_to_coordinates(polygon):
    """Convert polygon (as LineString) to GeoJSON coordinates format"""
    if not polygon or len(polygon.vertices) < 2:
        return []
    return [[v.x, v.y] for v in polygon.vertices]


def export_to_json(model, filename=None, indent=2):
    """
    Export model to GeoJSON FeatureCollection format matching ref.json

    Args:
        model: Model instance to export
        filename: Optional filename to save to. If None, returns JSON string
        indent: JSON indentation (default 2)

    Returns:
        JSON string if filename is None, otherwise None
    """
    features = []

    # 1. Values feature (metadata)
    features.append(
        {
            "type": "Feature",
            "id": "values",
            "roadWidth": 8,
            "towerRadius": 7.6,
            "wallThickness": 7.6,
            "generator": "mfcg-python",
            "version": _get_version(),
        }
    )

    # 2. Earth polygon (outer boundary of all original patches)
    # Use all_patches if available, otherwise fall back to patches
    all_patches = getattr(model, "all_patches", None) or model.patches
    earth_polygon = model.find_circumference(all_patches)
    if earth_polygon and len(earth_polygon.vertices) > 0:
        features.append(
            {
                "type": "Polygon",
                "id": "earth",
                "coordinates": polygon_to_coordinates(earth_polygon),
            }
        )

    # 3. Roads GeometryCollection (LineString, width: 8)
    road_geometries = []
    for road in model.roads:
        coords = linestring_to_coordinates(road)
        if len(coords) >= 2:
            road_geometries.append(
                {"type": "LineString", "width": 8, "coordinates": coords}
            )

    features.append(
        {"type": "GeometryCollection", "id": "roads", "geometries": road_geometries}
    )

    # 4. Walls GeometryCollection (Polygon, width: 7.6)
    wall_geometries = []
    if model.wall and model.wall.shape:
        coords = polygon_to_coordinates(model.wall.shape)
        if coords:
            wall_geometries.append(
                {"type": "Polygon", "width": 7.6, "coordinates": coords}
            )

    # Citadel wall
    if model.citadel and model.citadel.ward and hasattr(model.citadel.ward, "wall"):
        citadel_wall = model.citadel.ward.wall
        if citadel_wall and citadel_wall.shape:
            coords = polygon_to_coordinates(citadel_wall.shape)
            if coords:
                wall_geometries.append(
                    {"type": "Polygon", "width": 7.6, "coordinates": coords}
                )

    features.append(
        {"type": "GeometryCollection", "id": "walls", "geometries": wall_geometries}
    )

    # 5. Rivers GeometryCollection (empty)
    features.append({"type": "GeometryCollection", "id": "rivers", "geometries": []})

    # 6. Planks GeometryCollection (LineString, width: 4.8)
    # Planks are typically smaller paths - using streets for now
    plank_geometries = []
    for street in model.streets:
        coords = linestring_to_coordinates(street)
        if len(coords) >= 2:
            plank_geometries.append(
                {"type": "LineString", "width": 4.8, "coordinates": coords}
            )

    features.append(
        {"type": "GeometryCollection", "id": "planks", "geometries": plank_geometries}
    )

    # 7. Buildings MultiPolygon (all ward geometry except Market, Park, Farm)
    building_polygons = []
    for patch in model.patches:
        if patch.ward and hasattr(patch.ward, "geometry"):
            ward_type = type(patch.ward).__name__
            # Exclude Market, Park, Farm - they go to separate categories
            if ward_type not in ["Market", "Park", "Farm"]:
                for geom in patch.ward.geometry:
                    coords = polygon_to_coordinates(geom)
                    if coords:
                        building_polygons.append(coords)

    features.append(
        {
            "type": "MultiPolygon",
            "id": "buildings",
            "coordinates": building_polygons if building_polygons else [],
        }
    )

    # 8. Prisms MultiPolygon (Market statues - rect shapes)
    prism_polygons = []
    for patch in model.patches:
        if patch.ward and isinstance(patch.ward, Market):
            if hasattr(patch.ward, "geometry") and patch.ward.geometry:
                # Check if it's a rect (statue) - simplified check
                # In Market, statue is rect, fountain is circle
                # We'll use geometry[0] and check if it's likely a rect
                for geom in patch.ward.geometry:
                    # If it has 4 vertices and is roughly rectangular, it's a statue
                    if len(geom.vertices) == 4:
                        coords = polygon_to_coordinates(geom)
                        if coords:
                            prism_polygons.append(coords)

    features.append(
        {
            "type": "MultiPolygon",
            "id": "prisms",
            "coordinates": prism_polygons if prism_polygons else [],
        }
    )

    # 9. Squares MultiPolygon (Market fountains - circle shapes)
    square_polygons = []
    for patch in model.patches:
        if patch.ward and isinstance(patch.ward, Market):
            if hasattr(patch.ward, "geometry") and patch.ward.geometry:
                for geom in patch.ward.geometry:
                    # If it has more than 4 vertices, it's likely a circle (fountain)
                    if len(geom.vertices) > 4:
                        coords = polygon_to_coordinates(geom)
                        if coords:
                            square_polygons.append(coords)

    features.append(
        {
            "type": "MultiPolygon",
            "id": "squares",
            "coordinates": square_polygons if square_polygons else [],
        }
    )

    # 10. Greens MultiPolygon (Park groves)
    green_polygons = []
    for patch in model.patches:
        if patch.ward and isinstance(patch.ward, Park):
            if hasattr(patch.ward, "geometry") and patch.ward.geometry:
                for geom in patch.ward.geometry:
                    coords = polygon_to_coordinates(geom)
                    if coords:
                        green_polygons.append(coords)

    features.append(
        {
            "type": "MultiPolygon",
            "id": "greens",
            "coordinates": green_polygons if green_polygons else [],
        }
    )

    # 11. Fields MultiPolygon (Farm buildings)
    field_polygons = []
    for patch in model.patches:
        if patch.ward and isinstance(patch.ward, Farm):
            if hasattr(patch.ward, "geometry") and patch.ward.geometry:
                for geom in patch.ward.geometry:
                    coords = polygon_to_coordinates(geom)
                    if coords:
                        field_polygons.append(coords)

    features.append(
        {
            "type": "MultiPolygon",
            "id": "fields",
            "coordinates": field_polygons if field_polygons else [],
        }
    )

    # 12. Trees MultiPoint (empty for now)
    features.append({"type": "MultiPoint", "id": "trees", "coordinates": []})

    # 13. Districts GeometryCollection (all patches with names)
    district_geometries = []
    for patch in model.patches:
        if patch.ward:
            label = patch.ward.get_label()
            if label:
                coords = polygon_to_coordinates(patch.shape)
                if coords:
                    district_geometries.append(
                        {"type": "Polygon", "name": label, "coordinates": coords}
                    )

    features.append(
        {
            "type": "GeometryCollection",
            "id": "districts",
            "geometries": district_geometries,
        }
    )

    # 14. Water MultiPolygon (waterbody patches)
    water_polygons = []
    for patch in model.patches:
        # Water patches are those without wards or marked as waterbody
        if patch in model.waterbody or (patch.ward is None and not patch.within_city):
            coords = polygon_to_coordinates(patch.shape)
            if coords:
                water_polygons.append(coords)

    features.append(
        {
            "type": "MultiPolygon",
            "id": "water",
            "coordinates": water_polygons if water_polygons else [],
        }
    )

    # Create FeatureCollection
    feature_collection = {"type": "FeatureCollection", "features": features}

    json_str = json.dumps(feature_collection, indent=indent, default=str)

    if filename:
        with open(filename, "w") as f:
            f.write(json_str)
        return None
    else:
        return json_str


def generate_and_export(n_patches=15, seed=-1, filename=None, indent=2):
    """
    Generate a city and export to JSON

    Args:
        n_patches: Number of patches (city size)
        seed: Random seed (-1 for random)
        filename: Optional filename to save to
        indent: JSON indentation

    Returns:
        Model instance and JSON string (if filename is None)
    """
    model = Model(n_patches, seed)
    json_str = export_to_json(model, filename, indent)

    if filename:
        return model
    else:
        return model, json_str
