"""
Term class for representing package version constraints in PubGrub.
"""

from __future__ import annotations

from .package import Package
from .version import VersionRange, VersionSet


class Term:
    """
    Represents a term in the PubGrub algorithm.

    A term is either positive (the package must be selected) or negative
    (the package must not be selected), and has an associated version range.
    """

    def __init__(
        self, package: Package, version_range: VersionRange, positive: bool = True
    ) -> None:
        self.package = package
        self.version_range = version_range
        self.positive = positive

    def negate(self) -> Term:
        """Return the negation of this term."""
        return Term(self.package, self.version_range, not self.positive)

    def intersect(self, other: Term) -> Term | None:
        """
        Compute the intersection of two terms.

        Returns None if the terms are incompatible.
        """
        if self.package != other.package:
            raise ValueError("Cannot intersect terms for different packages")

        # Both positive: intersect version ranges
        if self.positive and other.positive:
            intersected_range = self.version_range.intersect(other.version_range)
            if intersected_range is None or intersected_range.is_empty():
                return None
            return Term(self.package, intersected_range, True)

        # Both negative: intersection of NOT A AND NOT B = NOT (A OR B)
        # We need to union the ranges and negate the result
        if not self.positive and not other.positive:
            # Create version sets from the ranges
            set1 = VersionSet([self.version_range])
            set2 = VersionSet([other.version_range])

            # Union the sets (A OR B)
            union_set = set1.union(set2)

            # For now, we'll handle the simple case where union results in a single range
            if len(union_set.ranges) == 1:
                # We can represent NOT (single range) as a negative term
                return Term(self.package, union_set.ranges[0], False)
            else:
                # Multiple disjoint ranges - this is complex to represent with a single Term
                # For now, return None to indicate we need a more complex Term representation
                return None

        # One positive, one negative
        if self.positive and not other.positive:
            # self is positive, other is negative
            # We want versions that are in self but not in other
            intersected_range = self.version_range.intersect(other.version_range)
            if intersected_range is None or intersected_range.is_empty():
                # No overlap, so positive term is unaffected
                return Term(self.package, self.version_range, True)
            else:
                # There's overlap - this creates a conflict
                return None
        else:
            # self is negative, other is positive
            # We want versions that are in other but not in self
            intersected_range = self.version_range.intersect(other.version_range)
            if intersected_range is None or intersected_range.is_empty():
                # No overlap, so positive term is unaffected
                return Term(self.package, other.version_range, True)
            else:
                # There's overlap - this creates a conflict
                return None

    def satisfies(self, other: Term) -> bool:
        """
        Check if this term satisfies another term.

        A term A satisfies term B if whenever A is true, B is also true.
        """
        if self.package != other.package:
            return False

        # If both are positive
        if self.positive and other.positive:
            # self satisfies other if self's range is a subset of other's range
            # This is approximated by checking if the intersection equals self's range
            intersected = self.version_range.intersect(other.version_range)
            return intersected == self.version_range

        # If both are negative
        if not self.positive and not other.positive:
            # NOT A satisfies NOT B if A's range is a superset of B's range
            # This is approximated by checking if the intersection equals other's range
            intersected = self.version_range.intersect(other.version_range)
            return intersected == other.version_range

        # If one is positive and one is negative
        if self.positive and not other.positive:
            # A satisfies NOT B if A and B have no overlap
            intersected = self.version_range.intersect(other.version_range)
            return intersected is None or intersected.is_empty()

        # If self is negative and other is positive
        if not self.positive and other.positive:
            # NOT A satisfies B - this is generally false unless B is empty
            return other.version_range.is_empty()

        return False

    def is_failure(self) -> bool:
        """Check if this term represents a failure (empty positive constraint)."""
        return self.positive and self.version_range.is_empty()

    def __str__(self) -> str:
        sign = "" if self.positive else "NOT "
        return f"{sign}{self.package.name} {self.version_range}"

    def __repr__(self) -> str:
        return f"Term({self.package!r}, {self.version_range!r}, {self.positive})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Term):
            return NotImplemented
        return (
            self.package == other.package
            and self.version_range == other.version_range
            and self.positive == other.positive
        )

    def __hash__(self) -> int:
        return hash((self.package, self.version_range, self.positive))
