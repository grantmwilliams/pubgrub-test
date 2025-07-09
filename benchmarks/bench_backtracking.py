"""
Backtracking performance benchmarks for PubGrub resolver.

These benchmarks specifically test the resolver's backtracking performance
under various conflict scenarios with increasing complexity.
"""

import time
from typing import List
from dataclasses import dataclass

from pubgrub_resolver.dependency_provider import SimpleDependencyProvider
from pubgrub_resolver.package import Dependency
from pubgrub_resolver.version import Version, VersionRange
from pubgrub_resolver.resolver import solve_dependencies


@dataclass
class BacktrackingBenchmarkResult:
    """Result of a backtracking benchmark run."""

    name: str
    duration_ms: float
    success: bool
    packages_resolved: int
    conflict_depth: int
    backtrack_count: int
    description: str


class BacktrackingBenchmarks:
    """Benchmarks focused on backtracking performance."""

    def __init__(self):
        self.results: List[BacktrackingBenchmarkResult] = []

    def benchmark_linear_backtracking(
        self, depth: int = 5
    ) -> BacktrackingBenchmarkResult:
        """Benchmark linear backtracking with increasing depth."""
        provider = SimpleDependencyProvider()

        # Create a scenario that requires linear backtracking
        root = provider.add_package("root", is_root=True)
        provider.add_version(root, Version("1.0.0"))

        packages = [root]

        # Create a chain where each package has multiple versions
        for i in range(1, depth + 1):
            pkg = provider.add_package(f"pkg{i}")
            packages.append(pkg)

            # Add multiple versions (higher versions will cause conflicts)
            for j in range(1, 4):  # versions 1.0.0, 2.0.0, 3.0.0
                provider.add_version(pkg, Version(f"{j}.0.0"))

        # Create dependencies that will force backtracking
        for i in range(depth):
            current_pkg = packages[i]
            next_pkg = packages[i + 1]

            if i == 0:
                # Root depends on first package
                provider.add_dependency(
                    current_pkg,
                    Version("1.0.0"),
                    Dependency(next_pkg, VersionRange(Version("1.0.0"), None)),
                )
            else:
                # Each package version depends on next package with constraints
                # Version 3.0.0 depends on next package >= 3.0.0
                provider.add_dependency(
                    current_pkg,
                    Version("3.0.0"),
                    Dependency(next_pkg, VersionRange(Version("3.0.0"), None)),
                )
                # Version 2.0.0 depends on next package >= 2.0.0
                provider.add_dependency(
                    current_pkg,
                    Version("2.0.0"),
                    Dependency(next_pkg, VersionRange(Version("2.0.0"), None)),
                )
                # Version 1.0.0 depends on next package >= 1.0.0
                provider.add_dependency(
                    current_pkg,
                    Version("1.0.0"),
                    Dependency(next_pkg, VersionRange(Version("1.0.0"), None)),
                )

        # Add a conflict at the end to force backtracking
        if depth > 0:
            last_pkg = packages[-1]
            conflict_pkg = provider.add_package("conflict")
            provider.add_version(conflict_pkg, Version("1.0.0"))
            provider.add_version(conflict_pkg, Version("2.0.0"))

            # Root needs conflict package v1.0.0
            provider.add_dependency(
                root,
                Version("1.0.0"),
                Dependency(
                    conflict_pkg,
                    VersionRange(Version("1.0.0"), Version("1.0.0"), True, True),
                ),
            )

            # Last package v3.0.0 needs conflict package v2.0.0 (forces backtracking)
            provider.add_dependency(
                last_pkg,
                Version("3.0.0"),
                Dependency(
                    conflict_pkg,
                    VersionRange(Version("2.0.0"), Version("2.0.0"), True, True),
                ),
            )

        # Benchmark resolution
        start_time = time.perf_counter()
        result = solve_dependencies(provider, root, Version("1.0.0"))
        end_time = time.perf_counter()

        duration_ms = (end_time - start_time) * 1000

        return BacktrackingBenchmarkResult(
            name=f"linear_backtracking_{depth}",
            duration_ms=duration_ms,
            success=result.success,
            packages_resolved=len(result.solution.get_all_assignments())
            if result.success
            else 0,
            conflict_depth=depth,
            backtrack_count=0,  # Would need to track this in resolver
            description=f"Linear backtracking with depth {depth}",
        )

    def benchmark_branching_backtracking(
        self, width: int = 3, depth: int = 3
    ) -> BacktrackingBenchmarkResult:
        """Benchmark branching backtracking scenarios."""
        provider = SimpleDependencyProvider()

        # Create a scenario with multiple branches that require backtracking
        root = provider.add_package("root", is_root=True)
        provider.add_version(root, Version("1.0.0"))

        # Create multiple branches from root
        branches = []
        for i in range(width):
            branch_packages = []
            for j in range(depth):
                pkg = provider.add_package(f"branch{i}_pkg{j}")
                branch_packages.append(pkg)

                # Add multiple versions
                provider.add_version(pkg, Version("1.0.0"))
                provider.add_version(pkg, Version("2.0.0"))

                if j == 0:
                    # Root depends on branch head
                    provider.add_dependency(
                        root,
                        Version("1.0.0"),
                        Dependency(pkg, VersionRange(Version("1.0.0"), None)),
                    )
                else:
                    # Chain within branch
                    provider.add_dependency(
                        branch_packages[j - 1],
                        Version("2.0.0"),
                        Dependency(pkg, VersionRange(Version("2.0.0"), None)),
                    )
                    provider.add_dependency(
                        branch_packages[j - 1],
                        Version("1.0.0"),
                        Dependency(pkg, VersionRange(Version("1.0.0"), None)),
                    )

            branches.append(branch_packages)

        # Add shared dependency that creates conflicts
        shared = provider.add_package("shared")
        provider.add_version(shared, Version("1.0.0"))
        provider.add_version(shared, Version("2.0.0"))

        # Root depends on shared v1.0.0
        provider.add_dependency(
            root,
            Version("1.0.0"),
            Dependency(
                shared, VersionRange(Version("1.0.0"), Version("1.0.0"), True, True)
            ),
        )

        # Some branch ends depend on shared v2.0.0 (creates conflict)
        for i in range(min(2, width)):
            if branches[i]:
                last_pkg = branches[i][-1]
                provider.add_dependency(
                    last_pkg,
                    Version("2.0.0"),
                    Dependency(
                        shared,
                        VersionRange(Version("2.0.0"), Version("2.0.0"), True, True),
                    ),
                )

        # Benchmark resolution
        start_time = time.perf_counter()
        result = solve_dependencies(provider, root, Version("1.0.0"))
        end_time = time.perf_counter()

        duration_ms = (end_time - start_time) * 1000

        return BacktrackingBenchmarkResult(
            name=f"branching_backtracking_{width}x{depth}",
            duration_ms=duration_ms,
            success=result.success,
            packages_resolved=len(result.solution.get_all_assignments())
            if result.success
            else 0,
            conflict_depth=depth,
            backtrack_count=0,
            description=f"Branching backtracking with {width} branches and {depth} depth",
        )

    def benchmark_version_explosion(
        self, packages: int = 5, versions: int = 10
    ) -> BacktrackingBenchmarkResult:
        """Benchmark scenarios with version explosion requiring extensive backtracking."""
        provider = SimpleDependencyProvider()

        # Create packages with many versions
        root = provider.add_package("root", is_root=True)
        provider.add_version(root, Version("1.0.0"))

        package_list = []
        for i in range(packages):
            pkg = provider.add_package(f"pkg{i}")
            package_list.append(pkg)

            # Add many versions
            for j in range(versions):
                provider.add_version(pkg, Version(f"{j}.0.0"))

        # Create complex interdependencies
        for i in range(packages):
            pkg = package_list[i]

            # Root depends on latest version of first few packages
            if i < min(3, packages):
                provider.add_dependency(
                    root,
                    Version("1.0.0"),
                    Dependency(pkg, VersionRange(Version(f"{versions - 1}.0.0"), None)),
                )

            # Create version-specific dependencies
            for j in range(versions):
                version = Version(f"{j}.0.0")

                # Dependencies on other packages with version constraints
                for k in range(i + 1, min(i + 3, packages)):
                    target_pkg = package_list[k]

                    # Higher versions have tighter constraints
                    if j >= versions // 2:
                        # Later versions need specific versions of dependencies
                        target_version = min(j, versions - 1)
                        provider.add_dependency(
                            pkg,
                            version,
                            Dependency(
                                target_pkg,
                                VersionRange(
                                    Version(f"{target_version}.0.0"),
                                    Version(f"{target_version}.0.0"),
                                    True,
                                    True,
                                ),
                            ),
                        )
                    else:
                        # Earlier versions have broader constraints
                        provider.add_dependency(
                            pkg,
                            version,
                            Dependency(
                                target_pkg, VersionRange(Version(f"{j}.0.0"), None)
                            ),
                        )

        # Add a conflict constraint
        if packages > 1:
            # Create a constraint that forces backtracking
            conflict_pkg = provider.add_package("conflict")
            provider.add_version(conflict_pkg, Version("1.0.0"))
            provider.add_version(conflict_pkg, Version("2.0.0"))

            # Root needs conflict v1.0.0
            provider.add_dependency(
                root,
                Version("1.0.0"),
                Dependency(
                    conflict_pkg,
                    VersionRange(Version("1.0.0"), Version("1.0.0"), True, True),
                ),
            )

            # Last package's latest version needs conflict v2.0.0
            provider.add_dependency(
                package_list[-1],
                Version(f"{versions - 1}.0.0"),
                Dependency(
                    conflict_pkg,
                    VersionRange(Version("2.0.0"), Version("2.0.0"), True, True),
                ),
            )

        # Benchmark resolution
        start_time = time.perf_counter()
        result = solve_dependencies(provider, root, Version("1.0.0"))
        end_time = time.perf_counter()

        duration_ms = (end_time - start_time) * 1000

        return BacktrackingBenchmarkResult(
            name=f"version_explosion_{packages}x{versions}",
            duration_ms=duration_ms,
            success=result.success,
            packages_resolved=len(result.solution.get_all_assignments())
            if result.success
            else 0,
            conflict_depth=packages,
            backtrack_count=0,
            description=f"Version explosion with {packages} packages and {versions} versions each",
        )

    def benchmark_cyclic_conflicts(
        self, cycle_length: int = 4
    ) -> BacktrackingBenchmarkResult:
        """Benchmark cyclic conflict scenarios."""
        provider = SimpleDependencyProvider()

        # Create a scenario with cyclic conflicts
        root = provider.add_package("root", is_root=True)
        provider.add_version(root, Version("1.0.0"))

        # Create packages in a cycle
        packages = []
        for i in range(cycle_length):
            pkg = provider.add_package(f"pkg{i}")
            packages.append(pkg)

            # Add multiple versions
            provider.add_version(pkg, Version("1.0.0"))
            provider.add_version(pkg, Version("2.0.0"))
            provider.add_version(pkg, Version("3.0.0"))

        # Root depends on first package
        provider.add_dependency(
            root,
            Version("1.0.0"),
            Dependency(packages[0], VersionRange(Version("1.0.0"), None)),
        )

        # Create cyclic dependencies with version constraints
        for i in range(cycle_length):
            current_pkg = packages[i]
            next_pkg = packages[(i + 1) % cycle_length]

            # v3.0.0 depends on next package v3.0.0
            provider.add_dependency(
                current_pkg,
                Version("3.0.0"),
                Dependency(next_pkg, VersionRange(Version("3.0.0"), None)),
            )

            # v2.0.0 depends on next package v2.0.0
            provider.add_dependency(
                current_pkg,
                Version("2.0.0"),
                Dependency(next_pkg, VersionRange(Version("2.0.0"), None)),
            )

            # v1.0.0 depends on next package v1.0.0
            provider.add_dependency(
                current_pkg,
                Version("1.0.0"),
                Dependency(next_pkg, VersionRange(Version("1.0.0"), None)),
            )

        # Add external constraints that break the cycle
        external = provider.add_package("external")
        provider.add_version(external, Version("1.0.0"))
        provider.add_version(external, Version("2.0.0"))

        # Root depends on external v1.0.0
        provider.add_dependency(
            root,
            Version("1.0.0"),
            Dependency(
                external, VersionRange(Version("1.0.0"), Version("1.0.0"), True, True)
            ),
        )

        # One of the cycle packages depends on external v2.0.0 (creates conflict)
        provider.add_dependency(
            packages[cycle_length // 2],
            Version("2.0.0"),
            Dependency(
                external, VersionRange(Version("2.0.0"), Version("2.0.0"), True, True)
            ),
        )

        # Benchmark resolution
        start_time = time.perf_counter()
        result = solve_dependencies(provider, root, Version("1.0.0"))
        end_time = time.perf_counter()

        duration_ms = (end_time - start_time) * 1000

        return BacktrackingBenchmarkResult(
            name=f"cyclic_conflicts_{cycle_length}",
            duration_ms=duration_ms,
            success=result.success,
            packages_resolved=len(result.solution.get_all_assignments())
            if result.success
            else 0,
            conflict_depth=cycle_length,
            backtrack_count=0,
            description=f"Cyclic conflicts with {cycle_length} packages in cycle",
        )

    def run_all_benchmarks(self) -> List[BacktrackingBenchmarkResult]:
        """Run all backtracking benchmarks."""
        benchmarks = [
            # Linear backtracking
            lambda: self.benchmark_linear_backtracking(3),
            lambda: self.benchmark_linear_backtracking(5),
            lambda: self.benchmark_linear_backtracking(7),
            # Branching backtracking
            lambda: self.benchmark_branching_backtracking(3, 3),
            lambda: self.benchmark_branching_backtracking(4, 3),
            lambda: self.benchmark_branching_backtracking(5, 4),
            # Version explosion
            lambda: self.benchmark_version_explosion(3, 8),
            lambda: self.benchmark_version_explosion(5, 10),
            lambda: self.benchmark_version_explosion(7, 8),
            # Cyclic conflicts
            lambda: self.benchmark_cyclic_conflicts(3),
            lambda: self.benchmark_cyclic_conflicts(4),
            lambda: self.benchmark_cyclic_conflicts(5),
        ]

        results = []
        for benchmark in benchmarks:
            try:
                result = benchmark()
                results.append(result)
                status = "SUCCESS" if result.success else "FAILED"
                print(f"✓ {result.name}: {result.duration_ms:.2f}ms ({status})")
            except Exception as e:
                print(f"✗ Benchmark failed: {e}")

        return results

    def print_results(self, results: List[BacktrackingBenchmarkResult]):
        """Print benchmark results in a formatted table."""
        print("\n" + "=" * 100)
        print("PUBGRUB BACKTRACKING PERFORMANCE BENCHMARKS")
        print("=" * 100)
        print(
            f"{'Benchmark':<35} {'Duration (ms)':<15} {'Status':<10} {'Packages':<10} {'Depth':<8} {'Description'}"
        )
        print("-" * 100)

        for result in results:
            status = "SUCCESS" if result.success else "FAILED"
            print(
                f"{result.name:<35} {result.duration_ms:<15.2f} {status:<10} {result.packages_resolved:<10} "
                f"{result.conflict_depth:<8} {result.description}"
            )

        print("-" * 100)

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

            max_depth = max(r.conflict_depth for r in successful)
            print(f"  Maximum conflict depth handled: {max_depth}")


def main():
    """Run backtracking benchmarks and print results."""
    benchmarks = BacktrackingBenchmarks()
    results = benchmarks.run_all_benchmarks()
    benchmarks.print_results(results)


if __name__ == "__main__":
    main()
