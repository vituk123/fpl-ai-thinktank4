"""
FPL Optimizer - Autonomous FPL analysis and optimization.
"""

__version__ = '1.0.0'
__author__ = 'FPL Optimizer Team'

from .fpl_api import FPLAPIClient
from .projections import ProjectionEngine
from .eo import EOCalculator
from .optimizer import TransferOptimizer
from .chips import ChipEvaluator
from .report import ReportGenerator

__all__ = [
    'FPLAPIClient',
    'ProjectionEngine',
    'EOCalculator',
    'TransferOptimizer',
    'ChipEvaluator',
    'ReportGenerator',
]

