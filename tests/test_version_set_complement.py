"""Tests for VersionSet complement operation."""

from pubgrub_resolver.version import Version, VersionRange, VersionSet


class TestVersionSetComplement:
    """Test cases for VersionSet complement operation."""

    def test_empty_set_complement(self):
        """Test complement of empty set is universal set."""
        empty_set = VersionSet([])
        universal_set = empty_set.complement()
        
        assert len(universal_set.ranges) == 1
        assert universal_set.ranges[0].min_version is None
        assert universal_set.ranges[0].max_version is None
        assert universal_set.contains(Version('1.0.0'))
        assert universal_set.contains(Version('0.1.0'))
        assert universal_set.contains(Version('100.0.0'))

    def test_single_range_complement(self):
        """Test complement of a single range."""
        single_range = VersionSet([VersionRange(Version("1.0.0"), Version("2.0.0"), True, False)])
        complement = single_range.complement()
        
        # Should have two ranges: (<∞, 1.0.0) and [2.0.0, ∞)
        assert len(complement.ranges) == 2
        
        # Test original set containment
        assert not single_range.contains(Version('0.5.0'))
        assert single_range.contains(Version('1.0.0'))
        assert single_range.contains(Version('1.5.0'))
        assert not single_range.contains(Version('2.0.0'))
        assert not single_range.contains(Version('2.5.0'))
        
        # Test complement containment (should be opposite)
        assert complement.contains(Version('0.5.0'))
        assert not complement.contains(Version('1.0.0'))
        assert not complement.contains(Version('1.5.0'))
        assert complement.contains(Version('2.0.0'))
        assert complement.contains(Version('2.5.0'))

    def test_multiple_ranges_complement(self):
        """Test complement of multiple disjoint ranges."""
        multi_range = VersionSet([
            VersionRange(Version("1.0.0"), Version("2.0.0"), True, False),
            VersionRange(Version("3.0.0"), Version("4.0.0"), True, False)
        ])
        complement = multi_range.complement()
        
        # Should have three ranges: (<∞, 1.0.0), [2.0.0, 3.0.0), [4.0.0, ∞)
        assert len(complement.ranges) == 3
        
        # Test specific versions
        assert complement.contains(Version('0.5.0'))    # Before first range
        assert not complement.contains(Version('1.5.0'))  # In first range
        assert complement.contains(Version('2.5.0'))    # Between ranges
        assert not complement.contains(Version('3.5.0'))  # In second range
        assert complement.contains(Version('4.5.0'))    # After second range

    def test_complement_normalization_disabled(self):
        """Test that complement operation doesn't normalize ranges incorrectly."""
        single_range = VersionSet([VersionRange(Version("1.0.0"), Version("2.0.0"), True, False)])
        complement = single_range.complement()
        
        # The complement should have exactly 2 ranges, not be normalized to "any"
        assert len(complement.ranges) == 2
        
        # Verify the ranges are what we expect
        ranges = sorted(complement.ranges, key=lambda r: (r.min_version is not None, r.min_version))
        
        # First range: (<∞, 1.0.0)
        assert ranges[0].min_version is None
        assert ranges[0].max_version == Version("1.0.0")
        assert ranges[0].include_min is True
        assert ranges[0].include_max is False
        
        # Second range: [2.0.0, ∞)
        assert ranges[1].min_version == Version("2.0.0")
        assert ranges[1].max_version is None
        assert ranges[1].include_min is True
        assert ranges[1].include_max is False

    def test_complement_edge_cases(self):
        """Test complement with edge cases like inclusive/exclusive boundaries."""
        # Test exclusive min, inclusive max
        range_set = VersionSet([VersionRange(Version("1.0.0"), Version("2.0.0"), False, True)])
        complement = range_set.complement()
        
        assert complement.contains(Version('1.0.0'))    # Excluded from original
        assert not complement.contains(Version('1.5.0'))  # Included in original
        assert not complement.contains(Version('2.0.0'))  # Included in original
        assert complement.contains(Version('2.1.0'))    # Excluded from original