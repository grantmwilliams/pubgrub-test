"""
PubGrub version resolution algorithm implementation.

This package provides a Python implementation of the PubGrub algorithm,
a next-generation version solving algorithm for dependency resolution.
"""

from .version import Version, VersionRange, VersionSet
from .package import Package
from .term import Term
from .partial_solution import PartialSolution, Assignment
from .incompatibility import Incompatibility, IncompatibilityKind
from .dependency_provider import DependencyProvider, SimpleDependencyProvider
from .resolver import PubGrubResolver, solve_dependencies

__version__ = "0.1.0"
__all__ = [
    "Version",
    "VersionRange",
    "VersionSet",
    "Package",
    "Term",
    "PartialSolution",
    "Assignment",
    "Incompatibility",
    "IncompatibilityKind",
    "DependencyProvider",
    "SimpleDependencyProvider",
    "PubGrubResolver",
    "solve_dependencies",
]
