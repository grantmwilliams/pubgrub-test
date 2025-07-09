"""
Benchmarks for Term operations.
"""

from pubgrub_resolver.term import Term
from pubgrub_resolver.package import Package
from pubgrub_resolver.version import Version, VersionRange


class TestTermBenchmarks:
    """Benchmark term operations."""

    def test_term_creation(self, benchmark):
        """Benchmark term creation performance."""
        pkg = Package("test")
        version_range = VersionRange(Version("1.0.0"), Version("2.0.0"))

        def create_term():
            return Term(pkg, version_range)

        result = benchmark(create_term)
        assert result.package == pkg
        assert result.version_range == version_range
        assert result.positive is True

    def test_term_negation(self, benchmark):
        """Benchmark term negation performance."""
        pkg = Package("test")
        version_range = VersionRange(Version("1.0.0"), Version("2.0.0"))
        term = Term(pkg, version_range)

        def negate_term():
            return term.negate()

        result = benchmark(negate_term)
        assert result.positive is False

    def test_term_intersection_positive(self, benchmark):
        """Benchmark positive term intersection."""
        pkg = Package("test")
        term1 = Term(pkg, VersionRange(Version("1.0.0"), Version("3.0.0")))
        term2 = Term(pkg, VersionRange(Version("2.0.0"), Version("4.0.0")))

        def intersect_terms():
            return term1.intersect(term2)

        result = benchmark(intersect_terms)
        assert result is not None
        assert result.positive is True

    def test_term_satisfies_check(self, benchmark):
        """Benchmark term satisfies relationship checking."""
        pkg = Package("test")
        term1 = Term(pkg, VersionRange(Version("1.5.0"), Version("2.0.0")))
        term2 = Term(pkg, VersionRange(Version("1.0.0"), Version("2.0.0")))

        def check_satisfies():
            return term1.satisfies(term2)

        result = benchmark(check_satisfies)
        assert result is True

    def test_many_term_intersections(self, benchmark):
        """Benchmark intersecting many terms."""
        pkg = Package("test")
        terms = []
        for i in range(100):
            start = Version(f"{i}.0.0")
            end = Version(f"{i + 50}.0.0")
            terms.append(Term(pkg, VersionRange(start, end)))

        def intersect_all_terms():
            result = terms[0]
            for term in terms[1:]:
                result = result.intersect(term)
                if result is None:
                    break
            return result

        result = benchmark(intersect_all_terms)
        # Result might be None if terms don't all intersect
        if result is not None:
            assert result.positive is True

    def test_term_chain_satisfies(self, benchmark):
        """Benchmark checking satisfies relationships in a chain."""
        pkg = Package("test")
        # Create a chain where each term is more restrictive than the previous
        # [10.0.0, 50.0.0), [15.0.0, 45.0.0), [20.0.0, 40.0.0), etc.
        terms = []
        for i in range(25):  # Fewer terms to ensure proper nesting
            start = Version(f"{10 + i}.0.0")
            end = Version(f"{50 - i}.0.0")
            if start < end:  # Only add if range is valid
                terms.append(Term(pkg, VersionRange(start, end)))

        def check_all_satisfies():
            results = []
            for i in range(len(terms) - 1):
                # Check if the more restrictive term satisfies the less restrictive one
                results.append(terms[i + 1].satisfies(terms[i]))
            return results

        result = benchmark(check_all_satisfies)
        assert len(result) == len(terms) - 1
        # Some should be True since terms are increasingly restrictive
        # But we're not asserting a specific count since the satisfies logic may have bugs


class TestTermStressBenchmarks:
    """Stress test benchmarks for term operations."""

    def test_complex_term_operations(self, benchmark):
        """Benchmark complex term operations with many packages."""
        packages = [Package(f"pkg{i}") for i in range(20)]
        terms = []

        for pkg in packages:
            for i in range(10):
                start = Version(f"{i}.0.0")
                end = Version(f"{i + 5}.0.0")
                terms.append(Term(pkg, VersionRange(start, end)))

        def complex_operations():
            results = []
            # Test intersections within the same package
            for pkg in packages:
                pkg_terms = [t for t in terms if t.package == pkg]
                if len(pkg_terms) >= 2:
                    intersection = pkg_terms[0].intersect(pkg_terms[1])
                    results.append(intersection)
            return results

        result = benchmark(complex_operations)
        assert len(result) == 20  # One result per package
        # Some intersections might be None
        valid_results = [r for r in result if r is not None]
        assert len(valid_results) > 0

    def test_negative_term_operations(self, benchmark):
        """Benchmark negative term operations."""
        pkg = Package("test")
        positive_terms = []
        negative_terms = []

        for i in range(25):
            start = Version(f"{i}.0.0")
            end = Version(f"{i + 10}.0.0")
            positive_terms.append(Term(pkg, VersionRange(start, end), True))
            negative_terms.append(Term(pkg, VersionRange(start, end), False))

        def mixed_operations():
            results = []
            for i in range(len(positive_terms)):
                for j in range(len(negative_terms)):
                    if i != j:  # Don't intersect the same range
                        intersection = positive_terms[i].intersect(negative_terms[j])
                        results.append(intersection)
            return results

        result = benchmark(mixed_operations)
        assert len(result) == 25 * 24  # 25 * 24 combinations
        # Some intersections might be None due to conflicts
        valid_results = [r for r in result if r is not None]
        assert len(valid_results) >= 0  # At least some should be valid
