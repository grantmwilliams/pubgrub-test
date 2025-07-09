"""
PartialSolution class for tracking the current state during PubGrub resolution.
"""

from __future__ import annotations

from .package import Package
from .version import Version, VersionRange
from .term import Term


class Assignment:
    """Represents an assignment of a package to a specific version."""

    def __init__(self, package: Package, version: Version, decision_level: int) -> None:
        self.package = package
        self.version = version
        self.decision_level = decision_level

    def __str__(self) -> str:
        return f"{self.package.name}@{self.version}"

    def __repr__(self) -> str:
        return f"Assignment({self.package!r}, {self.version!r}, {self.decision_level})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Assignment):
            return NotImplemented
        return (
            self.package == other.package
            and self.version == other.version
            and self.decision_level == other.decision_level
        )

    def __hash__(self) -> int:
        return hash((self.package, self.version, self.decision_level))


class PartialSolution:
    """
    Tracks the current state of package assignments during PubGrub resolution.

    This class maintains:
    - Current package assignments
    - Decision levels for backtracking
    - Derived constraints from assignments
    """

    def __init__(self) -> None:
        self.assignments: dict[Package, Assignment] = {}
        self.decision_level: int = 0

    def assign(
        self, package: Package, version: Version, decision_level: int | None = None
    ) -> None:
        """Assign a package to a specific version."""
        if decision_level is None:
            decision_level = self.decision_level

        assignment = Assignment(package, version, decision_level)
        self.assignments[package] = assignment

    def get_assignment(self, package: Package) -> Assignment | None:
        """Get the current assignment for a package."""
        return self.assignments.get(package)

    def get_version(self, package: Package) -> Version | None:
        """Get the assigned version for a package."""
        assignment = self.get_assignment(package)
        return assignment.version if assignment else None

    def is_assigned(self, package: Package) -> bool:
        """Check if a package is assigned."""
        return package in self.assignments

    def satisfies(self, term: Term) -> bool:
        """Check if the current partial solution satisfies a term."""
        assignment = self.get_assignment(term.package)
        if assignment is None:
            # Package not assigned - can't satisfy positive terms
            return not term.positive

        # Check if assigned version satisfies the term
        version_satisfies = term.version_range.contains(assignment.version)
        return version_satisfies == term.positive

    def get_constraint(self, package: Package) -> Term | None:
        """Get the current constraint for a package based on assignments."""
        assignment = self.get_assignment(package)
        if assignment is None:
            return None

        # Create a positive term for the exact assigned version
        exact_range = VersionRange(assignment.version, assignment.version, True, True)
        return Term(package, exact_range, True)

    def backtrack(self, target_level: int) -> None:
        """Backtrack to a specific decision level."""
        # Remove all assignments made at levels higher than target_level
        to_remove = []
        for package, assignment in self.assignments.items():
            if assignment.decision_level > target_level:
                to_remove.append(package)

        for package in to_remove:
            del self.assignments[package]

        self.decision_level = target_level

    def increment_decision_level(self) -> None:
        """Increment the decision level (for making new decisions)."""
        self.decision_level += 1

    def get_packages_at_level(self, level: int) -> list[Package]:
        """Get all packages assigned at a specific decision level."""
        return [
            pkg
            for pkg, assignment in self.assignments.items()
            if assignment.decision_level == level
        ]

    def get_all_packages(self) -> list[Package]:
        """Get all assigned packages."""
        return list(self.assignments.keys())

    def get_all_assignments(self) -> list[Assignment]:
        """Get all current assignments."""
        return list(self.assignments.values())

    def copy(self) -> PartialSolution:
        """Create a copy of this partial solution."""
        copy_solution = PartialSolution()
        copy_solution.assignments = self.assignments.copy()
        copy_solution.decision_level = self.decision_level
        return copy_solution

    def is_complete(self, required_packages: set[Package]) -> bool:
        """Check if all required packages are assigned."""
        return all(pkg in self.assignments for pkg in required_packages)

    def __str__(self) -> str:
        if not self.assignments:
            return "{}"

        assignments_str = ", ".join(
            str(assignment) for assignment in self.assignments.values()
        )
        return f"{{{assignments_str}}}"

    def __repr__(self) -> str:
        return f"PartialSolution({self.assignments!r}, decision_level={self.decision_level})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PartialSolution):
            return NotImplemented
        return (
            self.assignments == other.assignments
            and self.decision_level == other.decision_level
        )

    def __hash__(self) -> int:
        return hash((tuple(sorted(self.assignments.items())), self.decision_level))


class DecisionTracker:
    """Tracks decisions made during resolution for backtracking."""

    def __init__(self) -> None:
        self.decisions: list[tuple[Package, Version, int]] = []

    def add_decision(
        self, package: Package, version: Version, decision_level: int
    ) -> None:
        """Record a decision made at a specific level."""
        self.decisions.append((package, version, decision_level))

    def get_decisions_at_level(self, level: int) -> list[tuple[Package, Version]]:
        """Get all decisions made at a specific level."""
        return [(pkg, ver) for pkg, ver, lvl in self.decisions if lvl == level]

    def remove_decisions_above_level(self, level: int) -> None:
        """Remove all decisions made above a specific level."""
        self.decisions = [
            (pkg, ver, lvl) for pkg, ver, lvl in self.decisions if lvl <= level
        ]

    def get_latest_decision_level(self) -> int:
        """Get the latest decision level."""
        return max((lvl for _, _, lvl in self.decisions), default=0)

    def is_empty(self) -> bool:
        """Check if no decisions have been made."""
        return len(self.decisions) == 0

    def __str__(self) -> str:
        return f"DecisionTracker({len(self.decisions)} decisions)"

    def __repr__(self) -> str:
        return f"DecisionTracker({self.decisions!r})"
