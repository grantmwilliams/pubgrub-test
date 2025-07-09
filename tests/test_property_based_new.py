"""
Property-based testing for PubGrub resolver using Hypothesis.

This module contains property-based tests inspired by the Rust implementation's PropTest tests.
These tests generate random dependency graphs and verify that the resolver behaves correctly.
"""

import random
from typing import List

from hypothesis import given, strategies as st, settings

from pubgrub_resolver.dependency_provider import SimpleDependencyProvider
from pubgrub_resolver.package import Dependency
from pubgrub_resolver.version import Version, VersionRange
from pubgrub_resolver.resolver import solve_dependencies


# Strategy for generating package names
package_names = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=8
).filter(lambda x: x not in ["root", "bad"])

# Strategy for generating version numbers (simplified to integers)
version_numbers = st.integers(min_value=1, max_value=20)

# Strategy for generating versions
versions = version_numbers.map(lambda x: Version(f"{x}.0.0"))


def generate_dependency_provider(
    packages: List[str],
    max_versions_per_package: int = 5,
    max_dependencies_per_version: int = 3,
    dependency_probability: float = 0.7,
) -> SimpleDependencyProvider:
    """Generate a random dependency provider with given constraints."""
    provider = SimpleDependencyProvider()
    package_objects = {}

    # Create packages
    for package_name in packages:
        pkg = provider.add_package(package_name)
        package_objects[package_name] = pkg

    # Add versions to each package
    package_versions = {}
    for package_name in packages:
        pkg = package_objects[package_name]
        num_versions = random.randint(1, max_versions_per_package)
        versions_list = []

        for i in range(1, num_versions + 1):
            version = Version(f"{i}.0.0")
            provider.add_version(pkg, version)
            versions_list.append(version)

        package_versions[package_name] = versions_list

    # Add dependencies (ensure DAG by only depending on packages with smaller indices)
    for i, package_name in enumerate(packages):
        pkg = package_objects[package_name]

        for version in package_versions[package_name]:
            # Randomly decide how many dependencies this version will have
            num_deps = random.randint(0, min(max_dependencies_per_version, i))

            # Choose random packages to depend on (only earlier packages to ensure DAG)
            available_deps = packages[:i]
            if available_deps and random.random() < dependency_probability:
                dep_packages = random.sample(
                    available_deps, min(num_deps, len(available_deps))
                )

                for dep_package_name in dep_packages:
                    dep_pkg = package_objects[dep_package_name]
                    dep_versions = package_versions[dep_package_name]

                    # Generate a version range for the dependency
                    if len(dep_versions) == 1:
                        # Only one version available
                        dep_range = VersionRange(
                            dep_versions[0], dep_versions[0], True, True
                        )
                    else:
                        # Random range
                        start_idx = random.randint(0, len(dep_versions) - 1)
                        end_idx = random.randint(start_idx, len(dep_versions) - 1)

                        if start_idx == end_idx:
                            # Exact version
                            dep_range = VersionRange(
                                dep_versions[start_idx],
                                dep_versions[start_idx],
                                True,
                                True,
                            )
                        else:
                            # Range
                            dep_range = VersionRange(
                                dep_versions[start_idx],
                                dep_versions[end_idx],
                                True,
                                True,
                            )

                    dependency = Dependency(dep_pkg, dep_range)
                    provider.add_dependency(pkg, version, dependency)

    return provider


@given(
    packages=st.lists(package_names, min_size=2, max_size=8, unique=True),
    seed=st.integers(min_value=0, max_value=1000000),
)
@settings(max_examples=50, deadline=5000)  # Reasonable limits for CI
def test_resolver_determinism(packages, seed):
    """Test that the resolver produces deterministic results."""
    random.seed(seed)

    # Generate a dependency provider
    provider = generate_dependency_provider(packages)

    # Try resolving each package
    for package_name in packages:
        pkg = provider.get_package_by_name(package_name)
        versions = provider.get_package_versions(pkg)

        if not versions:
            continue

        # Test the first version
        test_version = versions[0]

        # Resolve multiple times and ensure results are identical
        results = []
        for _ in range(3):
            result = solve_dependencies(provider, pkg, test_version)
            results.append(result)

        # All results should be identical
        first_result = results[0]
        for result in results[1:]:
            assert result.success == first_result.success
            if result.success:
                # Compare solutions
                first_assignments = set(
                    (a.package.name, str(a.version))
                    for a in first_result.solution.get_all_assignments()
                )
                result_assignments = set(
                    (a.package.name, str(a.version))
                    for a in result.solution.get_all_assignments()
                )
                assert first_assignments == result_assignments


@given(
    packages=st.lists(package_names, min_size=2, max_size=6, unique=True),
    seed=st.integers(min_value=0, max_value=1000000),
)
@settings(max_examples=30, deadline=10000)
def test_solution_satisfies_all_constraints(packages, seed):
    """Test that any solution returned satisfies all dependency constraints."""
    random.seed(seed)

    provider = generate_dependency_provider(packages)

    for package_name in packages:
        pkg = provider.get_package_by_name(package_name)
        versions = provider.get_package_versions(pkg)

        if not versions:
            continue

        # Test the first version
        test_version = versions[0]
        result = solve_dependencies(provider, pkg, test_version)

        if result.success and result.solution:
            # Verify that the solution satisfies all constraints
            assignments = {
                a.package.name: a.version for a in result.solution.get_all_assignments()
            }

            # Check that root package is assigned correctly
            assert pkg.name in assignments
            assert assignments[pkg.name] == test_version

            # Check that all dependencies are satisfied
            for assigned_package_name, assigned_version in assignments.items():
                assigned_pkg = provider.get_package_by_name(assigned_package_name)
                dependencies = provider.get_dependencies(assigned_pkg, assigned_version)

                for dependency in dependencies:
                    dep_package_name = dependency.package.name
                    dep_range = dependency.version_range

                    # The dependency must be satisfied
                    assert dep_package_name in assignments, (
                        f"Dependency {dep_package_name} not in solution"
                    )
                    dep_assigned_version = assignments[dep_package_name]
                    assert dep_range.contains(dep_assigned_version), (
                        f"Dependency {dep_package_name} version {dep_assigned_version} does not satisfy range {dep_range}"
                    )


@given(
    num_packages=st.integers(min_value=2, max_value=4),
    seed=st.integers(min_value=0, max_value=1000),
)
@settings(max_examples=15)
def test_linear_dependency_chain(num_packages, seed):
    """Test resolution with linear dependency chains."""
    random.seed(seed)

    provider = SimpleDependencyProvider()
    packages = []

    # Create a linear chain: pkg0 -> pkg1 -> pkg2 -> ...
    for i in range(num_packages):
        pkg = provider.add_package(f"pkg{i}")
        ver = Version("1.0.0")
        provider.add_version(pkg, ver)
        packages.append((pkg, ver))

        if i > 0:
            # Current package depends on previous package
            prev_pkg, prev_ver = packages[i - 1]
            dep_range = VersionRange(prev_ver, prev_ver, True, True)
            dependency = Dependency(prev_pkg, dep_range)
            provider.add_dependency(pkg, ver, dependency)

    # Resolution should succeed
    root_pkg, root_ver = packages[-1]  # Start from the last package
    result = solve_dependencies(provider, root_pkg, root_ver)

    assert result.success
    assert result.solution is not None

    # All packages should be in the solution
    solution_packages = set(
        a.package.name for a in result.solution.get_all_assignments()
    )
    expected_packages = set(f"pkg{i}" for i in range(num_packages))
    assert solution_packages == expected_packages
