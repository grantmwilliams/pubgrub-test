"""
Conflict resolution and backtracking logic for PubGrub.
"""

from __future__ import annotations

from typing import NamedTuple
from .package import Package
from .version import Version
from .term import Term
from .incompatibility import Incompatibility, IncompatibilityKind
from .partial_solution import PartialSolution


class ConflictAnalysis(NamedTuple):
    """Result of conflict analysis."""

    learned_clause: Incompatibility | None
    backtrack_level: int
    explanation: str


class ConflictCause(NamedTuple):
    """Represents the cause of a conflict."""

    conflicting_incompatibilities: list[Incompatibility]
    decision_level: int
    explanation: str


class ConflictResolver:
    """
    Handles conflict resolution and backtracking in PubGrub.

    This implements sophisticated conflict analysis similar to modern SAT solvers,
    with conflict learning and intelligent backtracking.
    """

    def __init__(self) -> None:
        self.conflict_history: list[ConflictCause] = []
        self.learned_clauses: list[Incompatibility] = []

    def analyze_conflict(
        self,
        conflicting_term: Term,
        solution: PartialSolution,
        incompatibilities: list[Incompatibility],
    ) -> ConflictAnalysis:
        """
        Analyze a conflict to determine the learned clause and backtrack level.

        This uses a simplified version of conflict-driven clause learning (CDCL).
        """
        current_level = solution.decision_level

        # Find all incompatibilities that led to this conflict
        relevant_incompatibilities = self._find_relevant_incompatibilities(
            conflicting_term, solution, incompatibilities
        )

        if not relevant_incompatibilities:
            # No specific incompatibilities found - this is a root conflict
            return ConflictAnalysis(
                learned_clause=None,
                backtrack_level=-1,  # Indicate unsolvable
                explanation="Root conflict - no solution exists",
            )

        # Analyze the conflict chain
        learned_clause = self._derive_learned_clause(
            relevant_incompatibilities, solution
        )
        backtrack_level = self._calculate_backtrack_level(
            relevant_incompatibilities, solution
        )

        # Record this conflict
        conflict_cause = ConflictCause(
            conflicting_incompatibilities=relevant_incompatibilities,
            decision_level=current_level,
            explanation=f"Conflict with {conflicting_term} at level {current_level}",
        )
        self.conflict_history.append(conflict_cause)

        if learned_clause:
            self.learned_clauses.append(learned_clause)

        explanation = self._generate_explanation(conflict_cause, learned_clause)

        return ConflictAnalysis(
            learned_clause=learned_clause,
            backtrack_level=backtrack_level,
            explanation=explanation,
        )

    def _find_relevant_incompatibilities(
        self,
        conflicting_term: Term,
        solution: PartialSolution,
        incompatibilities: list[Incompatibility],
    ) -> list[Incompatibility]:
        """Find incompatibilities that are relevant to the current conflict."""
        relevant = []

        # Find incompatibilities involving the conflicting package
        for incompatibility in incompatibilities:
            if incompatibility.has_package(conflicting_term.package):
                relevant.append(incompatibility)

        # Find incompatibilities that are almost satisfied
        for incompatibility in incompatibilities:
            is_almost_satisfied, _ = incompatibility.is_almost_satisfied_by(solution)
            if is_almost_satisfied:
                relevant.append(incompatibility)

        return list(set(relevant))  # Remove duplicates

    def _derive_learned_clause(
        self, incompatibilities: list[Incompatibility], solution: PartialSolution
    ) -> Incompatibility | None:
        """Derive a learned clause from the conflict analysis."""
        if not incompatibilities:
            return None

        # For now, implement a simple learning strategy
        # A more sophisticated approach would do resolution-based learning

        # Find the most recent decision that led to this conflict
        latest_decision_level = 0
        conflicting_packages = set()

        for incompatibility in incompatibilities:
            for term in incompatibility.terms:
                assignment = solution.get_assignment(term.package)
                if assignment:
                    latest_decision_level = max(
                        latest_decision_level, assignment.decision_level
                    )
                    conflicting_packages.add(term.package)

        # Create a learned clause that prevents this specific conflict
        learned_terms = []
        for package in conflicting_packages:
            assignment = solution.get_assignment(package)
            if assignment and assignment.decision_level == latest_decision_level:
                # Add negation of this assignment
                from .version import VersionRange

                exact_range = VersionRange(
                    assignment.version, assignment.version, True, True
                )
                learned_term = Term(package, exact_range, False)  # NOT this version
                learned_terms.append(learned_term)

        if learned_terms:
            return Incompatibility(
                learned_terms,
                IncompatibilityKind.DERIVED,
                f"learned from conflict at level {latest_decision_level}",
            )

        return None

    def _calculate_backtrack_level(
        self, incompatibilities: list[Incompatibility], solution: PartialSolution
    ) -> int:
        """Calculate the appropriate backtrack level."""
        if not incompatibilities:
            return max(0, solution.decision_level - 1)

        # Find the second-highest decision level involved in the conflict
        decision_levels = set()
        for incompatibility in incompatibilities:
            for term in incompatibility.terms:
                assignment = solution.get_assignment(term.package)
                if assignment:
                    decision_levels.add(assignment.decision_level)

        sorted_levels = sorted(decision_levels, reverse=True)

        if len(sorted_levels) >= 2:
            # Backtrack to the second-highest level
            return sorted_levels[1]
        elif len(sorted_levels) == 1:
            # Backtrack one level below the conflict
            backtrack = sorted_levels[0] - 1
            return backtrack if backtrack >= 0 else -1  # Return -1 if unsolvable
        else:
            # No specific level found, backtrack one level
            backtrack = solution.decision_level - 1
            return backtrack if backtrack >= 0 else -1  # Return -1 if unsolvable

    def _generate_explanation(
        self, conflict_cause: ConflictCause, learned_clause: Incompatibility | None
    ) -> str:
        """Generate a human-readable explanation of the conflict."""
        explanation = f"Conflict at decision level {conflict_cause.decision_level}: "
        explanation += conflict_cause.explanation

        if learned_clause:
            explanation += f"\nLearned clause: {learned_clause}"

        if conflict_cause.conflicting_incompatibilities:
            explanation += f"\nInvolving {len(conflict_cause.conflicting_incompatibilities)} incompatibilities"

        return explanation

    def get_conflict_statistics(self) -> dict[str, int]:
        """Get statistics about conflicts encountered."""
        return {
            "total_conflicts": len(self.conflict_history),
            "learned_clauses": len(self.learned_clauses),
            "max_decision_level": max(
                (c.decision_level for c in self.conflict_history), default=0
            ),
        }

    def clear_history(self) -> None:
        """Clear conflict history and learned clauses."""
        self.conflict_history.clear()
        self.learned_clauses.clear()


class BacktrackingStrategy:
    """Defines different backtracking strategies."""

    @staticmethod
    def chronological_backtrack(solution: PartialSolution, target_level: int) -> None:
        """Simple chronological backtracking."""
        solution.backtrack(target_level)

    @staticmethod
    def non_chronological_backtrack(
        solution: PartialSolution,
        target_level: int,
        learned_clause: Incompatibility | None,
    ) -> None:
        """Non-chronological backtracking with learned clause consideration."""
        if learned_clause:
            # Find the appropriate level based on the learned clause
            min_level = 0
            for term in learned_clause.terms:
                assignment = solution.get_assignment(term.package)
                if assignment:
                    min_level = max(min_level, assignment.decision_level)

            # Backtrack to the minimum level that makes the learned clause meaningful
            actual_target = min(target_level, min_level)
            solution.backtrack(actual_target)
        else:
            solution.backtrack(target_level)


class ConflictExplainer:
    """Generates human-readable explanations for resolution failures."""

    def __init__(self) -> None:
        self.explanations: list[str] = []

    def explain_failure(
        self, conflict_resolver: ConflictResolver, root_package: Package
    ) -> str:
        """Generate a comprehensive explanation of why resolution failed."""
        stats = conflict_resolver.get_conflict_statistics()

        explanation = f"Failed to resolve dependencies for {root_package.name}\n"
        explanation += (
            f"Encountered {stats['total_conflicts']} conflicts during resolution\n"
        )

        if conflict_resolver.conflict_history:
            explanation += "\nConflict history:\n"
            for i, conflict in enumerate(conflict_resolver.conflict_history[-3:], 1):
                explanation += f"{i}. {conflict.explanation}\n"

        if conflict_resolver.learned_clauses:
            explanation += f"\nLearned {len(conflict_resolver.learned_clauses)} clauses during resolution\n"
            for clause in conflict_resolver.learned_clauses[-3:]:
                explanation += f"   - {clause}\n"

        return explanation

    def explain_version_conflict(
        self, package: Package, conflicting_versions: list[Version], reason: str
    ) -> str:
        """Explain why specific versions conflict."""
        explanation = f"Version conflict for {package.name}:\n"
        explanation += (
            f"Conflicting versions: {', '.join(str(v) for v in conflicting_versions)}\n"
        )
        explanation += f"Reason: {reason}\n"
        return explanation

    def explain_dependency_chain(self, chain: list[tuple[Package, Version]]) -> str:
        """Explain a dependency chain that led to a conflict."""
        explanation = "Dependency chain:\n"
        for i, (package, version) in enumerate(chain):
            indent = "  " * i
            explanation += f"{indent}{package.name}@{version}\n"
        return explanation
