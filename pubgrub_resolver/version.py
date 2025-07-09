"""
Version and VersionRange classes for semantic version handling.
"""

from __future__ import annotations

import re
from functools import total_ordering


@total_ordering
class Version:
    """Represents a semantic version (e.g., "1.2.3")."""

    def __init__(self, version_string: str) -> None:
        self.version_string = version_string
        self._parse_version()

    def _parse_version(self) -> None:
        """Parse version string into components."""
        # Simple semantic version parsing
        match = re.match(
            r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9.-]+))?(?:\+([a-zA-Z0-9.-]+))?$",
            self.version_string,
        )
        if not match:
            raise ValueError(f"Invalid version format: {self.version_string}")

        self.major = int(match.group(1))
        self.minor = int(match.group(2))
        self.patch = int(match.group(3))
        self.pre_release = match.group(4)
        self.build = match.group(5)

    def __str__(self) -> str:
        return self.version_string

    def __repr__(self) -> str:
        return f"Version('{self.version_string}')"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self.version_string == other.version_string

    def __lt__(self, other: Version) -> bool:
        if not isinstance(other, Version):
            return NotImplemented

        # Compare major, minor, patch
        if (self.major, self.minor, self.patch) != (
            other.major,
            other.minor,
            other.patch,
        ):
            return (self.major, self.minor, self.patch) < (
                other.major,
                other.minor,
                other.patch,
            )

        # Handle pre-release versions
        if self.pre_release is None and other.pre_release is None:
            return False
        elif self.pre_release is None:
            return False  # 1.0.0 > 1.0.0-alpha
        elif other.pre_release is None:
            return True  # 1.0.0-alpha < 1.0.0
        else:
            return self.pre_release < other.pre_release

    def __hash__(self) -> int:
        return hash(self.version_string)


class VersionRange:
    """Represents a range of acceptable versions."""

    def __init__(
        self,
        min_version: Version | None = None,
        max_version: Version | None = None,
        include_min: bool = True,
        include_max: bool = False,
    ) -> None:
        self.min_version = min_version
        self.max_version = max_version
        self.include_min = include_min
        self.include_max = include_max

    def contains(self, version: Version) -> bool:
        """Check if a version is within this range."""
        if self.min_version is not None:
            if self.include_min:
                if version < self.min_version:
                    return False
            else:
                if version <= self.min_version:
                    return False

        if self.max_version is not None:
            if self.include_max:
                if version > self.max_version:
                    return False
            else:
                if version >= self.max_version:
                    return False

        return True

    def intersect(self, other: VersionRange) -> VersionRange | None:
        """Compute the intersection of two version ranges."""
        # Determine new minimum
        new_min = None
        new_include_min = True

        if self.min_version is None:
            new_min = other.min_version
            new_include_min = other.include_min
        elif other.min_version is None:
            new_min = self.min_version
            new_include_min = self.include_min
        else:
            if self.min_version > other.min_version:
                new_min = self.min_version
                new_include_min = self.include_min
            elif self.min_version < other.min_version:
                new_min = other.min_version
                new_include_min = other.include_min
            else:  # Equal
                new_min = self.min_version
                new_include_min = self.include_min and other.include_min

        # Determine new maximum
        new_max = None
        new_include_max = False

        if self.max_version is None:
            new_max = other.max_version
            new_include_max = other.include_max
        elif other.max_version is None:
            new_max = self.max_version
            new_include_max = self.include_max
        else:
            if self.max_version < other.max_version:
                new_max = self.max_version
                new_include_max = self.include_max
            elif self.max_version > other.max_version:
                new_max = other.max_version
                new_include_max = other.include_max
            else:  # Equal
                new_max = self.max_version
                new_include_max = self.include_max and other.include_max

        # Check if range is valid
        if new_min is not None and new_max is not None:
            if new_min > new_max:
                return None
            elif new_min == new_max and not (new_include_min and new_include_max):
                return None

        return VersionRange(new_min, new_max, new_include_min, new_include_max)

    def union(self, other: VersionRange) -> list[VersionRange]:
        """
        Compute the union of two version ranges.

        Returns a list of VersionRange objects representing the union.
        If the ranges overlap or are adjacent, returns a single merged range.
        Otherwise, returns both ranges as separate elements.
        """
        # Check if ranges overlap or are adjacent
        if self._overlaps_or_adjacent(other):
            # Merge the ranges
            merged = self._merge_ranges(other)
            return [merged]
        else:
            # Return both ranges as separate elements
            return [self, other]

    def _overlaps_or_adjacent(self, other: VersionRange) -> bool:
        """Check if two ranges overlap or are adjacent."""
        if self.is_empty() or other.is_empty():
            return False

        # If either range is unbounded, they likely overlap
        if (
            self.min_version is None
            or self.max_version is None
            or other.min_version is None
            or other.max_version is None
        ):
            return True

        # Check for overlap or adjacency
        # Range 1: [a, b), Range 2: [c, d)
        # They overlap if a < d and c < b
        # They are adjacent if b == c or d == a

        # Check if self.max touches or overlaps with other.min
        if self.max_version == other.min_version:
            # Adjacent if one includes the boundary point
            return self.include_max or other.include_min
        elif self.max_version < other.min_version:
            return False

        # Check if other.max touches or overlaps with self.min
        if other.max_version == self.min_version:
            # Adjacent if one includes the boundary point
            return other.include_max or self.include_min
        elif other.max_version < self.min_version:
            return False

        # If we get here, ranges overlap
        return True

    def _merge_ranges(self, other: VersionRange) -> VersionRange:
        """Merge two overlapping or adjacent ranges."""
        # Determine new minimum
        new_min = None
        new_include_min = True

        if self.min_version is None:
            new_min = None
        elif other.min_version is None:
            new_min = None
        else:
            if self.min_version < other.min_version:
                new_min = self.min_version
                new_include_min = self.include_min
            elif self.min_version > other.min_version:
                new_min = other.min_version
                new_include_min = other.include_min
            else:  # Equal
                new_min = self.min_version
                new_include_min = self.include_min or other.include_min

        # Determine new maximum
        new_max = None
        new_include_max = False

        if self.max_version is None:
            new_max = None
        elif other.max_version is None:
            new_max = None
        else:
            if self.max_version > other.max_version:
                new_max = self.max_version
                new_include_max = self.include_max
            elif self.max_version < other.max_version:
                new_max = other.max_version
                new_include_max = other.include_max
            else:  # Equal
                new_max = self.max_version
                new_include_max = self.include_max or other.include_max

        return VersionRange(new_min, new_max, new_include_min, new_include_max)

    def is_empty(self) -> bool:
        """Check if this range is empty."""
        if self.min_version is None and self.max_version is None:
            return False

        if self.min_version is not None and self.max_version is not None:
            if self.min_version > self.max_version:
                return True
            elif self.min_version == self.max_version and not (
                self.include_min and self.include_max
            ):
                return True

        return False

    def __str__(self) -> str:
        if self.min_version is None and self.max_version is None:
            return "any"

        parts = []
        if self.min_version is not None:
            op = ">=" if self.include_min else ">"
            parts.append(f"{op}{self.min_version}")

        if self.max_version is not None:
            op = "<=" if self.include_max else "<"
            parts.append(f"{op}{self.max_version}")

        return ", ".join(parts)

    def __repr__(self) -> str:
        return f"VersionRange({self.min_version}, {self.max_version}, {self.include_min}, {self.include_max})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VersionRange):
            return NotImplemented
        return (
            self.min_version == other.min_version
            and self.max_version == other.max_version
            and self.include_min == other.include_min
            and self.include_max == other.include_max
        )

    def __hash__(self) -> int:
        return hash(
            (self.min_version, self.max_version, self.include_min, self.include_max)
        )


class VersionSet:
    """Represents a set of version ranges (union of disjoint ranges)."""

    def __init__(
        self, ranges: list[VersionRange] | None = None, normalize: bool = True
    ) -> None:
        """Initialize with a list of version ranges."""
        self.ranges = ranges or []
        if normalize:
            self._normalize()

    def _normalize(self) -> None:
        """Normalize the ranges by merging overlapping/adjacent ranges."""
        if not self.ranges:
            return

        # Sort ranges by minimum version
        self.ranges.sort(key=lambda r: (r.min_version is None, r.min_version))

        # Merge overlapping/adjacent ranges
        merged = [self.ranges[0]]
        for current in self.ranges[1:]:
            last = merged[-1]
            if last._overlaps_or_adjacent(current):
                merged[-1] = last._merge_ranges(current)
            else:
                merged.append(current)

        self.ranges = merged

    def union(self, other: VersionSet) -> VersionSet:
        """Compute the union of two version sets."""
        combined_ranges = self.ranges + other.ranges
        return VersionSet(combined_ranges)

    def intersect(self, other: VersionSet) -> VersionSet:
        """Compute the intersection of two version sets."""
        result_ranges = []
        for range1 in self.ranges:
            for range2 in other.ranges:
                intersection = range1.intersect(range2)
                if intersection is not None and not intersection.is_empty():
                    result_ranges.append(intersection)
        return VersionSet(result_ranges)

    def contains(self, version: Version) -> bool:
        """Check if a version is contained in this set."""
        return any(range_obj.contains(version) for range_obj in self.ranges)

    def is_empty(self) -> bool:
        """Check if this set is empty."""
        return len(self.ranges) == 0 or all(r.is_empty() for r in self.ranges)

    def complement(self) -> VersionSet:
        """Compute the complement of this version set."""
        if self.is_empty():
            # Complement of empty set is the universal set
            return VersionSet([VersionRange()])

        # Normalize the ranges first (merge overlapping ranges)
        normalized_ranges = []
        for r in self.ranges:
            if not r.is_empty():
                normalized_ranges.append(r)

        if not normalized_ranges:
            return VersionSet([VersionRange()])

        # Sort ranges by their minimum version
        sorted_ranges = sorted(
            normalized_ranges,
            key=lambda r: (r.min_version or Version("0.0.0"), r.include_min),
        )

        complement_ranges = []

        # Handle the range before the first range
        first_range = sorted_ranges[0]
        if first_range.min_version is not None:
            # Add range from negative infinity to the start of first range
            complement_ranges.append(
                VersionRange(
                    min_version=None,
                    max_version=first_range.min_version,
                    include_min=True,
                    include_max=not first_range.include_min,
                )
            )

        # Handle gaps between ranges
        for i in range(len(sorted_ranges) - 1):
            current_range = sorted_ranges[i]
            next_range = sorted_ranges[i + 1]

            # Check if there's a gap between current and next range
            if (
                current_range.max_version is not None
                and next_range.min_version is not None
            ):
                # There's a potential gap
                if current_range.max_version < next_range.min_version or (
                    current_range.max_version == next_range.min_version
                    and not (current_range.include_max and next_range.include_min)
                ):
                    # Add the gap as a range
                    complement_ranges.append(
                        VersionRange(
                            min_version=current_range.max_version,
                            max_version=next_range.min_version,
                            include_min=not current_range.include_max,
                            include_max=not next_range.include_min,
                        )
                    )

        # Handle the range after the last range
        last_range = sorted_ranges[-1]
        if last_range.max_version is not None:
            # Add range from end of last range to positive infinity
            complement_ranges.append(
                VersionRange(
                    min_version=last_range.max_version,
                    max_version=None,
                    include_min=not last_range.include_max,
                    include_max=False,
                )
            )

        # Filter out empty ranges
        complement_ranges = [r for r in complement_ranges if not r.is_empty()]

        return VersionSet(complement_ranges, normalize=False)

    def __str__(self) -> str:
        if not self.ranges:
            return "∅"
        return " ∪ ".join(str(r) for r in self.ranges)

    def __repr__(self) -> str:
        return f"VersionSet({self.ranges!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VersionSet):
            return NotImplemented
        return self.ranges == other.ranges

    def __hash__(self) -> int:
        return hash(tuple(self.ranges))


def parse_version_constraint(constraint: str) -> VersionRange:
    """Parse a version constraint string into a VersionRange."""
    constraint = constraint.strip()

    if constraint == "*" or constraint == "":
        return VersionRange()

    # Handle compound constraints like ">=1.0.0,<2.0.0"
    if "," in constraint:
        parts = [part.strip() for part in constraint.split(",")]
        min_version = None
        max_version = None
        min_inclusive = False
        max_inclusive = False

        for part in parts:
            if part.startswith(">="):
                min_version = Version(part[2:].strip())
                min_inclusive = True
            elif part.startswith(">"):
                min_version = Version(part[1:].strip())
                min_inclusive = False
            elif part.startswith("<="):
                max_version = Version(part[2:].strip())
                max_inclusive = True
            elif part.startswith("<"):
                max_version = Version(part[1:].strip())
                max_inclusive = False
            else:
                raise ValueError(f"Unsupported constraint part: {part}")

        return VersionRange(min_version, max_version, min_inclusive, max_inclusive)

    # Handle specific version
    if re.match(r"^\d+\.\d+\.\d+", constraint):
        version = Version(constraint)
        return VersionRange(version, version, True, True)

    # Handle range constraints
    if constraint.startswith(">="):
        version = Version(constraint[2:].strip())
        return VersionRange(min_version=version, include_min=True)
    elif constraint.startswith(">"):
        version = Version(constraint[1:].strip())
        return VersionRange(min_version=version, include_min=False)
    elif constraint.startswith("<="):
        version = Version(constraint[2:].strip())
        return VersionRange(max_version=version, include_max=True)
    elif constraint.startswith("<"):
        version = Version(constraint[1:].strip())
        return VersionRange(max_version=version, include_max=False)

    raise ValueError(f"Unsupported version constraint: {constraint}")
