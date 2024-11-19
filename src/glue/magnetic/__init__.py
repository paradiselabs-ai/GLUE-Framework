# src/glue/magnetic/__init__.py

from .field import MagneticField, MagneticResource
from .rules import AttractionRule, AttractionStrength

__all__ = [
    'MagneticField',
    'MagneticResource',
    'AttractionRule',
    'AttractionStrength'
]
