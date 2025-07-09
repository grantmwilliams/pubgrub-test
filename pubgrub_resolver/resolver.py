"""
Main PubGrub resolver algorithm implementation.
"""

from __future__ import annotations

from typing import NamedTuple
from .package import Package
from .version import Version, VersionRange
from .term import Term
from .partial_solution import PartialSolution
from .incompatibility import (
    Incompatibility,
    IncompatibilityKind,
    IncompatibilitySet,
    create_no_versions_incompatibility,
    create_dependency_incompatibility,
)
from .dependency_provider import DependencyProvider
from .conflict_resolver import ConflictResolver, ConflictExplainer


class ResolutionResult(NamedTuple):
    """Result of dependency resolution."""

    success: bool
    solution: PartialSolution | None
    error: str | None


class PubGrubResolver:
    """
    Main PubGrub resolver implementing the version resolution algorithm.

    This resolver uses a SAT-based approach with unit propagation,
    conflict learning, and backtracking to solve dependency constraints.
    """

    def __init__(self, provider: DependencyProvider) -> None:
        self.provider = provider
        self.incompatibilities = IncompatibilitySet()
        self.solution = PartialSolution()
        self.root_package: Package | None = None
        self.conflict_resolver = ConflictResolver()
        self.explainer = ConflictExplainer()

    def resolve(self, root_package: Package, root_version: Version) -> ResolutionResult:
        """
        Resolve dependencies starting from a root package.

        Returns a ResolutionResult containing the solution or error information.
        """
        try:
            self.root_package = root_package
            self.solution = PartialSolution()
            self.incompatibilities = IncompatibilitySet()
            self.conflict_resolver = ConflictResolver()
            self.explainer = ConflictExplainer()

            # Add root constraint
            self._add_root_constraint(root_package, root_version)

            # Main resolution loop
            while True:
                # Unit propagation
                propagation_result = self._unit_propagation()
                if not propagation_result.success:
                    return ResolutionResult(False, None, propagation_result.error)

                # Check if we have a complete solution
                if self._is_complete_solution():
                    return ResolutionResult(True, self.solution, None)

                # Make a decision
                decision_result = self._make_decision()
                if not decision_result.success:
                    return ResolutionResult(False, None, decision_result.error)

        except Exception as e:
            return ResolutionResult(False, None, f"Resolver error: {str(e)}")

    def _add_root_constraint(
        self, root_package: Package, root_version: Version
    ) -> None:
        """Add the root package constraint."""
        # Assign root package directly (no incompatibility needed)
        self.solution.assign(root_package, root_version, 0)

        # Add dependencies for root package
        self._add_package_dependencies(root_package, root_version)

    def _unit_propagation(self) -> ResolutionResult:
        """
        Perform unit propagation to derive new assignments.

        Returns success/failure and any error message.
        """
        changed = True
        while changed:
            changed = False

            # Check for failure incompatibilities first
            for incompatibility in self.incompatibilities.get_all():
                if incompatibility.is_failure():
                    return ResolutionResult(False, None, incompatibility.cause)

            # Find unit clauses
            unit_clauses = self.incompatibilities.find_unit_clauses(self.solution)

            for unit_clause in unit_clauses:
                # Check if this creates a conflict
                if self._creates_conflict(unit_clause):
                    # Use conflict-driven clause learning (CDCL)
                    conflict_analysis = self.conflict_resolver.analyze_conflict(
                        unit_clause, self.solution, self.incompatibilities.get_all()
                    )

                    if conflict_analysis.backtrack_level < 0:
                        return ResolutionResult(
                            False, None, conflict_analysis.explanation
                        )

                    # Add learned clause to prevent same conflict
                    if conflict_analysis.learned_clause:
                        self.incompatibilities.add(conflict_analysis.learned_clause)

                    # Non-chronological backtracking
                    self.solution.backtrack(conflict_analysis.backtrack_level)
                    changed = True
                    break
                else:
                    # Apply unit clause
                    success = self._apply_unit_clause(unit_clause)
                    if not success:
                        # Unit clause application failed - this is a conflict
                        conflict_analysis = self.conflict_resolver.analyze_conflict(
                            unit_clause, self.solution, self.incompatibilities.get_all()
                        )

                        if conflict_analysis.backtrack_level < 0:
                            return ResolutionResult(
                                False, None, conflict_analysis.explanation
                            )

                        # Add learned clause to prevent same conflict
                        if conflict_analysis.learned_clause:
                            self.incompatibilities.add(conflict_analysis.learned_clause)

                        # Non-chronological backtracking
                        self.solution.backtrack(conflict_analysis.backtrack_level)
                        changed = True
                        break
                    changed = True

        return ResolutionResult(True, self.solution, None)

    def _creates_conflict(self, unit_clause: Term) -> bool:
        """Check if applying a unit clause would create a conflict."""
        # Check if package is already assigned incompatibly
        assignment = self.solution.get_assignment(unit_clause.package)
        if assignment is not None:
            # Check if assigned version conflicts with unit clause
            return (
                not unit_clause.version_range.contains(assignment.version)
                == unit_clause.positive
            )

        # Check if unit clause conflicts with other constraints
        for incompatibility in self.incompatibilities.get_for_package(
            unit_clause.package
        ):
            term = incompatibility.get_term_for_package(unit_clause.package)
            if term is not None:
                # Check if terms conflict
                intersection = unit_clause.intersect(term)
                if intersection is None or intersection.is_failure():
                    return True

        return False

    def _apply_unit_clause(self, unit_clause: Term) -> bool:
        """Apply a unit clause by making an assignment. Returns True if successful, False if conflict."""
        if unit_clause.positive:
            # Positive term: assign a version from the range
            compatible_versions = self.provider.get_compatible_versions(
                unit_clause.package, unit_clause
            )
            if not compatible_versions:
                # No compatible versions available - this is a conflict
                return False

            # Filter versions that would create future conflicts
            conflict_free_versions = []
            for version in compatible_versions:
                if self._is_version_compatible(unit_clause.package, version):
                    conflict_free_versions.append(version)

            if conflict_free_versions:
                # Choose the latest conflict-free version
                chosen_version = max(conflict_free_versions)
            else:
                # Choose the latest compatible version as fallback
                chosen_version = max(compatible_versions)

            self.solution.assign(
                unit_clause.package, chosen_version, self.solution.decision_level
            )

            # Add dependencies for this assignment
            self._add_package_dependencies(unit_clause.package, chosen_version)
        else:
            # Negative term: add incompatibility for excluded versions
            excluded_versions = self.provider.get_compatible_versions(
                unit_clause.package, unit_clause.negate()
            )
            for version in excluded_versions:
                # Create incompatibility for this version
                exact_range = VersionRange(version, version, True, True)
                excluded_term = Term(unit_clause.package, exact_range, True)
                incompatibility = Incompatibility(
                    [excluded_term],
                    IncompatibilityKind.CONFLICT,
                    f"version {version} excluded by constraint",
                )
                self.incompatibilities.add(incompatibility)

        return True

    def _add_package_dependencies(self, package: Package, version: Version) -> None:
        """Add incompatibilities for a package's dependencies."""
        dependencies = self.provider.get_dependencies(package, version)

        for dependency in dependencies:
            # Special case: check for impossible self-dependencies before creating incompatibility
            if dependency.package == package:
                if not dependency.version_range.contains(version):
                    # Self-dependency is impossible - this should fail immediately
                    from .incompatibility import Incompatibility, IncompatibilityKind

                    failure_incompatibility = Incompatibility(
                        [],
                        IncompatibilityKind.CONFLICT,
                        f"{package.name}@{version} has unsatisfiable self-dependency on {dependency.version_range}",
                    )
                    self.incompatibilities.add(failure_incompatibility)
                    return

            # Create dependency incompatibility
            dependency_term = Term(dependency.package, dependency.version_range, True)
            incompatibility = create_dependency_incompatibility(
                package, version, dependency_term
            )
            self.incompatibilities.add(incompatibility)

    def _is_complete_solution(self) -> bool:
        """Check if we have a complete solution."""
        # A solution is complete if:
        # 1. Root package is assigned
        # 2. No unit clauses can be derived (stable state)
        # 3. No unassigned packages have pending dependencies

        if self.root_package is None or not self.solution.is_assigned(
            self.root_package
        ):
            return False

        # Check if we can derive any unit clauses
        unit_clauses = self.incompatibilities.find_unit_clauses(self.solution)
        if unit_clauses:
            return False  # Still have work to do

        # For now, we'll consider it complete if no unit clauses can be derived
        # A more sophisticated implementation would check all transitive dependencies
        return True

    def _make_decision(self) -> ResolutionResult:
        """
        Make a decision to advance the resolution.

        This chooses a package and version to assign next.
        """
        # Find an unassigned package
        unassigned_packages = self._find_unassigned_packages()

        if not unassigned_packages:
            return ResolutionResult(True, self.solution, None)

        # Choose the first unassigned package (heuristic could be improved)
        package = unassigned_packages[0]

        # Get available versions
        available_versions = self.provider.get_package_versions(package)
        if not available_versions:
            # No versions available
            no_versions_incompatibility = create_no_versions_incompatibility(package)
            self.incompatibilities.add(no_versions_incompatibility)
            return ResolutionResult(
                False, None, f"No versions available for {package.name}"
            )

        # Filter versions based on existing constraints
        compatible_versions = []
        for version in available_versions:
            # Check if this version would conflict with existing constraints
            if self._is_version_compatible(package, version):
                compatible_versions.append(version)

        if not compatible_versions:
            return ResolutionResult(
                False, None, f"No compatible versions for {package.name}"
            )

        # Choose the latest compatible version
        chosen_version = max(compatible_versions)

        # Increment decision level and assign
        self.solution.increment_decision_level()
        self.solution.assign(package, chosen_version, self.solution.decision_level)

        # Add dependencies for this assignment
        self._add_package_dependencies(package, chosen_version)

        return ResolutionResult(True, self.solution, None)

    def _is_version_compatible(self, package: Package, version: Version) -> bool:
        """Check if a version is compatible with existing constraints."""
        # Check all incompatibilities involving this package
        for incompatibility in self.incompatibilities.get_for_package(package):
            term = incompatibility.get_term_for_package(package)
            if term is not None:
                # Check if this version would violate the term
                if term.positive and not term.version_range.contains(version):
                    return False
                elif not term.positive and term.version_range.contains(version):
                    return False

        # Also check if this version would create future conflicts
        return not self._would_create_future_conflicts(package, version)

    def _would_create_future_conflicts(
        self, package: Package, version: Version
    ) -> bool:
        """Check if choosing this version would create future conflicts."""
        # Get dependencies for this version
        dependencies = self.provider.get_dependencies(package, version)

        # Check if any dependency would conflict with existing constraints
        for dependency in dependencies:
            dep_package = dependency.package
            dep_range = dependency.version_range

            # Special case: self-dependency
            if dep_package == package:
                # If package depends on itself, check if the chosen version satisfies the dependency
                if not dep_range.contains(version):
                    return True  # Would create conflict - package version doesn't satisfy its own dependency

            # Check if this dependency conflicts with existing constraints for the same package
            for incompatibility in self.incompatibilities.get_for_package(dep_package):
                dep_term = incompatibility.get_term_for_package(dep_package)
                if dep_term is not None:
                    # Check if the dependency range conflicts with the existing constraint
                    if dep_term.positive:
                        # Both positive - check if ranges intersect
                        intersection = dep_range.intersect(dep_term.version_range)
                        if intersection is None or intersection.is_empty():
                            return False  # Would create conflict
                    else:
                        # dep_term is negative - check if dependency range overlaps with excluded range
                        intersection = dep_range.intersect(dep_term.version_range)
                        if intersection is not None and not intersection.is_empty():
                            return False  # Would create conflict

        # Check if choosing this version would prevent other packages from being satisfied
        # This is critical for the conflict avoidance scenario
        for incompatibility in self.incompatibilities.get_all():
            for term in incompatibility.terms:
                if term.package == package:
                    continue  # Skip the package we're considering

                # Check if this term requires a specific version of another package
                # and if choosing our version would prevent that
                if term.positive:
                    # Find all versions of the other package that satisfy the constraint
                    other_package = term.package
                    compatible_versions = self.provider.get_package_versions(
                        other_package
                    )
                    satisfying_versions = [
                        v for v in compatible_versions if term.version_range.contains(v)
                    ]

                    # Check if any of these versions would have dependencies that conflict
                    # with our choice
                    for other_version in satisfying_versions:
                        other_deps = self.provider.get_dependencies(
                            other_package, other_version
                        )
                        for other_dep in other_deps:
                            if other_dep.package == package:
                                # This other version depends on our package
                                if not other_dep.version_range.contains(version):
                                    # Our version doesn't satisfy the other package's dependency
                                    # Check if we have no choice but to pick this version
                                    our_constraint = None
                                    for (
                                        our_incomp
                                    ) in self.incompatibilities.get_for_package(
                                        package
                                    ):
                                        our_term = our_incomp.get_term_for_package(
                                            package
                                        )
                                        if our_term and our_term.positive:
                                            our_constraint = our_term.version_range
                                            break

                                    if our_constraint:
                                        # Check if there are other versions of our package that would work
                                        our_versions = (
                                            self.provider.get_package_versions(package)
                                        )
                                        compatible_our_versions = [
                                            v
                                            for v in our_versions
                                            if our_constraint.contains(v)
                                            and other_dep.version_range.contains(v)
                                        ]
                                        if not compatible_our_versions:
                                            return False  # Would create future conflict

        return True

    def _find_unassigned_packages(self) -> list[Package]:
        """Find packages mentioned in incompatibilities but not yet assigned."""
        mentioned_packages = set()
        for incompatibility in self.incompatibilities.get_all():
            mentioned_packages.update(incompatibility.get_packages())

        unassigned = []
        for package in mentioned_packages:
            if not self.solution.is_assigned(package):
                unassigned.append(package)

        return unassigned

    def get_solution_dict(self) -> dict[str, str]:
        """Get the solution as a dictionary of package names to versions."""
        result = {}
        for assignment in self.solution.get_all_assignments():
            result[assignment.package.name] = str(assignment.version)
        return result

    def get_resolution_statistics(self) -> dict[str, int]:
        """Get statistics about the resolution process."""
        stats = self.conflict_resolver.get_conflict_statistics()
        stats.update(
            {
                "total_incompatibilities": len(self.incompatibilities),
                "total_assignments": len(self.solution.get_all_assignments()),
                "final_decision_level": self.solution.decision_level,
            }
        )
        return stats

    def __str__(self) -> str:
        return f"PubGrubResolver(provider={self.provider})"

    def __repr__(self) -> str:
        return f"PubGrubResolver({self.provider!r})"


def solve_dependencies(
    provider: DependencyProvider, root_package: Package, root_version: Version
) -> ResolutionResult:
    """
    Convenience function to solve dependencies with PubGrub.

    Args:
        provider: DependencyProvider to get package information
        root_package: Root package to start resolution from
        root_version: Version of the root package

    Returns:
        ResolutionResult with solution or error information
    """
    resolver = PubGrubResolver(provider)
    return resolver.resolve(root_package, root_version)
