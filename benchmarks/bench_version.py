"""
Benchmarks for version handling operations.
"""

from pubgrub_resolver.version import Version, VersionRange


class TestVersionBenchmarks:
    """Benchmark version operations."""

    def test_version_creation(self, benchmark):
        """Benchmark version creation performance."""

        def create_version():
            return Version("1.2.3")

        result = benchmark(create_version)
        assert result.major == 1
        assert result.minor == 2
        assert result.patch == 3

    def test_version_comparison(self, benchmark):
        """Benchmark version comparison performance."""
        v1 = Version("1.2.3")
        v2 = Version("1.2.4")

        def compare_versions():
            return v1 < v2

        result = benchmark(compare_versions)
        assert result is True

    def test_version_range_contains(self, benchmark):
        """Benchmark version range containment checks."""
        version_range = VersionRange(Version("1.0.0"), Version("2.0.0"))
        test_version = Version("1.5.0")

        def check_contains():
            return version_range.contains(test_version)

        result = benchmark(check_contains)
        assert result is True

    def test_version_range_intersection(self, benchmark):
        """Benchmark version range intersection."""
        range1 = VersionRange(Version("1.0.0"), Version("3.0.0"))
        range2 = VersionRange(Version("2.0.0"), Version("4.0.0"))

        def intersect_ranges():
            return range1.intersect(range2)

        result = benchmark(intersect_ranges)
        assert result is not None
        assert result.min_version == Version("2.0.0")
        assert result.max_version == Version("3.0.0")

    def test_many_version_comparisons(self, benchmark):
        """Benchmark sorting many versions."""
        versions = [
            Version(f"{i}.{j}.{k}")
            for i in range(10)
            for j in range(10)
            for k in range(10)
        ]

        def sort_versions():
            return sorted(versions)

        result = benchmark(sort_versions)
        assert len(result) == 1000
        assert result[0] == Version("0.0.0")
        assert result[-1] == Version("9.9.9")


class TestVersionStressBenchmarks:
    """Stress test benchmarks for version operations."""

    def test_complex_range_intersections(self, benchmark):
        """Benchmark complex range intersection scenarios."""
        # Create many overlapping ranges
        ranges = []
        for i in range(100):
            start = Version(f"{i}.0.0")
            end = Version(f"{i + 10}.0.0")
            ranges.append(VersionRange(start, end))

        def intersect_all_ranges():
            result = ranges[0]
            for range_item in ranges[1:]:
                result = result.intersect(range_item)
                if result is None:
                    break
            return result

        result = benchmark(intersect_all_ranges)
        # Result might be None if ranges don't all overlap
        if result is not None:
            assert not result.is_empty()

    def test_version_parsing_stress(self, benchmark):
        """Benchmark parsing many version strings."""
        version_strings = [
            f"{i}.{j}.{k}-alpha.{m}"
            for i in range(5)
            for j in range(5)
            for k in range(5)
            for m in range(5)
        ]

        def parse_all_versions():
            return [Version(v) for v in version_strings]

        result = benchmark(parse_all_versions)
        assert len(result) == 625
        assert all(
            v.pre_release == f"alpha.{v.version_string.split('-alpha.')[1]}"
            for v in result
        )
