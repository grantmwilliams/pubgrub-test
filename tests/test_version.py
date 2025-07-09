"""
Comprehensive tests for version handling.
"""

import pytest
from pubgrub_resolver.version import Version, VersionRange, parse_version_constraint


class TestVersion:
    """Test Version class functionality."""

    def test_version_creation(self):
        """Test basic version creation."""
        v = Version("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3
        assert v.pre_release is None
        assert v.build is None

    def test_version_with_prerelease(self):
        """Test version with pre-release."""
        v = Version("1.2.3-alpha.1")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3
        assert v.pre_release == "alpha.1"
        assert v.build is None

    def test_version_with_build(self):
        """Test version with build metadata."""
        v = Version("1.2.3+build.1")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3
        assert v.pre_release is None
        assert v.build == "build.1"

    def test_version_with_prerelease_and_build(self):
        """Test version with both pre-release and build."""
        v = Version("1.2.3-alpha.1+build.1")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3
        assert v.pre_release == "alpha.1"
        assert v.build == "build.1"

    def test_invalid_version_format(self):
        """Test invalid version formats."""
        with pytest.raises(ValueError):
            Version("1.2")

        with pytest.raises(ValueError):
            Version("1.2.3.4")

        with pytest.raises(ValueError):
            Version("invalid")

    def test_version_comparison(self):
        """Test version comparison operations."""
        v1 = Version("1.2.3")
        v2 = Version("1.2.4")
        v3 = Version("1.3.0")
        v4 = Version("2.0.0")

        assert v1 < v2
        assert v2 < v3
        assert v3 < v4
        assert v1 < v4

        assert v4 > v3
        assert v3 > v2
        assert v2 > v1

    def test_version_prerelease_comparison(self):
        """Test comparison with pre-release versions."""
        v1 = Version("1.0.0-alpha")
        v2 = Version("1.0.0-beta")
        v3 = Version("1.0.0")

        assert v1 < v2
        assert v2 < v3
        assert v1 < v3

    def test_version_equality(self):
        """Test version equality."""
        v1 = Version("1.2.3")
        v2 = Version("1.2.3")
        v3 = Version("1.2.4")

        assert v1 == v2
        assert v1 != v3
        assert hash(v1) == hash(v2)
        assert hash(v1) != hash(v3)

    def test_version_string_representation(self):
        """Test string representation of versions."""
        v = Version("1.2.3-alpha.1+build.1")
        assert str(v) == "1.2.3-alpha.1+build.1"
        assert repr(v) == "Version('1.2.3-alpha.1+build.1')"


class TestVersionRange:
    """Test VersionRange class functionality."""

    def test_version_range_creation(self):
        """Test basic version range creation."""
        v1 = Version("1.0.0")
        v2 = Version("2.0.0")

        # Unbounded range
        range1 = VersionRange()
        assert range1.min_version is None
        assert range1.max_version is None

        # Bounded range
        range2 = VersionRange(v1, v2)
        assert range2.min_version == v1
        assert range2.max_version == v2
        assert range2.include_min is True
        assert range2.include_max is False

    def test_version_range_contains(self):
        """Test version range containment."""
        v1 = Version("1.0.0")
        v2 = Version("2.0.0")
        v3 = Version("1.5.0")

        range1 = VersionRange(v1, v2)
        assert range1.contains(v1)  # Included by default
        assert not range1.contains(v2)  # Excluded by default
        assert range1.contains(v3)

        range2 = VersionRange(v1, v2, include_min=False, include_max=True)
        assert not range2.contains(v1)
        assert range2.contains(v2)
        assert range2.contains(v3)

    def test_version_range_intersection(self):
        """Test version range intersection."""
        v1 = Version("1.0.0")
        v2 = Version("2.0.0")
        v3 = Version("1.5.0")
        v4 = Version("3.0.0")

        range1 = VersionRange(v1, v4)  # [1.0.0, 3.0.0)
        range2 = VersionRange(v3, v2)  # [1.5.0, 2.0.0)

        intersection = range1.intersect(range2)
        assert intersection is not None
        assert intersection.min_version == v3
        assert intersection.max_version == v2

    def test_version_range_intersection_empty(self):
        """Test empty intersection."""
        v1 = Version("1.0.0")
        v2 = Version("2.0.0")
        v3 = Version("3.0.0")
        v4 = Version("4.0.0")

        range1 = VersionRange(v1, v2)  # [1.0.0, 2.0.0)
        range2 = VersionRange(v3, v4)  # [3.0.0, 4.0.0)

        intersection = range1.intersect(range2)
        assert intersection is None

    def test_version_range_intersection_single_point(self):
        """Test intersection at a single point."""
        v1 = Version("1.0.0")
        v2 = Version("2.0.0")

        range1 = VersionRange(v1, v2, include_max=True)  # [1.0.0, 2.0.0]
        range2 = VersionRange(v2, None)  # [2.0.0, ∞)

        intersection = range1.intersect(range2)
        assert intersection is not None
        assert intersection.min_version == v2
        assert intersection.max_version == v2
        assert intersection.include_min is True
        assert intersection.include_max is True

    def test_version_range_is_empty(self):
        """Test empty range detection."""
        v1 = Version("1.0.0")
        v2 = Version("2.0.0")

        # Normal range
        range1 = VersionRange(v1, v2)
        assert not range1.is_empty()

        # Empty range (min > max)
        range2 = VersionRange(v2, v1)
        assert range2.is_empty()

        # Empty range (min = max but not inclusive)
        range3 = VersionRange(v1, v1, include_min=False, include_max=False)
        assert range3.is_empty()

        # Valid single point
        range4 = VersionRange(v1, v1, include_min=True, include_max=True)
        assert not range4.is_empty()

    def test_version_range_equality(self):
        """Test version range equality."""
        v1 = Version("1.0.0")
        v2 = Version("2.0.0")

        range1 = VersionRange(v1, v2)
        range2 = VersionRange(v1, v2)
        range3 = VersionRange(v1, v2, include_max=True)

        assert range1 == range2
        assert range1 != range3
        assert hash(range1) == hash(range2)

    def test_version_range_string_representation(self):
        """Test string representation of version ranges."""
        v1 = Version("1.0.0")
        v2 = Version("2.0.0")

        range1 = VersionRange()
        assert str(range1) == "any"

        range2 = VersionRange(v1, v2)
        assert str(range2) == ">=1.0.0, <2.0.0"

        range3 = VersionRange(v1, v2, include_min=False, include_max=True)
        assert str(range3) == ">1.0.0, <=2.0.0"


class TestVersionConstraintParsing:
    """Test version constraint parsing."""

    def test_parse_any_constraint(self):
        """Test parsing of 'any' constraints."""
        range1 = parse_version_constraint("*")
        assert range1.min_version is None
        assert range1.max_version is None

        range2 = parse_version_constraint("")
        assert range2.min_version is None
        assert range2.max_version is None

    def test_parse_exact_version(self):
        """Test parsing exact version constraints."""
        range1 = parse_version_constraint("1.2.3")
        assert range1.min_version == Version("1.2.3")
        assert range1.max_version == Version("1.2.3")
        assert range1.include_min is True
        assert range1.include_max is True

    def test_parse_greater_than_constraints(self):
        """Test parsing greater-than constraints."""
        range1 = parse_version_constraint(">=1.2.3")
        assert range1.min_version == Version("1.2.3")
        assert range1.max_version is None
        assert range1.include_min is True

        range2 = parse_version_constraint(">1.2.3")
        assert range2.min_version == Version("1.2.3")
        assert range2.max_version is None
        assert range2.include_min is False

    def test_parse_less_than_constraints(self):
        """Test parsing less-than constraints."""
        range1 = parse_version_constraint("<=1.2.3")
        assert range1.min_version is None
        assert range1.max_version == Version("1.2.3")
        assert range1.include_max is True

        range2 = parse_version_constraint("<1.2.3")
        assert range2.min_version is None
        assert range2.max_version == Version("1.2.3")
        assert range2.include_max is False

    def test_parse_invalid_constraint(self):
        """Test parsing invalid constraints."""
        with pytest.raises(ValueError):
            parse_version_constraint("~1.2.3")

        with pytest.raises(ValueError):
            parse_version_constraint("^1.2.3")


class TestVersionStressTests:
    """Stress tests for version handling."""

    def test_many_versions_sorting(self):
        """Test sorting many versions."""
        versions = [
            Version("1.0.0"),
            Version("1.0.1"),
            Version("1.1.0"),
            Version("1.1.1"),
            Version("2.0.0"),
            Version("2.0.1"),
            Version("2.1.0"),
            Version("10.0.0"),
            Version("10.0.1"),
        ]

        # Shuffle and sort
        import random

        shuffled = versions.copy()
        random.shuffle(shuffled)
        sorted_versions = sorted(shuffled)

        assert sorted_versions == versions

    def test_complex_range_intersections(self):
        """Test complex range intersections."""
        v1 = Version("1.0.0")
        v2 = Version("2.0.0")
        v3 = Version("3.0.0")
        v4 = Version("4.0.0")
        v5 = Version("5.0.0")

        ranges = [
            VersionRange(v1, v5),  # [1.0.0, 5.0.0)
            VersionRange(v2, v4),  # [2.0.0, 4.0.0)
            VersionRange(v3, None),  # [3.0.0, ∞)
            VersionRange(None, v4),  # (-∞, 4.0.0)
        ]

        # Intersect all ranges
        result = ranges[0]
        for range_item in ranges[1:]:
            result = result.intersect(range_item)
            if result is None:
                break

        assert result is not None
        assert result.min_version == v3
        assert result.max_version == v4
        assert result.include_min is True
        assert result.include_max is False

    def test_version_range_edge_cases(self):
        """Test edge cases in version ranges."""
        v1 = Version("1.0.0")

        # Range with same min and max
        range1 = VersionRange(v1, v1, include_min=True, include_max=True)
        assert range1.contains(v1)
        assert not range1.is_empty()

        # Range with same min and max, exclusive
        range2 = VersionRange(v1, v1, include_min=False, include_max=False)
        assert not range2.contains(v1)
        assert range2.is_empty()

        # Range with same min and max, partially inclusive
        range3 = VersionRange(v1, v1, include_min=True, include_max=False)
        assert not range3.contains(v1)
        assert range3.is_empty()

    def test_prerelease_version_edge_cases(self):
        """Test edge cases with pre-release versions."""
        versions = [
            Version("1.0.0-alpha"),
            Version("1.0.0-alpha.1"),
            Version("1.0.0-alpha.2"),
            Version("1.0.0-beta"),
            Version("1.0.0-beta.1"),
            Version("1.0.0-rc.1"),
            Version("1.0.0"),
        ]

        # Check that they are in order
        for i in range(len(versions) - 1):
            assert versions[i] < versions[i + 1]

        # Check that stable version is greater than all pre-releases
        stable = Version("1.0.0")
        for version in versions[:-1]:
            assert version < stable
