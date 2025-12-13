"""
JSON export functionality
"""
import json
from .model import Model


def export_to_json(model, filename=None, indent=2):
    """
    Export model to JSON format
    
    Args:
        model: Model instance to export
        filename: Optional filename to save to. If None, returns JSON string
        indent: JSON indentation (default 2)
    
    Returns:
        JSON string if filename is None, otherwise None
    """
    data = model.to_dict()
    json_str = json.dumps(data, indent=indent, default=str)
    
    if filename:
        with open(filename, 'w') as f:
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
