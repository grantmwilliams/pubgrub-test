"""Advanced tests for Term intersection logic."""

import pytest
from pubgrub_resolver.version import Version, VersionRange
from pubgrub_resolver.package import Package
from pubgrub_resolver.term import Term


class TestTermIntersectionAdvanced:
    """Test cases for advanced term intersection scenarios."""

    def setup_method(self):
        """Set up test package."""
        self.pkg = Package("test")

    def test_both_positive_terms_intersection(self):
        """Test intersection of two positive terms."""
        term1 = Term(
            self.pkg,
            VersionRange(Version("1.0.0"), Version("3.0.0"), True, False),
            True,
        )  # [1.0.0, 3.0.0)
        term2 = Term(
            self.pkg,
            VersionRange(Version("2.0.0"), Version("4.0.0"), True, False),
            True,
        )  # [2.0.0, 4.0.0)

        result = term1.intersect(term2)

        assert result is not None
        assert result.positive is True
        assert result.version_range.min_version == Version("2.0.0")
        assert result.version_range.max_version == Version("3.0.0")
        assert result.version_range.include_min is True
        assert result.version_range.include_max is False

    def test_both_positive_terms_no_intersection(self):
        """Test intersection of two positive terms with no overlap."""
        term1 = Term(
            self.pkg,
            VersionRange(Version("1.0.0"), Version("2.0.0"), True, False),
            True,
        )  # [1.0.0, 2.0.0)
        term2 = Term(
            self.pkg,
            VersionRange(Version("3.0.0"), Version("4.0.0"), True, False),
            True,
        )  # [3.0.0, 4.0.0)

        result = term1.intersect(term2)

        assert result is None

    def test_both_negative_terms_intersection(self):
        """Test intersection of two negative terms."""
        term1 = Term(
            self.pkg,
            VersionRange(Version("1.0.0"), Version("2.0.0"), True, False),
            False,
        )  # NOT [1.0.0, 2.0.0)
        term2 = Term(
            self.pkg,
            VersionRange(Version("1.5.0"), Version("2.5.0"), True, False),
            False,
        )  # NOT [1.5.0, 2.5.0)

        result = term1.intersect(term2)

        # Should be NOT [1.0.0, 2.5.0) since NOT A AND NOT B = NOT (A OR B)
        assert result is not None
        assert result.positive is False
        assert result.version_range.min_version == Version("1.0.0")
        assert result.version_range.max_version == Version("2.5.0")
        assert result.version_range.include_min is True
        assert result.version_range.include_max is False

    def test_positive_and_negative_intersection(self):
        """Test intersection of positive and negative terms."""
        term1 = Term(
            self.pkg,
            VersionRange(Version("1.0.0"), Version("3.0.0"), True, False),
            True,
        )  # [1.0.0, 3.0.0)
        term2 = Term(
            self.pkg,
            VersionRange(Version("2.0.0"), Version("4.0.0"), True, False),
            False,
        )  # NOT [2.0.0, 4.0.0)

        result = term1.intersect(term2)

        # Should be [1.0.0, 3.0.0) ∩ NOT [2.0.0, 4.0.0) = [1.0.0, 2.0.0)
        assert result is not None
        assert result.positive is True
        assert result.version_range.min_version == Version("1.0.0")
        assert result.version_range.max_version == Version("2.0.0")
        assert result.version_range.include_min is True
        assert result.version_range.include_max is False

    def test_negative_and_positive_intersection(self):
        """Test intersection of negative and positive terms."""
        term1 = Term(
            self.pkg,
            VersionRange(Version("1.0.0"), Version("2.0.0"), True, False),
            False,
        )  # NOT [1.0.0, 2.0.0)
        term2 = Term(
            self.pkg,
            VersionRange(Version("1.5.0"), Version("3.0.0"), True, False),
            True,
        )  # [1.5.0, 3.0.0)

        result = term1.intersect(term2)

        # Should be NOT [1.0.0, 2.0.0) ∩ [1.5.0, 3.0.0) = [2.0.0, 3.0.0)
        assert result is not None
        assert result.positive is True
        assert result.version_range.min_version == Version("2.0.0")
        assert result.version_range.max_version == Version("3.0.0")
        assert result.version_range.include_min is True
        assert result.version_range.include_max is False

    def test_positive_negative_no_overlap(self):
        """Test positive and negative terms with no overlap."""
        term1 = Term(
            self.pkg,
            VersionRange(Version("1.0.0"), Version("2.0.0"), True, False),
            True,
        )  # [1.0.0, 2.0.0)
        term2 = Term(
            self.pkg,
            VersionRange(Version("3.0.0"), Version("4.0.0"), True, False),
            False,
        )  # NOT [3.0.0, 4.0.0)

        result = term1.intersect(term2)

        # No overlap, so positive term should be unaffected
        assert result is not None
        assert result.positive is True
        assert result.version_range.min_version == Version("1.0.0")
        assert result.version_range.max_version == Version("2.0.0")

    def test_negative_positive_no_overlap(self):
        """Test negative and positive terms with no overlap."""
        term1 = Term(
            self.pkg,
            VersionRange(Version("3.0.0"), Version("4.0.0"), True, False),
            False,
        )  # NOT [3.0.0, 4.0.0)
        term2 = Term(
            self.pkg,
            VersionRange(Version("1.0.0"), Version("2.0.0"), True, False),
            True,
        )  # [1.0.0, 2.0.0)

        result = term1.intersect(term2)

        # No overlap, so positive term should be unaffected
        assert result is not None
        assert result.positive is True
        assert result.version_range.min_version == Version("1.0.0")
        assert result.version_range.max_version == Version("2.0.0")

    def test_different_packages_intersection(self):
        """Test intersection of terms for different packages."""
        pkg1 = Package("package1")
        pkg2 = Package("package2")

        term1 = Term(
            pkg1, VersionRange(Version("1.0.0"), Version("2.0.0"), True, False), True
        )
        term2 = Term(
            pkg2, VersionRange(Version("1.0.0"), Version("2.0.0"), True, False), True
        )

        # Different packages can't intersect - should raise ValueError
        with pytest.raises(
            ValueError, match="Cannot intersect terms for different packages"
        ):
            term1.intersect(term2)

    def test_complex_boundary_conditions(self):
        """Test intersection with complex boundary conditions."""
        # Test adjacent ranges
        term1 = Term(
            self.pkg,
            VersionRange(Version("1.0.0"), Version("2.0.0"), True, False),
            True,
        )  # [1.0.0, 2.0.0)
        term2 = Term(
            self.pkg,
            VersionRange(Version("2.0.0"), Version("3.0.0"), True, False),
            False,
        )  # NOT [2.0.0, 3.0.0)

        result = term1.intersect(term2)

        # Should be [1.0.0, 2.0.0) since they don't overlap
        assert result is not None
        assert result.positive is True
        assert result.version_range.min_version == Version("1.0.0")
        assert result.version_range.max_version == Version("2.0.0")
        assert result.version_range.include_min is True
        assert result.version_range.include_max is False
