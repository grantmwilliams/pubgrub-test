"""
Pytest-benchmark tests for PubGrub resolver performance.

These tests use pytest-benchmark to provide detailed performance metrics
and comparisons across different benchmark runs.
"""

from pubgrub_resolver.dependency_provider import SimpleDependencyProvider
from pubgrub_resolver.package import Dependency
from pubgrub_resolver.version import Version, VersionRange
from pubgrub_resolver.resolver import solve_dependencies


class TestPubGrubBenchmarks:
    """Pytest benchmark tests for PubGrub resolver performance."""

    def create_simple_chain(self, chain_length: int):
        """Create a simple dependency chain for benchmarking."""
        provider = SimpleDependencyProvider()

        # Create chain: pkg0 -> pkg1 -> pkg2 -> ... -> pkgN
        packages = []
        for i in range(chain_length):
            pkg = provider.add_package(f"pkg{i}", is_root=(i == 0))
            packages.append(pkg)
            provider.add_version(pkg, Version("1.0.0"))

        # Add dependencies
        for i in range(chain_length - 1):
            provider.add_dependency(
                packages[i],
                Version("1.0.0"),
                Dependency(packages[i + 1], VersionRange(Version("1.0.0"), None)),
            )

        return provider, packages[0]

    def create_diamond_pattern(self, width: int, depth: int):
        """Create a diamond dependency pattern for benchmarking."""
        provider = SimpleDependencyProvider()

        # Create diamond pattern: root -> {left1, left2, ...} -> shared
        root = provider.add_package("root", is_root=True)
        provider.add_version(root, Version("1.0.0"))

        # Create multiple "left" packages
        left_packages = []
        for i in range(width):
            left_pkg = provider.add_package(f"left{i}")
            provider.add_version(left_pkg, Version("1.0.0"))
            left_packages.append(left_pkg)

            # Root depends on all left packages
            provider.add_dependency(
                root,
                Version("1.0.0"),
                Dependency(left_pkg, VersionRange(Version("1.0.0"), None)),
            )

        # Create shared dependencies
        shared_packages = []
        for level in range(depth):
            shared_pkg = provider.add_package(f"shared{level}")
            provider.add_version(shared_pkg, Version("1.0.0"))
            shared_packages.append(shared_pkg)

            if level == 0:
                for left_pkg in left_packages:
                    provider.add_dependency(
                        left_pkg,
                        Version("1.0.0"),
                        Dependency(shared_pkg, VersionRange(Version("1.0.0"), None)),
                    )
            else:
                provider.add_dependency(
                    shared_packages[level - 1],
                    Version("1.0.0"),
                    Dependency(shared_pkg, VersionRange(Version("1.0.0"), None)),
                )

        return provider, root

    def create_many_versions_scenario(
        self, package_count: int, versions_per_package: int
    ):
        """Create a scenario with many versions per package."""
        provider = SimpleDependencyProvider()

        # Create root package
        root = provider.add_package("root", is_root=True)
        provider.add_version(root, Version("1.0.0"))

        # Create packages with many versions
        packages = []
        for i in range(package_count):
            pkg = provider.add_package(f"pkg{i}")
            packages.append(pkg)

            # Add many versions
            for j in range(versions_per_package):
                provider.add_version(pkg, Version(f"{j}.0.0"))

            # Root depends on latest version of each package
            provider.add_dependency(
                root,
                Version("1.0.0"),
                Dependency(
                    pkg, VersionRange(Version(f"{versions_per_package - 1}.0.0"), None)
                ),
            )

        return provider, root

    # Simple chain benchmarks
    def test_simple_chain_10(self, benchmark):
        """Benchmark simple chain with 10 packages."""
        provider, root = self.create_simple_chain(10)

        def resolve():
            return solve_dependencies(provider, root, Version("1.0.0"))

        result = benchmark(resolve)
        assert result.success is True
        assert len(result.solution.get_all_assignments()) == 10

    def test_simple_chain_20(self, benchmark):
        """Benchmark simple chain with 20 packages."""
        provider, root = self.create_simple_chain(20)

        def resolve():
            return solve_dependencies(provider, root, Version("1.0.0"))

        result = benchmark(resolve)
        assert result.success is True
        assert len(result.solution.get_all_assignments()) == 20

    def test_simple_chain_50(self, benchmark):
        """Benchmark simple chain with 50 packages."""
        provider, root = self.create_simple_chain(50)

        def resolve():
            return solve_dependencies(provider, root, Version("1.0.0"))

        result = benchmark(resolve)
        assert result.success is True
        assert len(result.solution.get_all_assignments()) == 50

    # Diamond pattern benchmarks
    def test_diamond_5x3(self, benchmark):
        """Benchmark diamond pattern 5x3."""
        provider, root = self.create_diamond_pattern(5, 3)

        def resolve():
            return solve_dependencies(provider, root, Version("1.0.0"))

        result = benchmark(resolve)
        assert result.success is True

    def test_diamond_10x3(self, benchmark):
        """Benchmark diamond pattern 10x3."""
        provider, root = self.create_diamond_pattern(10, 3)

        def resolve():
            return solve_dependencies(provider, root, Version("1.0.0"))

        result = benchmark(resolve)
        assert result.success is True

    def test_diamond_20x3(self, benchmark):
        """Benchmark diamond pattern 20x3."""
        provider, root = self.create_diamond_pattern(20, 3)

        def resolve():
            return solve_dependencies(provider, root, Version("1.0.0"))

        result = benchmark(resolve)
        assert result.success is True

    # Many versions benchmarks
    def test_many_versions_5x10(self, benchmark):
        """Benchmark 5 packages with 10 versions each."""
        provider, root = self.create_many_versions_scenario(5, 10)

        def resolve():
            return solve_dependencies(provider, root, Version("1.0.0"))

        result = benchmark(resolve)
        assert result.success is True

    def test_many_versions_10x20(self, benchmark):
        """Benchmark 10 packages with 20 versions each."""
        provider, root = self.create_many_versions_scenario(10, 20)

        def resolve():
            return solve_dependencies(provider, root, Version("1.0.0"))

        result = benchmark(resolve)
        assert result.success is True

    def test_many_versions_20x10(self, benchmark):
        """Benchmark 20 packages with 10 versions each."""
        provider, root = self.create_many_versions_scenario(20, 10)

        def resolve():
            return solve_dependencies(provider, root, Version("1.0.0"))

        result = benchmark(resolve)
        assert result.success is True

    # Pubgrub-rs example scenarios
    def test_pubgrub_no_conflict(self, benchmark):
        """Benchmark pubgrub-rs no conflict scenario."""
        provider = SimpleDependencyProvider()

        # Add packages
        root = provider.add_package("root", is_root=True)
        foo = provider.add_package("foo")
        bar = provider.add_package("bar")

        # Add versions
        provider.add_version(root, Version("1.0.0"))
        provider.add_version(foo, Version("1.0.0"))
        provider.add_version(foo, Version("2.0.0"))
        provider.add_version(bar, Version("1.0.0"))
        provider.add_version(bar, Version("2.0.0"))

        # Dependencies
        provider.add_dependency(
            root,
            Version("1.0.0"),
            Dependency(foo, VersionRange(Version("1.0.0"), Version("2.0.0"))),
        )
        provider.add_dependency(
            foo,
            Version("1.0.0"),
            Dependency(bar, VersionRange(Version("1.0.0"), Version("2.0.0"))),
        )

        def resolve():
            return solve_dependencies(provider, root, Version("1.0.0"))

        result = benchmark(resolve)
        assert result.success is True

    def test_pubgrub_avoiding_conflict(self, benchmark):
        """Benchmark pubgrub-rs avoiding conflict scenario."""
        provider = SimpleDependencyProvider()

        # Add packages
        root = provider.add_package("root", is_root=True)
        foo = provider.add_package("foo")
        bar = provider.add_package("bar")

        # Add versions
        provider.add_version(root, Version("1.0.0"))
        provider.add_version(foo, Version("1.0.0"))
        provider.add_version(foo, Version("1.1.0"))
        provider.add_version(bar, Version("1.0.0"))
        provider.add_version(bar, Version("1.1.0"))
        provider.add_version(bar, Version("2.0.0"))

        # Dependencies
        provider.add_dependency(
            root,
            Version("1.0.0"),
            Dependency(foo, VersionRange(Version("1.0.0"), Version("2.0.0"))),
        )
        provider.add_dependency(
            root,
            Version("1.0.0"),
            Dependency(bar, VersionRange(Version("1.0.0"), Version("2.0.0"))),
        )
        provider.add_dependency(
            foo,
            Version("1.1.0"),
            Dependency(bar, VersionRange(Version("2.0.0"), Version("3.0.0"))),
        )

        def resolve():
            return solve_dependencies(provider, root, Version("1.0.0"))

        result = benchmark(resolve)
        assert result.success is True

    def test_pubgrub_conflict_resolution(self, benchmark):
        """Benchmark pubgrub-rs conflict resolution scenario."""
        provider = SimpleDependencyProvider()

        # Add packages
        root = provider.add_package("root", is_root=True)
        foo = provider.add_package("foo")
        bar = provider.add_package("bar")

        # Add versions
        provider.add_version(root, Version("1.0.0"))
        provider.add_version(foo, Version("1.0.0"))
        provider.add_version(foo, Version("2.0.0"))
        provider.add_version(bar, Version("1.0.0"))
        provider.add_version(bar, Version("2.0.0"))

        # Dependencies
        provider.add_dependency(
            root,
            Version("1.0.0"),
            Dependency(foo, VersionRange(Version("1.0.0"), None, False, False)),
        )
        provider.add_dependency(
            foo,
            Version("2.0.0"),
            Dependency(bar, VersionRange(Version("1.0.0"), Version("2.0.0"))),
        )

        def resolve():
            return solve_dependencies(provider, root, Version("1.0.0"))

        result = benchmark(resolve)
        assert result.success is True
