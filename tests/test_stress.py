"""
Stress tests for PubGrub resolver with larger dependency graphs.

These tests verify that the resolver can handle complex scenarios with many packages
and dependencies without excessive performance degradation.
"""

import time

import pytest

from pubgrub_resolver.dependency_provider import SimpleDependencyProvider
from pubgrub_resolver.package import Dependency
from pubgrub_resolver.version import Version, VersionRange
from pubgrub_resolver.resolver import solve_dependencies


def create_large_linear_chain(num_packages: int) -> SimpleDependencyProvider:
    """Create a large linear dependency chain: pkg0 -> pkg1 -> ... -> pkg(n-1)"""
    provider = SimpleDependencyProvider()
    packages = []

    for i in range(num_packages):
        pkg = provider.add_package(f"pkg{i}")
        ver = Version("1.0.0")
        provider.add_version(pkg, ver)
        packages.append(pkg)

        if i > 0:
            # Current package depends on previous package
            prev_pkg = packages[i - 1]
            dep_range = VersionRange(ver, ver, True, True)
            dependency = Dependency(prev_pkg, dep_range)
            provider.add_dependency(pkg, ver, dependency)

    return provider, packages[-1], Version("1.0.0")


def create_wide_dependency_tree(width: int, depth: int) -> SimpleDependencyProvider:
    """Create a wide dependency tree with given width and depth."""
    provider = SimpleDependencyProvider()

    # Create root package
    root = provider.add_package("root")
    root_ver = Version("1.0.0")
    provider.add_version(root, root_ver)

    # Create levels
    packages_by_level = [[root]]

    for level in range(1, depth + 1):
        level_packages = []

        for i in range(width):
            pkg = provider.add_package(f"pkg_l{level}_i{i}")
            ver = Version("1.0.0")
            provider.add_version(pkg, ver)
            level_packages.append(pkg)

            # Each package in this level depends on one package from the previous level
            prev_level_pkg = packages_by_level[level - 1][
                i % len(packages_by_level[level - 1])
            ]
            dep_range = VersionRange(ver, ver, True, True)
            dependency = Dependency(prev_level_pkg, dep_range)
            provider.add_dependency(pkg, ver, dependency)

        packages_by_level.append(level_packages)

    return provider, root, root_ver


def create_complex_version_scenario(
    num_packages: int, versions_per_package: int
) -> SimpleDependencyProvider:
    """Create a scenario with many packages, each having multiple versions."""
    provider = SimpleDependencyProvider()
    packages = []

    # Create packages with multiple versions
    for i in range(num_packages):
        pkg = provider.add_package(f"pkg{i}")
        packages.append(pkg)

        for j in range(1, versions_per_package + 1):
            ver = Version(f"{j}.0.0")
            provider.add_version(pkg, ver)

    # Add some complex dependencies
    for i in range(1, num_packages):
        pkg = packages[i]
        prev_pkg = packages[i - 1]

        # Latest version of current package depends on latest version of previous
        latest_ver = Version(f"{versions_per_package}.0.0")
        latest_prev_ver = Version(f"{versions_per_package}.0.0")

        dep_range = VersionRange(latest_prev_ver, latest_prev_ver, True, True)
        dependency = Dependency(prev_pkg, dep_range)
        provider.add_dependency(pkg, latest_ver, dependency)

        # Second-to-latest version has broader dependency range
        if versions_per_package > 1:
            second_ver = Version(f"{versions_per_package - 1}.0.0")
            broad_range = VersionRange(
                Version("1.0.0"), Version(f"{versions_per_package}.0.0"), True, True
            )
            broad_dependency = Dependency(prev_pkg, broad_range)
            provider.add_dependency(pkg, second_ver, broad_dependency)

    return provider, packages[-1], Version(f"{versions_per_package}.0.0")


class TestStressTests:
    """Stress tests for the PubGrub resolver."""

    def test_linear_chain_performance(self):
        """Test performance with a long linear dependency chain."""
        chain_lengths = [10, 25, 50]

        for length in chain_lengths:
            provider, root_pkg, root_ver = create_large_linear_chain(length)

            start_time = time.perf_counter()
            result = solve_dependencies(provider, root_pkg, root_ver)
            end_time = time.perf_counter()

            duration = end_time - start_time

            # Should succeed and be reasonably fast (under 1 second for 50 packages)
            assert result.success, (
                f"Resolution failed for chain length {length}: {result.error}"
            )
            assert duration < 1.0, (
                f"Resolution took too long ({duration:.3f}s) for chain length {length}"
            )

            # Should have all packages in solution
            if result.solution:
                solution_size = len(result.solution.get_all_assignments())
                assert solution_size == length, (
                    f"Expected {length} packages, got {solution_size}"
                )

    def test_wide_dependency_tree_performance(self):
        """Test performance with wide dependency trees."""
        scenarios = [
            (5, 3),  # 5 packages per level, 3 levels deep
            (10, 3),  # 10 packages per level, 3 levels deep
            (5, 5),  # 5 packages per level, 5 levels deep
        ]

        for width, depth in scenarios:
            provider, root_pkg, root_ver = create_wide_dependency_tree(width, depth)

            start_time = time.perf_counter()
            result = solve_dependencies(provider, root_pkg, root_ver)
            end_time = time.perf_counter()

            duration = end_time - start_time

            # Should succeed and be reasonably fast
            assert result.success, (
                f"Resolution failed for {width}x{depth} tree: {result.error}"
            )
            assert duration < 2.0, (
                f"Resolution took too long ({duration:.3f}s) for {width}x{depth} tree"
            )

            # Should have reasonable number of packages in solution
            if result.solution:
                solution_size = len(result.solution.get_all_assignments())
                expected_min = depth + 1  # At least root + one from each level
                assert solution_size >= expected_min, (
                    f"Expected at least {expected_min} packages, got {solution_size}"
                )

    def test_many_versions_scenario(self):
        """Test performance with many packages having multiple versions."""
        scenarios = [
            (10, 5),  # 10 packages, 5 versions each
            (15, 3),  # 15 packages, 3 versions each
            (8, 8),  # 8 packages, 8 versions each
        ]

        for num_packages, versions_per_package in scenarios:
            provider, root_pkg, root_ver = create_complex_version_scenario(
                num_packages, versions_per_package
            )

            start_time = time.perf_counter()
            result = solve_dependencies(provider, root_pkg, root_ver)
            end_time = time.perf_counter()

            duration = end_time - start_time

            # Should either succeed or fail cleanly
            assert isinstance(result.success, bool), (
                f"Invalid result for {num_packages}x{versions_per_package} scenario"
            )
            assert duration < 3.0, (
                f"Resolution took too long ({duration:.3f}s) for {num_packages}x{versions_per_package} scenario"
            )

            if result.success and result.solution:
                solution_size = len(result.solution.get_all_assignments())
                assert solution_size <= num_packages, (
                    f"Too many packages in solution: {solution_size} > {num_packages}"
                )

    def test_repeated_resolution_consistency(self):
        """Test that repeated resolutions of the same problem are consistent."""
        provider, root_pkg, root_ver = create_complex_version_scenario(8, 4)

        # Resolve multiple times
        results = []
        for _ in range(5):
            result = solve_dependencies(provider, root_pkg, root_ver)
            results.append(result)

        # All results should be identical
        first_result = results[0]
        for i, result in enumerate(results[1:], 1):
            assert result.success == first_result.success, (
                f"Result {i} success differs from first"
            )

            if result.success and first_result.success:
                first_solution = {
                    a.package.name: str(a.version)
                    for a in first_result.solution.get_all_assignments()
                }
                result_solution = {
                    a.package.name: str(a.version)
                    for a in result.solution.get_all_assignments()
                }
                assert first_solution == result_solution, (
                    f"Result {i} solution differs from first"
                )

    @pytest.mark.slow
    def test_very_large_scenario(self):
        """Test with a very large dependency graph (marked as slow test)."""
        # This test is marked as slow and may be skipped in normal CI runs
        provider, root_pkg, root_ver = create_large_linear_chain(100)

        start_time = time.perf_counter()
        result = solve_dependencies(provider, root_pkg, root_ver)
        end_time = time.perf_counter()

        duration = end_time - start_time

        # Should succeed but may take longer
        assert result.success, (
            f"Resolution failed for very large scenario: {result.error}"
        )
        assert duration < 10.0, (
            f"Resolution took too long ({duration:.3f}s) for very large scenario"
        )

        if result.solution:
            solution_size = len(result.solution.get_all_assignments())
            assert solution_size == 100, f"Expected 100 packages, got {solution_size}"


# Benchmark-style test for performance regression detection
def test_performance_benchmark():
    """Simple benchmark to detect performance regressions."""
    scenarios = [
        ("linear_10", lambda: create_large_linear_chain(10)),
        ("linear_25", lambda: create_large_linear_chain(25)),
        ("tree_5x3", lambda: create_wide_dependency_tree(5, 3)),
        ("versions_8x4", lambda: create_complex_version_scenario(8, 4)),
    ]

    results = {}

    for name, scenario_func in scenarios:
        provider, root_pkg, root_ver = scenario_func()

        # Warm up
        solve_dependencies(provider, root_pkg, root_ver)

        # Measure
        times = []
        for _ in range(3):
            start_time = time.perf_counter()
            result = solve_dependencies(provider, root_pkg, root_ver)
            end_time = time.perf_counter()

            assert isinstance(result.success, bool), f"Invalid result for {name}"
            times.append(end_time - start_time)

        avg_time = sum(times) / len(times)
        results[name] = avg_time

        # Print benchmark results for visibility
        print(f"Benchmark {name}: {avg_time:.4f}s average")

    # Basic sanity checks (adjust thresholds as needed)
    assert results["linear_10"] < 0.1, "Linear 10 scenario too slow"
    assert results["linear_25"] < 0.5, "Linear 25 scenario too slow"
    assert results["tree_5x3"] < 0.5, "Tree 5x3 scenario too slow"
    assert results["versions_8x4"] < 1.0, "Versions 8x4 scenario too slow"
