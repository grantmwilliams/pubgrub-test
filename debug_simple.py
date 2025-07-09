#!/usr/bin/env python3

from pubgrub_resolver.dependency_provider import SimpleDependencyProvider
from pubgrub_resolver.package import Dependency
from pubgrub_resolver.version import Version, VersionRange
from pubgrub_resolver.resolver import solve_dependencies


def create_scenario_2():
    """Avoiding conflict during decision making."""
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
    # root 1.0.0 depends on foo [1.0.0, 2.0.0) and bar [1.0.0, 2.0.0)
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

    # foo 1.1.0 depends on bar [2.0.0, 3.0.0)
    provider.add_dependency(
        foo,
        Version("1.1.0"),
        Dependency(bar, VersionRange(Version("2.0.0"), Version("3.0.0"))),
    )

    return provider


def test_scenario_2():
    """Test scenario 2 with debug output."""
    print("=== SCENARIO 2 TEST ===")
    provider = create_scenario_2()
    root_package = provider.get_package_by_name("root")

    result = solve_dependencies(provider, root_package, Version("1.0.0"))

    print(f"Result: success={result.success}")
    if result.success:
        print("Solution:")
        solution_dict = {}
        for assignment in result.solution.get_all_assignments():
            solution_dict[assignment.package.name] = str(assignment.version)
        for name, version in solution_dict.items():
            print(f"  {name} = {version}")

        print("Expected: root=1.0.0, foo=1.0.0, bar=1.0.0 or 1.1.0")
        print(f"Actual: {solution_dict}")
    else:
        print(f"Error: {result.error}")


if __name__ == "__main__":
    test_scenario_2()
