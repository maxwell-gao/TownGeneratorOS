"""
Medieval Fantasy City Generator - Python Port
Only includes core generation logic and JSON export functionality.
"""

__version__ = "1.0.0"

# Core classes
from .model import Model
from .patch import Patch
from .polygon import Polygon
from .point import Point
from .voronoi import Voronoi
from .curtain_wall import CurtainWall
from .topology import Topology
from .random import Random

# Ward types
from .ward import (
    Ward,
    CommonWard,
    CraftsmenWard,
    MerchantWard,
    Slum,
    Market,
    Castle,
    GateWard,
    AdministrationWard,
    MilitaryWard,
    PatriciateWard,
    Park,
    Cathedral,
    Farm,
)

# Debug visualization
from .step_visualizer import StepVisualizer

__all__ = [
    # Core
    'Model',
    'Patch',
    'Polygon',
    'Point',
    'Voronoi',
    'CurtainWall',
    'Topology',
    'Random',
    # Wards
    'Ward',
    'CommonWard',
    'CraftsmenWard',
    'MerchantWard',
    'Slum',
    'Market',
    'Castle',
    'GateWard',
    'AdministrationWard',
    'MilitaryWard',
    'PatriciateWard',
    'Park',
    'Cathedral',
    'Farm',
    # Debug
    'StepVisualizer',
]
