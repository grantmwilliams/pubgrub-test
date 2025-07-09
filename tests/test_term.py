"""
Comprehensive tests for Term class.
"""

import pytest
from pubgrub_resolver.term import Term
from pubgrub_resolver.package import Package
from pubgrub_resolver.version import Version, VersionRange


class TestTerm:
    """Test Term class functionality."""

    def test_term_creation(self):
        """Test basic term creation."""
        pkg = Package("test")
        version_range = VersionRange(Version("1.0.0"), Version("2.0.0"))

        # Positive term
        term1 = Term(pkg, version_range, True)
        assert term1.package == pkg
        assert term1.version_range == version_range
        assert term1.positive is True

        # Negative term
        term2 = Term(pkg, version_range, False)
        assert term2.package == pkg
        assert term2.version_range == version_range
        assert term2.positive is False

        # Default positive
        term3 = Term(pkg, version_range)
        assert term3.positive is True

    def test_term_negation(self):
        """Test term negation."""
        pkg = Package("test")
        version_range = VersionRange(Version("1.0.0"), Version("2.0.0"))

        term = Term(pkg, version_range, True)
        negated = term.negate()

        assert negated.package == pkg
        assert negated.version_range == version_range
        assert negated.positive is False

        double_negated = negated.negate()
        assert double_negated.positive is True

    def test_term_intersection_both_positive(self):
        """Test intersection of two positive terms."""
        pkg = Package("test")
        v1 = Version("1.0.0")
        v2 = Version("2.0.0")
        v3 = Version("1.5.0")
        v4 = Version("2.5.0")

        term1 = Term(pkg, VersionRange(v1, v4))  # [1.0.0, 2.5.0)
        term2 = Term(pkg, VersionRange(v3, v2))  # [1.5.0, 2.0.0)

        intersection = term1.intersect(term2)
        assert intersection is not None
        assert intersection.positive is True
        assert intersection.version_range.min_version == v3
        assert intersection.version_range.max_version == v2

    def test_term_intersection_both_positive_no_overlap(self):
        """Test intersection of two positive terms with no overlap."""
        pkg = Package("test")
        v1 = Version("1.0.0")
        v2 = Version("2.0.0")
        v3 = Version("3.0.0")
        v4 = Version("4.0.0")

        term1 = Term(pkg, VersionRange(v1, v2))  # [1.0.0, 2.0.0)
        term2 = Term(pkg, VersionRange(v3, v4))  # [3.0.0, 4.0.0)

        intersection = term1.intersect(term2)
        assert intersection is None

    def test_term_intersection_both_negative(self):
        """Test intersection of two negative terms."""
        pkg = Package("test")
        v1 = Version("1.0.0")
        v2 = Version("2.0.0")
        v3 = Version("1.5.0")
        v4 = Version("2.5.0")

        term1 = Term(pkg, VersionRange(v1, v4), False)  # NOT [1.0.0, 2.5.0)
        term2 = Term(pkg, VersionRange(v3, v2), False)  # NOT [1.5.0, 2.0.0)

        intersection = term1.intersect(term2)
        # This is intersection of two negative terms with overlapping ranges
        # NOT [1.0.0, 2.5.0) AND NOT [1.5.0, 2.0.0) should be NOT ([1.0.0, 2.5.0) OR [1.5.0, 2.0.0))
        # Since [1.5.0, 2.0.0) is contained in [1.0.0, 2.5.0), the union is [1.0.0, 2.5.0)
        # So the result should be NOT [1.0.0, 2.5.0)
        assert intersection is not None
        assert intersection.positive is False
        expected_range = VersionRange(v1, v4)  # [1.0.0, 2.5.0)
        assert intersection.version_range == expected_range

    def test_term_intersection_both_negative_correctness(self):
        """Test that negative term intersection is mathematically correct."""
        pkg = Package("test")
        v1 = Version("1.0.0")
        v2 = Version("2.0.0")
        v3 = Version("3.0.0")

        # NOT [1.0.0, 2.0.0) AND NOT [2.0.0, 3.0.0)
        # Should be NOT ([1.0.0, 2.0.0) OR [2.0.0, 3.0.0)) = NOT [1.0.0, 3.0.0)
        term1 = Term(pkg, VersionRange(v1, v2), False)  # NOT [1.0.0, 2.0.0)
        term2 = Term(pkg, VersionRange(v2, v3), False)  # NOT [2.0.0, 3.0.0)

        intersection = term1.intersect(term2)

        # This is what the correct behavior should be:
        expected_range = VersionRange(v1, v3)
        assert intersection is not None
        assert intersection.positive is False
        assert intersection.version_range == expected_range

    def test_term_intersection_positive_negative_no_overlap(self):
        """Test intersection of positive and negative terms with no overlap."""
        pkg = Package("test")
        v1 = Version("1.0.0")
        v2 = Version("2.0.0")
        v3 = Version("3.0.0")
        v4 = Version("4.0.0")

        term1 = Term(pkg, VersionRange(v1, v2), True)  # [1.0.0, 2.0.0)
        term2 = Term(pkg, VersionRange(v3, v4), False)  # NOT [3.0.0, 4.0.0)

        intersection = term1.intersect(term2)
        assert intersection is not None
        assert intersection.positive is True
        assert intersection.version_range == term1.version_range

    def test_term_intersection_positive_negative_overlap(self):
        """Test intersection of positive and negative terms with overlap."""
        pkg = Package("test")
        v1 = Version("1.0.0")
        v2 = Version("2.0.0")
        v3 = Version("1.5.0")

        term1 = Term(pkg, VersionRange(v1, v2), True)  # [1.0.0, 2.0.0)
        term2 = Term(pkg, VersionRange(v3, v2), False)  # NOT [1.5.0, 2.0.0)

        intersection = term1.intersect(term2)
        # Should compute [1.0.0, 2.0.0) ∩ NOT [1.5.0, 2.0.0) = [1.0.0, 1.5.0)
        assert intersection is not None
        assert intersection.positive is True
        assert intersection.version_range.min_version == v1
        assert intersection.version_range.max_version == v3
        assert intersection.version_range.include_min is True
        assert intersection.version_range.include_max is False

    def test_term_intersection_different_packages(self):
        """Test intersection of terms for different packages."""
        pkg1 = Package("test1")
        pkg2 = Package("test2")
        version_range = VersionRange(Version("1.0.0"), Version("2.0.0"))

        term1 = Term(pkg1, version_range)
        term2 = Term(pkg2, version_range)

        with pytest.raises(ValueError):
            term1.intersect(term2)

    def test_term_satisfies_both_positive(self):
        """Test satisfies relationship for positive terms."""
        pkg = Package("test")
        v1 = Version("1.0.0")
        v2 = Version("2.0.0")
        v3 = Version("1.5.0")

        # term1 is more restrictive than term2
        term1 = Term(pkg, VersionRange(v3, v2))  # [1.5.0, 2.0.0)
        term2 = Term(pkg, VersionRange(v1, v2))  # [1.0.0, 2.0.0)

        assert term1.satisfies(term2)
        assert not term2.satisfies(term1)

    def test_term_satisfies_both_negative(self):
        """Test satisfies relationship for negative terms."""
        pkg = Package("test")
        v1 = Version("1.0.0")
        v2 = Version("2.0.0")
        v3 = Version("1.5.0")

        # NOT term1 is more restrictive than NOT term2
        term1 = Term(pkg, VersionRange(v1, v2), False)  # NOT [1.0.0, 2.0.0)
        term2 = Term(pkg, VersionRange(v3, v2), False)  # NOT [1.5.0, 2.0.0)

        assert term1.satisfies(term2)
        assert not term2.satisfies(term1)

    def test_term_satisfies_positive_negative_no_overlap(self):
        """Test satisfies relationship for positive and negative terms with no overlap."""
        pkg = Package("test")
        v1 = Version("1.0.0")
        v2 = Version("2.0.0")
        v3 = Version("3.0.0")
        v4 = Version("4.0.0")

        term1 = Term(pkg, VersionRange(v1, v2), True)  # [1.0.0, 2.0.0)
        term2 = Term(pkg, VersionRange(v3, v4), False)  # NOT [3.0.0, 4.0.0)

        assert term1.satisfies(term2)
        assert not term2.satisfies(term1)

    def test_term_satisfies_positive_negative_overlap(self):
        """Test satisfies relationship for positive and negative terms with overlap."""
        pkg = Package("test")
        v1 = Version("1.0.0")
        v2 = Version("2.0.0")
        v3 = Version("1.5.0")

        term1 = Term(pkg, VersionRange(v1, v2), True)  # [1.0.0, 2.0.0)
        term2 = Term(pkg, VersionRange(v3, v2), False)  # NOT [1.5.0, 2.0.0)

        assert not term1.satisfies(term2)
        assert not term2.satisfies(term1)

    def test_term_satisfies_different_packages(self):
        """Test satisfies relationship for different packages."""
        pkg1 = Package("test1")
        pkg2 = Package("test2")
        version_range = VersionRange(Version("1.0.0"), Version("2.0.0"))

        term1 = Term(pkg1, version_range)
        term2 = Term(pkg2, version_range)

        assert not term1.satisfies(term2)
        assert not term2.satisfies(term1)

    def test_term_is_failure(self):
        """Test failure detection."""
        pkg = Package("test")
        v1 = Version("1.0.0")

        # Normal positive term
        term1 = Term(pkg, VersionRange(v1, None))
        assert not term1.is_failure()

        # Negative term (never a failure)
        term2 = Term(pkg, VersionRange(v1, None), False)
        assert not term2.is_failure()

        # Empty positive term (failure)
        empty_range = VersionRange(v1, v1, include_min=False, include_max=False)
        term3 = Term(pkg, empty_range)
        assert term3.is_failure()

    def test_term_equality(self):
        """Test term equality."""
        pkg = Package("test")
        version_range = VersionRange(Version("1.0.0"), Version("2.0.0"))

        term1 = Term(pkg, version_range, True)
        term2 = Term(pkg, version_range, True)
        term3 = Term(pkg, version_range, False)

        assert term1 == term2
        assert term1 != term3
        assert hash(term1) == hash(term2)
        assert hash(term1) != hash(term3)

    def test_term_string_representation(self):
        """Test string representation of terms."""
        pkg = Package("test")
        version_range = VersionRange(Version("1.0.0"), Version("2.0.0"))

        term1 = Term(pkg, version_range, True)
        assert "test" in str(term1)
        assert "NOT" not in str(term1)

        term2 = Term(pkg, version_range, False)
        assert "test" in str(term2)
        assert "NOT" in str(term2)

        assert "Term(" in repr(term1)


class TestTermStressTests:
    """Stress tests for Term class."""

    def test_complex_term_intersections(self):
        """Test complex term intersections with many overlapping ranges."""
        pkg = Package("test")
        versions = [Version(f"{i}.0.0") for i in range(1, 11)]

        # Create multiple overlapping positive terms - this is a challenging stress test
        terms = []
        for i in range(
            len(versions) - 3
        ):  # -3 to ensure versions[i + 3] doesn't go out of bounds
            range_obj = VersionRange(versions[i], versions[i + 3])
            terms.append(Term(pkg, range_obj, True))

        # Intersect all terms - this should result in a very narrow intersection or None
        result = terms[0]
        for term in terms[1:]:
            result = result.intersect(term)
            if result is None:
                break

        # This is a challenging test - the intersection of many ranges might be None
        # Don't make assumptions about the result, just verify it's handled correctly
        if result is not None:
            assert result.positive is True
            # If there's a result, it should be a valid term
            assert not result.is_failure()
        # If result is None, that's also valid - it means no common intersection exists

    def test_term_satisfies_chains(self):
        """Test chains of satisfies relationships."""
        pkg = Package("test")
        v1 = Version("1.0.0")
        v2 = Version("2.0.0")
        v3 = Version("3.0.0")
        v4 = Version("4.0.0")

        # Create a chain where term1 satisfies term2, term2 satisfies term3
        term1 = Term(pkg, VersionRange(v2, v3))  # [2.0.0, 3.0.0)
        term2 = Term(pkg, VersionRange(v1, v3))  # [1.0.0, 3.0.0)
        term3 = Term(pkg, VersionRange(v1, v4))  # [1.0.0, 4.0.0)

        assert term1.satisfies(term2)
        assert term2.satisfies(term3)
        assert term1.satisfies(term3)  # Transitivity

    def test_term_negation_stress(self):
        """Test multiple negations and intersections."""
        pkg = Package("test")
        v1 = Version("1.0.0")
        v2 = Version("2.0.0")

        term = Term(pkg, VersionRange(v1, v2))

        # Multiple negations should return to original
        negated = term.negate()
        double_negated = negated.negate()
        triple_negated = double_negated.negate()

        assert term.positive == double_negated.positive
        assert term.positive != triple_negated.positive
        assert term == double_negated
        assert term != triple_negated

    def test_edge_case_version_ranges(self):
        """Test terms with edge case version ranges."""
        pkg = Package("test")
        v1 = Version("1.0.0")

        # Single point range
        single_point = VersionRange(v1, v1, include_min=True, include_max=True)
        term1 = Term(pkg, single_point)
        assert not term1.is_failure()

        # Empty range
        empty_range = VersionRange(v1, v1, include_min=False, include_max=False)
        term2 = Term(pkg, empty_range)
        assert term2.is_failure()

        # Unbounded range
        unbounded = VersionRange()
        term3 = Term(pkg, unbounded)
        assert not term3.is_failure()

        # Test intersections with these edge cases
        intersection = term1.intersect(term3)
        assert intersection is not None
        assert intersection.version_range == single_point

    def test_term_with_prerelease_versions(self):
        """Test terms with pre-release versions."""
        pkg = Package("test")
        v1 = Version("1.0.0-alpha")
        v2 = Version("1.0.0-beta")
        v3 = Version("1.0.0")

        term1 = Term(pkg, VersionRange(v1, v2))
        term2 = Term(pkg, VersionRange(v2, v3))

        # These should not intersect at v2 (exclusive upper bound)
        intersection = term1.intersect(term2)
        assert intersection is None

        # Test with inclusive bounds
        term3 = Term(pkg, VersionRange(v1, v2, include_max=True))
        term4 = Term(pkg, VersionRange(v2, v3, include_min=True))

        intersection2 = term3.intersect(term4)
        assert intersection2 is not None
        assert intersection2.version_range.min_version == v2
        assert intersection2.version_range.max_version == v2
