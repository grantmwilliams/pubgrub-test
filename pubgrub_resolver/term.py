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

            # The complement of the union gives us NOT (A OR B)
            complement_set = union_set.complement()

            # If complement is empty, return None (no valid versions)
            if complement_set.is_empty():
                return None

            # If complement has exactly one range, we can represent it as a positive term
            if len(complement_set.ranges) == 1:
                return Term(self.package, complement_set.ranges[0], True)
            else:
                # Multiple disjoint ranges - we need to represent this as a negative term
                # of the union, which is what we computed above
                if len(union_set.ranges) == 1:
                    return Term(self.package, union_set.ranges[0], False)
                else:
                    # For now, return None for very complex cases
                    return None

        # One positive, one negative
        if self.positive and not other.positive:
            # self is positive, other is negative
            # We want versions that are in self but not in other
            # This is A AND NOT B = A - B (set difference)
            self_set = VersionSet([self.version_range])
            other_set = VersionSet([other.version_range])

            # Compute A - B = A ∩ complement(B)
            other_complement = other_set.complement()
            difference_set = self_set.intersect(other_complement)

            if difference_set.is_empty():
                return None

            # If result is a single range, we can represent it as a positive term
            if len(difference_set.ranges) == 1:
                return Term(self.package, difference_set.ranges[0], True)
            else:
                # Multiple ranges - for now return None for complex cases
                return None
        else:
            # self is negative, other is positive
            # We want versions that are in other but not in self
            # This is NOT A AND B = B - A (set difference)
            self_set = VersionSet([self.version_range])
            other_set = VersionSet([other.version_range])

            # Compute B - A = B ∩ complement(A)
            self_complement = self_set.complement()
            difference_set = other_set.intersect(self_complement)

            if difference_set.is_empty():
                return None

            # If result is a single range, we can represent it as a positive term
            if len(difference_set.ranges) == 1:
                return Term(self.package, difference_set.ranges[0], True)
            else:
                # Multiple ranges - for now return None for complex cases
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
