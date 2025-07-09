"""
Incompatibility class for representing conflicts in PubGrub resolution.
"""

from __future__ import annotations

from enum import Enum
from .term import Term
from .package import Package
from .partial_solution import PartialSolution
from .version import Version


class IncompatibilityKind(Enum):
    """The kind of incompatibility."""

    # Root package must be selected
    ROOT = "root"

    # Package has no available versions
    NO_VERSIONS = "no_versions"

    # Package version has dependencies
    DEPENDENCY = "dependency"

    # Two constraints are incompatible
    CONFLICT = "conflict"

    # Derived from other incompatibilities
    DERIVED = "derived"


class Incompatibility:
    """
    Represents an incompatibility - a set of terms that cannot all be satisfied.

    An incompatibility is a clause in the resolution SAT problem.
    If all terms in an incompatibility are satisfied, we have a contradiction.
    """

    def __init__(
        self, terms: list[Term], kind: IncompatibilityKind, cause: str | None = None
    ) -> None:
        self.terms = terms
        self.kind = kind
        self.cause = cause or ""

        # Validate that all terms are for different packages
        packages = [term.package for term in terms]
        if len(set(packages)) != len(packages):
            raise ValueError(
                "Incompatibility cannot have multiple terms for the same package"
            )

    def get_term_for_package(self, package: Package) -> Term | None:
        """Get the term for a specific package, if any."""
        for term in self.terms:
            if term.package == package:
                return term
        return None

    def has_package(self, package: Package) -> bool:
        """Check if this incompatibility involves a specific package."""
        return any(term.package == package for term in self.terms)

    def get_packages(self) -> set[Package]:
        """Get all packages involved in this incompatibility."""
        return {term.package for term in self.terms}

    def is_satisfied_by(self, solution: PartialSolution) -> bool:
        """Check if this incompatibility is satisfied by a partial solution."""
        # An incompatibility is satisfied if all its terms are satisfied
        return all(solution.satisfies(term) for term in self.terms)

    def is_almost_satisfied_by(
        self, solution: PartialSolution
    ) -> tuple[bool, Term | None]:
        """
        Check if this incompatibility is almost satisfied (all but one term satisfied).

        Returns (is_almost_satisfied, unsatisfied_term).
        If almost satisfied, returns the single unsatisfied term.
        """
        satisfied_terms = []
        unsatisfied_terms = []
        unresolved_terms = []

        for term in self.terms:
            assignment = solution.get_assignment(term.package)
            if assignment is None:
                # Package not assigned - term is unresolved
                unresolved_terms.append(term)
            else:
                # Package is assigned - check if term is satisfied
                if solution.satisfies(term):
                    satisfied_terms.append(term)
                else:
                    unsatisfied_terms.append(term)

        # For unit propagation, we want exactly one unresolved term and all others unsatisfied
        # This means the incompatibility will be violated unless the unresolved term is true
        if len(unresolved_terms) == 1 and len(satisfied_terms) == 0:
            return True, unresolved_terms[0]
        else:
            return False, None

    def get_unit_clause(self, solution: PartialSolution) -> Term | None:
        """
        Get the unit clause from this incompatibility given a partial solution.

        If this incompatibility is almost satisfied, returns the unresolved term
        that must be true to satisfy the incompatibility.
        """
        is_almost_satisfied, unresolved_term = self.is_almost_satisfied_by(solution)
        if is_almost_satisfied and unresolved_term is not None:
            return unresolved_term
        return None

    def is_failure(self) -> bool:
        """Check if this incompatibility represents a failure (no terms)."""
        return len(self.terms) == 0

    def is_unit(self) -> bool:
        """Check if this incompatibility is a unit clause (single term)."""
        return len(self.terms) == 1

    def get_single_term(self) -> Term:
        """Get the single term (only valid if is_unit() is True)."""
        if not self.is_unit():
            raise ValueError("Incompatibility is not a unit clause")
        return self.terms[0]

    def negate(self) -> list[Term]:
        """Get the negation of this incompatibility (for unit propagation)."""
        return [term.negate() for term in self.terms]

    def __str__(self) -> str:
        if self.is_failure():
            return "⊥"  # Bottom symbol for contradiction

        terms_str = " ∨ ".join(str(term) for term in self.terms)
        if self.cause:
            return f"{terms_str} (because {self.cause})"
        return terms_str

    def __repr__(self) -> str:
        return f"Incompatibility({self.terms!r}, {self.kind}, {self.cause!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Incompatibility):
            return NotImplemented
        return (
            self.terms == other.terms
            and self.kind == other.kind
            and self.cause == other.cause
        )

    def __hash__(self) -> int:
        return hash((tuple(self.terms), self.kind, self.cause))


def create_root_incompatibility(root_package: Package) -> Incompatibility:
    """Create an incompatibility requiring the root package to be selected."""
    from .version import VersionRange

    # NOT root means root must be selected
    root_term = Term(root_package, VersionRange(), False)
    return Incompatibility(
        [root_term], IncompatibilityKind.ROOT, "root package must be selected"
    )


def create_no_versions_incompatibility(package: Package) -> Incompatibility:
    """Create an incompatibility when a package has no available versions."""
    from .version import VersionRange

    # Package has no versions available
    no_versions_term = Term(package, VersionRange(), True)
    return Incompatibility(
        [no_versions_term],
        IncompatibilityKind.NO_VERSIONS,
        f"no versions available for {package.name}",
    )


def create_dependency_incompatibility(
    package: Package, package_version: Version, dependency_term: Term
) -> Incompatibility:
    """Create an incompatibility representing a dependency relationship."""
    from .version import VersionRange

    # If package@version is selected, then dependency must be satisfied
    # This is: NOT package@version OR dependency
    package_exact_range = VersionRange(package_version, package_version, True, True)
    package_term = Term(package, package_exact_range, False)  # NOT package@version

    return Incompatibility(
        [package_term, dependency_term],
        IncompatibilityKind.DEPENDENCY,
        f"{package.name}@{package_version} depends on {dependency_term}",
    )


def create_conflict_incompatibility(term1: Term, term2: Term) -> Incompatibility:
    """Create an incompatibility representing a conflict between two terms."""
    # Two terms conflict if they cannot both be satisfied
    # This is: NOT term1 OR NOT term2
    return Incompatibility(
        [term1.negate(), term2.negate()],
        IncompatibilityKind.CONFLICT,
        f"{term1} conflicts with {term2}",
    )


class IncompatibilitySet:
    """Manages a set of incompatibilities for efficient queries."""

    def __init__(self) -> None:
        self.incompatibilities: list[Incompatibility] = []
        self._by_package: dict[Package, list[Incompatibility]] = {}

    def add(self, incompatibility: Incompatibility) -> None:
        """Add an incompatibility to the set."""
        self.incompatibilities.append(incompatibility)

        # Index by package for efficient lookup
        for package in incompatibility.get_packages():
            if package not in self._by_package:
                self._by_package[package] = []
            self._by_package[package].append(incompatibility)

    def get_for_package(self, package: Package) -> list[Incompatibility]:
        """Get all incompatibilities involving a specific package."""
        return self._by_package.get(package, [])

    def get_all(self) -> list[Incompatibility]:
        """Get all incompatibilities."""
        return self.incompatibilities.copy()

    def find_unit_clauses(self, solution: PartialSolution) -> list[Term]:
        """Find all unit clauses given a partial solution."""
        unit_clauses = []
        for incompatibility in self.incompatibilities:
            unit_clause = incompatibility.get_unit_clause(solution)
            if unit_clause is not None:
                unit_clauses.append(unit_clause)
        return unit_clauses

    def find_satisfied(self, solution: PartialSolution) -> list[Incompatibility]:
        """Find all incompatibilities satisfied by a partial solution."""
        return [inc for inc in self.incompatibilities if inc.is_satisfied_by(solution)]

    def __len__(self) -> int:
        return len(self.incompatibilities)

    def __str__(self) -> str:
        return f"IncompatibilitySet({len(self.incompatibilities)} incompatibilities)"

    def __repr__(self) -> str:
        return f"IncompatibilitySet({self.incompatibilities!r})"
