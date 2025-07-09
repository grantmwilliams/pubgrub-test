"""
Benchmarks for PubGrub resolver inspired by pubgrub-rs benchmarks.

These benchmarks test the performance of the resolver on various
scenarios similar to those in the pubgrub-rs crate.
"""

import time
from typing import List
from dataclasses import dataclass

from pubgrub_resolver.dependency_provider import SimpleDependencyProvider
from pubgrub_resolver.package import Dependency
from pubgrub_resolver.version import Version, VersionRange
from pubgrub_resolver.resolver import solve_dependencies


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""

    name: str
    duration_ms: float
    success: bool
    packages_resolved: int
    incompatibilities_generated: int
    description: str


class PubGrubBenchmarks:
    """Benchmarks inspired by pubgrub-rs performance tests."""

    def __init__(self):
        self.results: List[BenchmarkResult] = []

    def benchmark_simple_chain(self, chain_length: int = 20) -> BenchmarkResult:
        """Benchmark simple dependency chain resolution."""
        provider = SimpleDependencyProvider()

        # Create a chain of dependencies: pkg0 -> pkg1 -> pkg2 -> ... -> pkgN
        packages = []
        for i in range(chain_length):
            pkg = provider.add_package(f"pkg{i}", is_root=(i == 0))
            packages.append(pkg)
            provider.add_version(pkg, Version("1.0.0"))

        # Add dependencies: pkg_i depends on pkg_{i+1}
        for i in range(chain_length - 1):
            provider.add_dependency(
                packages[i],
                Version("1.0.0"),
                Dependency(packages[i + 1], VersionRange(Version("1.0.0"), None)),
            )

        # Benchmark resolution
        start_time = time.perf_counter()
        result = solve_dependencies(provider, packages[0], Version("1.0.0"))
        end_time = time.perf_counter()

        duration_ms = (end_time - start_time) * 1000

        return BenchmarkResult(
            name=f"simple_chain_{chain_length}",
            duration_ms=duration_ms,
            success=result.success,
            packages_resolved=len(result.solution.get_all_assignments())
            if result.success
            else 0,
            incompatibilities_generated=0,  # Would need to track this
            description=f"Simple chain of {chain_length} packages",
        )

    def benchmark_diamond_dependency(
        self, width: int = 10, depth: int = 3
    ) -> BenchmarkResult:
        """Benchmark diamond dependency pattern resolution."""
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

        # Create shared dependencies at multiple levels
        shared_packages = []
        for level in range(depth):
            shared_pkg = provider.add_package(f"shared{level}")
            provider.add_version(shared_pkg, Version("1.0.0"))
            shared_packages.append(shared_pkg)

            # All left packages depend on shared packages
            if level == 0:
                for left_pkg in left_packages:
                    provider.add_dependency(
                        left_pkg,
                        Version("1.0.0"),
                        Dependency(shared_pkg, VersionRange(Version("1.0.0"), None)),
                    )
            else:
                # Chain shared packages
                provider.add_dependency(
                    shared_packages[level - 1],
                    Version("1.0.0"),
                    Dependency(shared_pkg, VersionRange(Version("1.0.0"), None)),
                )

        # Benchmark resolution
        start_time = time.perf_counter()
        result = solve_dependencies(provider, root, Version("1.0.0"))
        end_time = time.perf_counter()

        duration_ms = (end_time - start_time) * 1000

        return BenchmarkResult(
            name=f"diamond_{width}x{depth}",
            duration_ms=duration_ms,
            success=result.success,
            packages_resolved=len(result.solution.get_all_assignments())
            if result.success
            else 0,
            incompatibilities_generated=0,
            description=f"Diamond pattern with {width} width and {depth} depth",
        )

    def benchmark_many_versions(
        self, package_count: int = 10, versions_per_package: int = 20
    ) -> BenchmarkResult:
        """Benchmark resolution with many versions per package."""
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

        # Add some inter-package dependencies
        for i in range(package_count - 1):
            # pkg_i depends on pkg_{i+1} with a range that includes multiple versions
            provider.add_dependency(
                packages[i],
                Version(f"{versions_per_package - 1}.0.0"),
                Dependency(
                    packages[i + 1],
                    VersionRange(Version(f"{versions_per_package // 2}.0.0"), None),
                ),
            )

        # Benchmark resolution
        start_time = time.perf_counter()
        result = solve_dependencies(provider, root, Version("1.0.0"))
        end_time = time.perf_counter()

        duration_ms = (end_time - start_time) * 1000

        return BenchmarkResult(
            name=f"many_versions_{package_count}x{versions_per_package}",
            duration_ms=duration_ms,
            success=result.success,
            packages_resolved=len(result.solution.get_all_assignments())
            if result.success
            else 0,
            incompatibilities_generated=0,
            description=f"{package_count} packages with {versions_per_package} versions each",
        )

    def benchmark_conflict_resolution(self, conflict_depth: int = 5) -> BenchmarkResult:
        """Benchmark conflict resolution with multiple levels of backtracking."""
        provider = SimpleDependencyProvider()

        # Create a scenario that requires backtracking
        root = provider.add_package("root", is_root=True)
        provider.add_version(root, Version("1.0.0"))

        # Create packages that will conflict
        packages = []
        for i in range(conflict_depth):
            pkg = provider.add_package(f"pkg{i}")
            packages.append(pkg)

            # Add multiple versions
            provider.add_version(pkg, Version("1.0.0"))
            provider.add_version(pkg, Version("2.0.0"))

            if i == 0:
                # Root depends on first package
                provider.add_dependency(
                    root,
                    Version("1.0.0"),
                    Dependency(pkg, VersionRange(Version("1.0.0"), None)),
                )
            else:
                # Create a chain that will require backtracking
                # pkg_{i-1} v2.0.0 depends on pkg_i v2.0.0
                provider.add_dependency(
                    packages[i - 1],
                    Version("2.0.0"),
                    Dependency(pkg, VersionRange(Version("2.0.0"), None)),
                )

                # pkg_{i-1} v1.0.0 depends on pkg_i v1.0.0
                provider.add_dependency(
                    packages[i - 1],
                    Version("1.0.0"),
                    Dependency(pkg, VersionRange(Version("1.0.0"), None)),
                )

        # Create a conflict at the end
        if conflict_depth > 1:
            # Last package v2.0.0 conflicts with something root needs
            conflict_pkg = provider.add_package("conflict")
            provider.add_version(conflict_pkg, Version("1.0.0"))

            # Root requires conflict package
            provider.add_dependency(
                root,
                Version("1.0.0"),
                Dependency(conflict_pkg, VersionRange(Version("1.0.0"), None)),
            )

            # Last package v2.0.0 depends on incompatible version
            provider.add_dependency(
                packages[-1],
                Version("2.0.0"),
                Dependency(conflict_pkg, VersionRange(Version("2.0.0"), None)),
            )

        # Benchmark resolution
        start_time = time.perf_counter()
        result = solve_dependencies(provider, root, Version("1.0.0"))
        end_time = time.perf_counter()

        duration_ms = (end_time - start_time) * 1000

        return BenchmarkResult(
            name=f"conflict_resolution_{conflict_depth}",
            duration_ms=duration_ms,
            success=result.success,
            packages_resolved=len(result.solution.get_all_assignments())
            if result.success
            else 0,
            incompatibilities_generated=0,
            description=f"Conflict resolution with {conflict_depth} levels",
        )

    def benchmark_large_graph(
        self, nodes: int = 100, edges_per_node: int = 3
    ) -> BenchmarkResult:
        """Benchmark resolution on a large dependency graph."""
        provider = SimpleDependencyProvider()

        # Create root package
        root = provider.add_package("root", is_root=True)
        provider.add_version(root, Version("1.0.0"))

        # Create many packages
        packages = []
        for i in range(nodes):
            pkg = provider.add_package(f"pkg{i}")
            packages.append(pkg)
            provider.add_version(pkg, Version("1.0.0"))

            if i < 10:  # Root depends on first 10 packages
                provider.add_dependency(
                    root,
                    Version("1.0.0"),
                    Dependency(pkg, VersionRange(Version("1.0.0"), None)),
                )

        # Add random dependencies between packages
        import random

        random.seed(42)  # For reproducible results

        for i, pkg in enumerate(packages):
            # Each package depends on a few others
            dependency_count = min(edges_per_node, len(packages) - i - 1)
            for _ in range(dependency_count):
                dep_index = random.randint(i + 1, len(packages) - 1)
                provider.add_dependency(
                    pkg,
                    Version("1.0.0"),
                    Dependency(
                        packages[dep_index], VersionRange(Version("1.0.0"), None)
                    ),
                )

        # Benchmark resolution
        start_time = time.perf_counter()
        result = solve_dependencies(provider, root, Version("1.0.0"))
        end_time = time.perf_counter()

        duration_ms = (end_time - start_time) * 1000

        return BenchmarkResult(
            name=f"large_graph_{nodes}x{edges_per_node}",
            duration_ms=duration_ms,
            success=result.success,
            packages_resolved=len(result.solution.get_all_assignments())
            if result.success
            else 0,
            incompatibilities_generated=0,
            description=f"Large graph with {nodes} nodes and ~{edges_per_node} edges per node",
        )

    def run_all_benchmarks(self) -> List[BenchmarkResult]:
        """Run all benchmarks and return results."""
        benchmarks = [
            # Simple chain benchmarks
            lambda: self.benchmark_simple_chain(10),
            lambda: self.benchmark_simple_chain(20),
            lambda: self.benchmark_simple_chain(50),
            # Diamond pattern benchmarks
            lambda: self.benchmark_diamond_dependency(5, 3),
            lambda: self.benchmark_diamond_dependency(10, 3),
            lambda: self.benchmark_diamond_dependency(20, 3),
            # Many versions benchmarks
            lambda: self.benchmark_many_versions(5, 10),
            lambda: self.benchmark_many_versions(10, 20),
            lambda: self.benchmark_many_versions(20, 10),
            # Conflict resolution benchmarks
            lambda: self.benchmark_conflict_resolution(3),
            lambda: self.benchmark_conflict_resolution(5),
            lambda: self.benchmark_conflict_resolution(7),
            # Large graph benchmarks
            lambda: self.benchmark_large_graph(50, 2),
            lambda: self.benchmark_large_graph(100, 3),
            lambda: self.benchmark_large_graph(200, 2),
        ]

        results = []
        for benchmark in benchmarks:
            try:
                result = benchmark()
                results.append(result)
                print(
                    f"✓ {result.name}: {result.duration_ms:.2f}ms ({'SUCCESS' if result.success else 'FAILED'})"
                )
            except Exception as e:
                print(f"✗ Benchmark failed: {e}")

        return results

    def print_results(self, results: List[BenchmarkResult]):
        """Print benchmark results in a formatted table."""
        print("\n" + "=" * 80)
        print("PUBGRUB RESOLVER BENCHMARKS")
        print("=" * 80)
        print(
            f"{'Benchmark':<30} {'Duration (ms)':<15} {'Status':<10} {'Packages':<10} {'Description'}"
        )
        print("-" * 80)

        for result in results:
            status = "SUCCESS" if result.success else "FAILED"
            print(
                f"{result.name:<30} {result.duration_ms:<15.2f} {status:<10} {result.packages_resolved:<10} {result.description}"
            )

        print("-" * 80)

        # Summary statistics
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        print("\nSUMMARY:")
        print(f"  Total benchmarks: {len(results)}")
        print(f"  Successful: {len(successful)}")
        print(f"  Failed: {len(failed)}")

        if successful:
            durations = [r.duration_ms for r in successful]
            print(f"  Average duration: {sum(durations) / len(durations):.2f}ms")
            print(f"  Min duration: {min(durations):.2f}ms")
            print(f"  Max duration: {max(durations):.2f}ms")

            total_packages = sum(r.packages_resolved for r in successful)
            print(f"  Total packages resolved: {total_packages}")


def main():
    """Run benchmarks and print results."""
    benchmarks = PubGrubBenchmarks()
    results = benchmarks.run_all_benchmarks()
    benchmarks.print_results(results)


if __name__ == "__main__":
    main()
